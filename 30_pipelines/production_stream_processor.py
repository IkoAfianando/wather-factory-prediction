#!/usr/bin/env python3
"""
Production Stream Processor for Weather AI Integration
Real-time processing of production data with weather correlation and optimization
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import pandas as pd
import numpy as np
from pymongo import MongoClient
import redis
from kafka import KafkaConsumer, KafkaProducer
import time
from concurrent.futures import ThreadPoolExecutor
from collections import deque
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ProductionEvent:
    """Standardized production event structure"""
    event_id: str
    timestamp: datetime
    location_id: str
    machine_id: str
    machine_class_id: str
    cycle: int
    global_cycle: int
    part_id: str
    job_id: str
    timer_id: str
    operator_id: str
    status: str            # Gain, Loss, New Session, etc.
    cycle_time: float      # seconds
    details: Dict[str, Any]  # runRate, tons, targetRate, etc.
    stop_reason: List[str]
    event_source: str      # APMS, Manual, API

@dataclass
class WeatherContext:
    """Weather context for production correlation"""
    timestamp: datetime
    location_id: str
    temperature: float
    humidity: float
    pressure: float
    weather_condition: str
    data_age_minutes: float  # How old the weather data is

@dataclass
class ProductionOptimization:
    """Production optimization recommendation"""
    optimization_id: str
    location_id: str
    machine_id: str
    timestamp: datetime
    weather_trigger: str
    current_parameters: Dict[str, float]
    optimized_parameters: Dict[str, float]
    expected_improvement: Dict[str, float]
    confidence_score: float
    implementation_priority: str

class ProductionStreamProcessor:
    """Real-time production stream processor with weather correlation"""
    
    def __init__(self, config_path: str = "config/production_processor.json"):
        self.config = self._load_config(config_path)
        
        # Database connections
        self.mongo_client = MongoClient(self.config['mongodb']['connection_string'])
        self.db = self.mongo_client[self.config['mongodb']['database']]
        self.redis_client = redis.Redis(**self.config['redis'])
        
        # Kafka setup
        self.kafka_consumer = KafkaConsumer(
            'production-events',
            'weather-data',
            bootstrap_servers=self.config['kafka']['bootstrap_servers'],
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            group_id='production-weather-processor'
        )
        
        self.kafka_producer = KafkaProducer(
            bootstrap_servers=self.config['kafka']['bootstrap_servers'],
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8')
        )
        
        # Processing state
        self.recent_production_events = deque(maxlen=1000)  # Last 1000 events
        self.recent_weather_data = {}  # Latest weather by location
        self.correlation_cache = {}    # Cached correlations
        self.optimization_models = {}  # ML models for optimization
        
        # Performance tracking
        self.processing_metrics = {
            'events_processed': 0,
            'optimizations_generated': 0,
            'alerts_triggered': 0,
            'processing_times': deque(maxlen=100),
            'correlation_accuracy': deque(maxlen=100)
        }
        
        # Thread pool for CPU-intensive tasks
        self.executor = ThreadPoolExecutor(max_workers=4)
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load processor configuration"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Config file {config_path} not found, using defaults")
            return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """Default configuration for production processor"""
        return {
            'mongodb': {
                'connection_string': 'mongodb://localhost:27017/',
                'database': 'weather_ai_profile'
            },
            'redis': {
                'host': 'localhost',
                'port': 6379,
                'db': 0
            },
            'kafka': {
                'bootstrap_servers': ['localhost:9092']
            },
            'correlation': {
                'max_weather_age_minutes': 30,  # Max age for weather correlation
                'correlation_window_minutes': 60,  # Correlation analysis window
                'min_confidence_threshold': 0.7,  # Min confidence for recommendations
            },
            'optimization': {
                'parameter_adjustment_limits': {
                    'pre_mix_time': {'min': 0.8, 'max': 1.4},    # 80% to 140% of base
                    'dryer_temp': {'min': -20, 'max': 10},        # -20°F to +10°F adjustment
                    'hold_release': {'min': -10, 'max': 15}       # -10s to +15s adjustment
                },
                'safety_overrides': {
                    'max_temperature': 95,     # °F
                    'max_humidity': 85,        # %
                    'min_quality_threshold': 80  # Quality score
                }
            }
        }
    
    async def start_processing(self):
        """Start the production stream processing"""
        logger.info("Starting production stream processor...")
        
        # Initialize models and cache
        await self._initialize_models()
        await self._load_correlation_cache()
        
        # Start processing tasks
        tasks = [
            self._kafka_message_processor(),
            self._real_time_correlator(),
            self._optimization_generator(),
            self._performance_monitor(),
            self._cache_maintenance()
        ]
        
        await asyncio.gather(*tasks)
    
    async def _initialize_models(self):
        """Initialize ML models and correlation algorithms"""
        logger.info("Initializing correlation models...")
        
        # Load pre-trained models or initialize new ones
        # This would load actual ML models for production optimization
        self.optimization_models = {
            'humidity_curing': {'model': None, 'accuracy': 0.85},
            'temperature_efficiency': {'model': None, 'accuracy': 0.78},
            'pressure_handling': {'model': None, 'accuracy': 0.72}
        }
        
    async def _load_correlation_cache(self):
        """Load correlation patterns from cache"""
        logger.info("Loading correlation cache...")
        
        try:
            # Load cached correlations from Redis
            cached_data = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.redis_client.get,
                'correlation_cache'
            )
            
            if cached_data:
                self.correlation_cache = json.loads(cached_data)
                logger.info(f"Loaded {len(self.correlation_cache)} cached correlations")
            else:
                # Initialize with base correlations from historical analysis
                self.correlation_cache = self._initialize_base_correlations()
                
        except Exception as e:
            logger.error(f"Failed to load correlation cache: {e}")
            self.correlation_cache = self._initialize_base_correlations()
    
    def _initialize_base_correlations(self) -> Dict[str, Any]:
        """Initialize base correlation patterns from analysis"""
        return {
            'humidity_cycle_time': {
                'correlation_coefficient': 0.73,
                'adjustment_formula': 'linear',
                'parameters': {'slope': 0.15, 'intercept': 1.0}
            },
            'temperature_efficiency': {
                'correlation_coefficient': -0.47,
                'adjustment_formula': 'exponential',
                'parameters': {'threshold': 85, 'factor': 0.85}
            },
            'pressure_quality': {
                'correlation_coefficient': 0.31,
                'adjustment_formula': 'step',
                'parameters': {'thresholds': [29.5, 30.2], 'adjustments': [0.95, 1.0, 1.05]}
            }
        }
    
    async def _kafka_message_processor(self):
        """Process incoming Kafka messages (production events and weather data)"""
        logger.info("Starting Kafka message processing...")
        
        while True:
            try:
                # Poll for messages
                message_batch = self.kafka_consumer.poll(timeout_ms=1000)
                
                for topic_partition, messages in message_batch.items():
                    for message in messages:
                        await self._process_kafka_message(message)
                        
            except Exception as e:
                logger.error(f"Kafka processing error: {e}")
                await asyncio.sleep(5)
    
    async def _process_kafka_message(self, message):
        """Process individual Kafka message"""
        start_time = time.time()
        
        try:
            data = message.value
            topic = message.topic
            
            if topic == 'production-events':
                await self._process_production_event(data)
            elif topic == 'weather-data':
                await self._process_weather_update(data)
            
            # Record processing time
            processing_time = time.time() - start_time
            self.processing_metrics['processing_times'].append(processing_time)
            self.processing_metrics['events_processed'] += 1
            
        except Exception as e:
            logger.error(f"Failed to process message: {e}")
    
    async def _process_production_event(self, event_data: Dict[str, Any]):
        """Process production event with weather correlation"""
        
        # Parse production event
        production_event = ProductionEvent(
            event_id=event_data.get('event_id', ''),
            timestamp=datetime.fromisoformat(event_data['timestamp']),
            location_id=event_data['location_id'],
            machine_id=event_data['machine_id'],
            machine_class_id=event_data.get('machine_class_id', ''),
            cycle=event_data.get('cycle', 0),
            global_cycle=event_data.get('global_cycle', 0),
            part_id=event_data.get('part_id', ''),
            job_id=event_data.get('job_id', ''),
            timer_id=event_data.get('timer_id', ''),
            operator_id=event_data.get('operator_id', ''),
            status=event_data['status'],
            cycle_time=event_data.get('cycle_time', 0.0),
            details=event_data.get('details', {}),
            stop_reason=event_data.get('stop_reason', []),
            event_source=event_data.get('event_source', 'APMS')
        )
        
        # Add to recent events
        self.recent_production_events.append(production_event)
        
        # Get weather context
        weather_context = await self._get_weather_context(
            production_event.location_id, 
            production_event.timestamp
        )
        
        if weather_context:
            # Analyze correlation
            correlation_analysis = await self._analyze_weather_production_correlation(
                production_event, weather_context
            )
            
            # Generate optimization if needed
            if correlation_analysis['requires_optimization']:
                optimization = await self._generate_optimization_recommendation(
                    production_event, weather_context, correlation_analysis
                )
                
                if optimization:
                    await self._publish_optimization(optimization)
                    
        # Store enriched event
        await self._store_enriched_event(production_event, weather_context)
    
    async def _process_weather_update(self, weather_data: Dict[str, Any]):
        """Process weather data update"""
        
        if weather_data['type'] == 'weather_reading':
            weather_info = weather_data['data']
            location_id = weather_info['location_id']
            
            # Update recent weather cache
            self.recent_weather_data[location_id] = WeatherContext(
                timestamp=datetime.fromisoformat(weather_info['timestamp']),
                location_id=location_id,
                temperature=weather_info['temperature'],
                humidity=weather_info['humidity'],
                pressure=weather_info['pressure'],
                weather_condition=weather_info['weather_condition'],
                data_age_minutes=0
            )
            
            # Check if any active production needs re-optimization
            await self._check_active_production_optimization(location_id)
    
    async def _get_weather_context(self, location_id: str, timestamp: datetime) -> Optional[WeatherContext]:
        """Get weather context for production event"""
        
        # Check recent weather cache first
        if location_id in self.recent_weather_data:
            weather = self.recent_weather_data[location_id]
            data_age = (timestamp - weather.timestamp).total_seconds() / 60
            
            if data_age <= self.config['correlation']['max_weather_age_minutes']:
                weather.data_age_minutes = data_age
                return weather
        
        # Fallback to Redis cache
        try:
            cached_weather = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.redis_client.get,
                f"weather:current:{location_id}"
            )
            
            if cached_weather:
                weather_data = json.loads(cached_weather)
                weather_timestamp = datetime.fromisoformat(weather_data['timestamp'])
                data_age = (timestamp - weather_timestamp).total_seconds() / 60
                
                if data_age <= self.config['correlation']['max_weather_age_minutes']:
                    return WeatherContext(
                        timestamp=weather_timestamp,
                        location_id=location_id,
                        temperature=weather_data['temperature'],
                        humidity=weather_data['humidity'],
                        pressure=weather_data['pressure'],
                        weather_condition=weather_data['weather_condition'],
                        data_age_minutes=data_age
                    )
        except Exception as e:
            logger.error(f"Failed to get cached weather: {e}")
        
        return None
    
    async def _analyze_weather_production_correlation(
        self, 
        production_event: ProductionEvent, 
        weather_context: WeatherContext
    ) -> Dict[str, Any]:
        """Analyze correlation between weather and production event"""
        
        analysis = {
            'requires_optimization': False,
            'correlation_factors': {},
            'risk_assessment': 'LOW',
            'recommended_actions': []
        }
        
        # Humidity correlation analysis
        if weather_context.humidity > 70:
            if production_event.status in ['Loss', 'Quality Issue']:
                analysis['correlation_factors']['humidity'] = {
                    'value': weather_context.humidity,
                    'impact': 'HIGH',
                    'correlation': 'NEGATIVE',
                    'confidence': 0.85
                }
                analysis['requires_optimization'] = True
                analysis['risk_assessment'] = 'HIGH'
                analysis['recommended_actions'].append('Increase pre-mix time')
        
        # Temperature correlation analysis
        if weather_context.temperature > 85:
            efficiency_impact = self._calculate_temperature_efficiency_impact(
                weather_context.temperature
            )
            
            if efficiency_impact > 0.1:  # >10% impact
                analysis['correlation_factors']['temperature'] = {
                    'value': weather_context.temperature,
                    'impact': 'MEDIUM' if efficiency_impact < 0.2 else 'HIGH',
                    'correlation': 'NEGATIVE',
                    'confidence': 0.78
                }
                analysis['requires_optimization'] = True
                analysis['recommended_actions'].append('Reduce dryer temperature')
        
        # Pressure correlation analysis
        pressure_trend = await self._get_pressure_trend(weather_context.location_id)
        if abs(pressure_trend) > 0.1:  # Significant pressure change
            analysis['correlation_factors']['pressure'] = {
                'value': weather_context.pressure,
                'trend': pressure_trend,
                'impact': 'MEDIUM',
                'correlation': 'VARIABLE',
                'confidence': 0.72
            }
            analysis['recommended_actions'].append('Adjust hold/release timing')
        
        return analysis
    
    def _calculate_temperature_efficiency_impact(self, temperature: float) -> float:
        """Calculate efficiency impact from temperature"""
        
        if temperature <= 85:
            return 0.0
        elif temperature <= 95:
            # Linear degradation from 85°F to 95°F
            return (temperature - 85) * 0.015  # 1.5% per degree
        else:
            # Exponential degradation above 95°F
            base_impact = 0.15  # 15% at 95°F
            excess_temp = temperature - 95
            return base_impact + (excess_temp * 0.03)  # 3% per degree above 95°F
    
    async def _get_pressure_trend(self, location_id: str) -> float:
        """Get pressure trend (change rate) for location"""
        
        try:
            # Get recent pressure readings from Redis
            pressure_history = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.redis_client.lrange,
                f"weather:pressure_history:{location_id}",
                0, 5
            )
            
            if len(pressure_history) >= 2:
                recent_pressures = [float(p) for p in pressure_history[:2]]
                return recent_pressures[0] - recent_pressures[1]  # Latest - Previous
            
        except Exception as e:
            logger.error(f"Failed to get pressure trend: {e}")
        
        return 0.0
    
    async def _generate_optimization_recommendation(
        self,
        production_event: ProductionEvent,
        weather_context: WeatherContext,
        correlation_analysis: Dict[str, Any]
    ) -> Optional[ProductionOptimization]:
        """Generate production optimization recommendation"""
        
        # Get current parameters
        current_params = production_event.details.copy() if production_event.details else {}
        
        # Base parameters (would be loaded from machine/part configuration)
        base_pre_mix_time = current_params.get('time', 60)  # Default 60 seconds
        base_dryer_temp = 300  # Default dryer temperature (would be from config)
        base_hold_time = 5     # Default hold time (would be from config)
        
        optimized_params = {}
        expected_improvements = {}
        confidence_scores = []
        
        # Humidity-based optimization
        if 'humidity' in correlation_analysis['correlation_factors']:
            humidity_factor = correlation_analysis['correlation_factors']['humidity']
            
            if humidity_factor['impact'] == 'HIGH':
                # Increase pre-mix time for high humidity
                adjustment_factor = 1.0 + (weather_context.humidity - 65) * 0.003  # 0.3% per % humidity above 65%
                adjustment_factor = min(adjustment_factor, self.config['optimization']['parameter_adjustment_limits']['pre_mix_time']['max'])
                
                optimized_params['pre_mix_time'] = base_pre_mix_time * adjustment_factor
                expected_improvements['quality_consistency'] = 0.20  # 20% improvement
                expected_improvements['defect_reduction'] = 0.15    # 15% fewer defects
                confidence_scores.append(humidity_factor['confidence'])
        
        # Temperature-based optimization
        if 'temperature' in correlation_analysis['correlation_factors']:
            temp_factor = correlation_analysis['correlation_factors']['temperature']
            
            if temp_factor['impact'] in ['HIGH', 'MEDIUM']:
                # Reduce dryer temperature for high ambient temperature
                temp_adjustment = min(-(weather_context.temperature - 85) * 1.5, 0)  # Reduce by 1.5°F per degree above 85°F
                temp_adjustment = max(temp_adjustment, self.config['optimization']['parameter_adjustment_limits']['dryer_temp']['min'])
                
                optimized_params['dryer_temp'] = base_dryer_temp + temp_adjustment
                expected_improvements['energy_savings'] = abs(temp_adjustment) * 0.02  # 2% per degree reduction
                expected_improvements['efficiency_improvement'] = abs(temp_adjustment) * 0.015  # 1.5% per degree
                confidence_scores.append(temp_factor['confidence'])
        
        # Pressure-based optimization
        if 'pressure' in correlation_analysis['correlation_factors']:
            pressure_factor = correlation_analysis['correlation_factors']['pressure']
            
            if abs(pressure_factor.get('trend', 0)) > 0.05:  # Significant pressure change
                # Adjust hold time based on pressure trend
                pressure_adjustment = pressure_factor['trend'] * 20  # 20 seconds per inHg change
                pressure_adjustment = max(min(pressure_adjustment, 
                                            self.config['optimization']['parameter_adjustment_limits']['hold_release']['max']),
                                        self.config['optimization']['parameter_adjustment_limits']['hold_release']['min'])
                
                optimized_params['hold_time'] = base_hold_time + pressure_adjustment
                expected_improvements['material_handling'] = 0.12  # 12% improvement
                confidence_scores.append(pressure_factor['confidence'])
        
        # Only generate optimization if we have meaningful changes and sufficient confidence
        if optimized_params and confidence_scores:
            avg_confidence = np.mean(confidence_scores)
            
            if avg_confidence >= self.config['correlation']['min_confidence_threshold']:
                optimization = ProductionOptimization(
                    optimization_id=f"opt_{production_event.location_id}_{production_event.machine_id}_{int(time.time())}",
                    location_id=production_event.location_id,
                    machine_id=production_event.machine_id,
                    timestamp=datetime.now(),
                    weather_trigger=f"T:{weather_context.temperature:.1f}°F H:{weather_context.humidity:.1f}% P:{weather_context.pressure:.2f}inHg",
                    current_parameters={
                        'pre_mix_time': base_pre_mix_time,
                        'dryer_temp': base_dryer_temp,
                        'hold_time': base_hold_time
                    },
                    optimized_parameters=optimized_params,
                    expected_improvement=expected_improvements,
                    confidence_score=avg_confidence,
                    implementation_priority=self._calculate_implementation_priority(
                        correlation_analysis['risk_assessment'], avg_confidence
                    )
                )
                
                return optimization
        
        return None
    
    def _calculate_implementation_priority(self, risk_assessment: str, confidence: float) -> str:
        """Calculate implementation priority for optimization"""
        
        if risk_assessment == 'HIGH' and confidence > 0.8:
            return 'IMMEDIATE'
        elif risk_assessment == 'HIGH' or confidence > 0.85:
            return 'HIGH'
        elif confidence > 0.75:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    async def _publish_optimization(self, optimization: ProductionOptimization):
        """Publish optimization recommendation"""
        
        try:
            # Stream to Kafka
            kafka_message = {
                'type': 'production_optimization',
                'data': asdict(optimization),
                'timestamp': datetime.now().isoformat()
            }
            
            await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.kafka_producer.send,
                'production-optimizations',
                kafka_message
            )
            
            # Store in database
            await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.db.production_optimizations.insert_one,
                asdict(optimization)
            )
            
            self.processing_metrics['optimizations_generated'] += 1
            
            logger.info(f"Published optimization: {optimization.optimization_id} - "
                       f"Priority: {optimization.implementation_priority} - "
                       f"Confidence: {optimization.confidence_score:.2f}")
            
        except Exception as e:
            logger.error(f"Failed to publish optimization: {e}")
    
    async def _store_enriched_event(self, production_event: ProductionEvent, weather_context: Optional[WeatherContext]):
        """Store production event enriched with weather context"""
        
        try:
            enriched_event = asdict(production_event)
            
            if weather_context:
                enriched_event['weather_context'] = asdict(weather_context)
            
            await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.db.enriched_production_events.insert_one,
                enriched_event
            )
            
        except Exception as e:
            logger.error(f"Failed to store enriched event: {e}")
    
    async def _real_time_correlator(self):
        """Real-time correlation analysis and model updates"""
        logger.info("Starting real-time correlation analysis...")
        
        while True:
            try:
                # Analyze recent events for correlation patterns
                if len(self.recent_production_events) > 50:
                    await self._analyze_recent_correlations()
                
                await asyncio.sleep(300)  # Analyze every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in correlation analysis: {e}")
                await asyncio.sleep(60)
    
    async def _analyze_recent_correlations(self):
        """Analyze correlations in recent production events"""
        
        # Extract events from last hour
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_events = [
            event for event in self.recent_production_events
            if event.timestamp >= one_hour_ago
        ]
        
        if len(recent_events) < 10:
            return
        
        # Group by location for analysis
        by_location = {}
        for event in recent_events:
            if event.location_id not in by_location:
                by_location[event.location_id] = []
            by_location[event.location_id].append(event)
        
        # Analyze each location
        for location_id, events in by_location.items():
            correlation_update = await self._calculate_location_correlations(location_id, events)
            
            if correlation_update:
                await self._update_correlation_cache(location_id, correlation_update)
    
    async def _calculate_location_correlations(self, location_id: str, events: List[ProductionEvent]) -> Optional[Dict[str, Any]]:
        """Calculate correlations for specific location"""
        
        # This would implement statistical correlation analysis
        # For now, return placeholder correlation updates
        return None
    
    async def _update_correlation_cache(self, location_id: str, correlation_update: Dict[str, Any]):
        """Update correlation cache with new patterns"""
        
        cache_key = f"correlation:{location_id}"
        
        try:
            await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.redis_client.setex,
                cache_key,
                3600,  # 1 hour
                json.dumps(correlation_update, default=str)
            )
            
        except Exception as e:
            logger.error(f"Failed to update correlation cache: {e}")
    
    async def _optimization_generator(self):
        """Continuous optimization opportunity detection"""
        logger.info("Starting optimization generator...")
        
        while True:
            try:
                # Look for optimization opportunities in recent events
                await self._scan_optimization_opportunities()
                
                await asyncio.sleep(180)  # Scan every 3 minutes
                
            except Exception as e:
                logger.error(f"Error in optimization generator: {e}")
                await asyncio.sleep(60)
    
    async def _scan_optimization_opportunities(self):
        """Scan for optimization opportunities"""
        
        # Check for patterns that indicate optimization opportunities
        # This would analyze recent events and weather patterns
        pass
    
    async def _check_active_production_optimization(self, location_id: str):
        """Check if active production at location needs re-optimization"""
        
        # Get recent production events for location
        recent_events = [
            event for event in self.recent_production_events
            if (event.location_id == location_id and 
                (datetime.now() - event.timestamp).total_seconds() < 1800)  # Last 30 minutes
        ]
        
        if recent_events:
            # Check if weather change requires new optimization
            latest_weather = self.recent_weather_data.get(location_id)
            
            if latest_weather:
                # Trigger re-optimization if significant weather changes
                for event in recent_events:
                    if event.status in ['Gain', 'Loss']:
                        # Check if optimization needed based on new weather
                        pass
    
    async def _performance_monitor(self):
        """Monitor processing performance and accuracy"""
        logger.info("Starting performance monitoring...")
        
        while True:
            try:
                # Log performance metrics
                if self.processing_metrics['processing_times']:
                    avg_processing_time = np.mean(list(self.processing_metrics['processing_times']))
                    events_per_minute = self.processing_metrics['events_processed'] / max(1, time.time() / 60)
                    
                    logger.info(f"Performance Metrics - Events: {self.processing_metrics['events_processed']}, "
                              f"Avg Processing Time: {avg_processing_time:.3f}s, "
                              f"Events/min: {events_per_minute:.1f}, "
                              f"Optimizations: {self.processing_metrics['optimizations_generated']}")
                
                await asyncio.sleep(3600)  # Report every hour
                
            except Exception as e:
                logger.error(f"Error in performance monitor: {e}")
                await asyncio.sleep(300)
    
    async def _cache_maintenance(self):
        """Maintain caches and clean up old data"""
        logger.info("Starting cache maintenance...")
        
        while True:
            try:
                # Clean up old correlation cache entries
                # Refresh model accuracy metrics
                # Archive old production events
                
                await asyncio.sleep(3600)  # Maintenance every hour
                
            except Exception as e:
                logger.error(f"Error in cache maintenance: {e}")
                await asyncio.sleep(300)
    
    async def shutdown(self):
        """Gracefully shutdown the processor"""
        logger.info("Shutting down production stream processor...")
        
        self.kafka_consumer.close()
        self.kafka_producer.close()
        self.redis_client.close()
        self.mongo_client.close()
        
        logger.info("Production stream processor shutdown complete")


async def main():
    """Main processor execution"""
    
    processor = ProductionStreamProcessor()
    
    try:
        await processor.start_processing()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        await processor.shutdown()


if __name__ == "__main__":
    asyncio.run(main())