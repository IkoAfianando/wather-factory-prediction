#!/usr/bin/env python3
"""
Real-Time Weather Data Pipeline for Production Integration
Handles real-time ingestion, processing, and correlation of weather data with production systems
"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import pandas as pd
import numpy as np
from pymongo import MongoClient
import redis
from kafka import KafkaProducer, KafkaConsumer
import schedule
import time
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class WeatherReading:
    """Standardized weather reading structure"""
    timestamp: datetime
    location_id: str
    location_name: str
    latitude: float
    longitude: float
    temperature: float      # Fahrenheit
    humidity: float         # Percentage
    pressure: float         # inHg
    wind_speed: float       # mph
    wind_direction: int     # degrees
    precipitation: float    # inches
    visibility: float       # miles
    uv_index: float
    weather_condition: str
    weather_code: int
    data_source: str        # API source
    quality_score: float    # Data quality 0-1

@dataclass
class WeatherAlert:
    """Weather alert for production impact"""
    alert_id: str
    location_id: str
    alert_type: str         # HUMIDITY, TEMPERATURE, PRESSURE, STORM
    severity: str           # LOW, MEDIUM, HIGH, CRITICAL
    message: str
    recommended_actions: List[str]
    production_impact: str
    valid_until: datetime

class WeatherDataPipeline:
    """Real-time weather data pipeline for production integration"""
    
    def __init__(self, config_path: str = "config/weather_pipeline.json"):
        self.config = self._load_config(config_path)
        self.locations = self.config['locations']
        self.api_keys = self.config['api_keys']
        
        # Initialize connections
        self.mongo_client = MongoClient(self.config['mongodb']['connection_string'])
        self.db = self.mongo_client[self.config['mongodb']['database']]
        self.redis_client = redis.Redis(**self.config['redis'])
        
        # Kafka setup for real-time streaming
        self.kafka_producer = KafkaProducer(
            bootstrap_servers=self.config['kafka']['bootstrap_servers'],
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8')
        )
        
        # Weather API clients
        self.api_sessions = {}
        self.executor = ThreadPoolExecutor(max_workers=5)
        
        # Data quality tracking
        self.quality_metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'api_response_times': [],
            'data_quality_scores': []
        }
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load pipeline configuration"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Config file {config_path} not found, using defaults")
            return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """Default configuration for weather pipeline"""
        return {
            'locations': {
                'seguin_tx': {
                    'name': 'Seguin, TX',
                    'latitude': 29.5688,
                    'longitude': -97.9647,
                    'timezone': 'America/Chicago',
                    'priority': 'HIGH'
                },
                'conroe_tx': {
                    'name': 'Conroe, TX', 
                    'latitude': 30.3118,
                    'longitude': -95.4560,
                    'timezone': 'America/Chicago',
                    'priority': 'MEDIUM'
                },
                'gunter_tx': {
                    'name': 'Gunter, TX',
                    'latitude': 33.4476,
                    'longitude': -96.7474,
                    'timezone': 'America/Chicago',
                    'priority': 'MEDIUM'
                }
            },
            'api_keys': {
                'openweathermap': os.getenv('OPENWEATHERMAP_API_KEY', ''),
                'noaa': os.getenv('NOAA_API_KEY', ''),
                'weatherapi': os.getenv('WEATHERAPI_KEY', '')
            },
            'mongodb': {
                'connection_string': os.getenv('MONGODB_URI', 'mongodb://localhost:27017/'),
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
            'polling_intervals': {
                'current_weather': 900,    # 15 minutes
                'forecast': 3600,          # 1 hour  
                'alerts': 300              # 5 minutes
            }
        }
    
    async def start_pipeline(self):
        """Start the real-time weather data pipeline"""
        logger.info("Starting weather data pipeline...")
        
        # Initialize async HTTP sessions
        await self._init_api_sessions()
        
        # Start background tasks
        tasks = [
            self._current_weather_loop(),
            self._forecast_loop(),
            self._weather_alerts_loop(),
            self._data_quality_monitor(),
            self._production_correlation_processor()
        ]
        
        # Run all tasks concurrently
        await asyncio.gather(*tasks)
        
    async def _init_api_sessions(self):
        """Initialize HTTP sessions for weather APIs"""
        self.api_sessions = {
            'openweathermap': aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={'User-Agent': 'WeatherAI-Pipeline/1.0'}
            ),
            'noaa': aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            ),
            'weatherapi': aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        }
        
    async def _current_weather_loop(self):
        """Continuous current weather monitoring"""
        logger.info("Starting current weather monitoring loop")
        
        while True:
            try:
                # Fetch current weather for all locations
                weather_tasks = []
                for location_id, location_data in self.locations.items():
                    weather_tasks.append(
                        self._fetch_current_weather(location_id, location_data)
                    )
                
                # Execute all requests concurrently
                weather_results = await asyncio.gather(*weather_tasks, return_exceptions=True)
                
                # Process results
                for result in weather_results:
                    if isinstance(result, WeatherReading):
                        await self._process_weather_reading(result)
                    elif isinstance(result, Exception):
                        logger.error(f"Weather fetch error: {result}")
                        
                # Wait for next polling interval
                await asyncio.sleep(self.config['polling_intervals']['current_weather'])
                
            except Exception as e:
                logger.error(f"Error in current weather loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retry
    
    async def _fetch_current_weather(self, location_id: str, location_data: Dict[str, Any]) -> Optional[WeatherReading]:
        """Fetch current weather from multiple sources with fallback"""
        
        # Try OpenWeatherMap first
        try:
            weather = await self._fetch_openweathermap_current(location_id, location_data)
            if weather:
                return weather
        except Exception as e:
            logger.warning(f"OpenWeatherMap failed for {location_id}: {e}")
            
        # Fallback to WeatherAPI
        try:
            weather = await self._fetch_weatherapi_current(location_id, location_data)
            if weather:
                return weather
        except Exception as e:
            logger.warning(f"WeatherAPI failed for {location_id}: {e}")
            
        # Fallback to NOAA
        try:
            weather = await self._fetch_noaa_current(location_id, location_data)
            if weather:
                return weather
        except Exception as e:
            logger.warning(f"NOAA failed for {location_id}: {e}")
            
        logger.error(f"All weather APIs failed for {location_id}")
        return None
        
    async def _fetch_openweathermap_current(self, location_id: str, location_data: Dict[str, Any]) -> Optional[WeatherReading]:
        """Fetch current weather from OpenWeatherMap API"""
        
        if not self.api_keys['openweathermap']:
            return None
            
        url = "http://api.openweathermap.org/data/2.5/weather"
        params = {
            'lat': location_data['latitude'],
            'lon': location_data['longitude'],
            'appid': self.api_keys['openweathermap'],
            'units': 'imperial'  # Fahrenheit
        }
        
        start_time = time.time()
        
        try:
            async with self.api_sessions['openweathermap'].get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Record metrics
                    self.quality_metrics['successful_requests'] += 1
                    self.quality_metrics['api_response_times'].append(time.time() - start_time)
                    
                    # Convert to standard format
                    return WeatherReading(
                        timestamp=datetime.now(),
                        location_id=location_id,
                        location_name=location_data['name'],
                        latitude=location_data['latitude'],
                        longitude=location_data['longitude'],
                        temperature=data['main']['temp'],
                        humidity=data['main']['humidity'],
                        pressure=data['main']['pressure'] * 0.02953,  # hPa to inHg
                        wind_speed=data.get('wind', {}).get('speed', 0),
                        wind_direction=data.get('wind', {}).get('deg', 0),
                        precipitation=data.get('rain', {}).get('1h', 0) * 0.0394,  # mm to inches
                        visibility=data.get('visibility', 10000) * 0.000621371,  # meters to miles
                        uv_index=0,  # Not available in current weather
                        weather_condition=data['weather'][0]['description'],
                        weather_code=data['weather'][0]['id'],
                        data_source='openweathermap',
                        quality_score=self._calculate_quality_score(data)
                    )
                else:
                    logger.error(f"OpenWeatherMap API error: {response.status}")
                    self.quality_metrics['failed_requests'] += 1
                    return None
                    
        except Exception as e:
            logger.error(f"OpenWeatherMap request error: {e}")
            self.quality_metrics['failed_requests'] += 1
            return None
        
    async def _fetch_weatherapi_current(self, location_id: str, location_data: Dict[str, Any]) -> Optional[WeatherReading]:
        """Fetch current weather from WeatherAPI"""
        
        if not self.api_keys['weatherapi']:
            return None
            
        url = "http://api.weatherapi.com/v1/current.json"
        params = {
            'key': self.api_keys['weatherapi'],
            'q': f"{location_data['latitude']},{location_data['longitude']}",
            'aqi': 'no'
        }
        
        try:
            async with self.api_sessions['weatherapi'].get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    current = data['current']
                    
                    return WeatherReading(
                        timestamp=datetime.now(),
                        location_id=location_id,
                        location_name=location_data['name'],
                        latitude=location_data['latitude'],
                        longitude=location_data['longitude'],
                        temperature=current['temp_f'],
                        humidity=current['humidity'],
                        pressure=current['pressure_in'],
                        wind_speed=current['wind_mph'],
                        wind_direction=current['wind_degree'],
                        precipitation=current.get('precip_in', 0),
                        visibility=current['vis_miles'],
                        uv_index=current['uv'],
                        weather_condition=current['condition']['text'],
                        weather_code=current['condition']['code'],
                        data_source='weatherapi',
                        quality_score=self._calculate_quality_score(current)
                    )
                    
        except Exception as e:
            logger.error(f"WeatherAPI request error: {e}")
            return None
            
    async def _fetch_noaa_current(self, location_id: str, location_data: Dict[str, Any]) -> Optional[WeatherReading]:
        """Fetch current weather from NOAA API"""
        
        # NOAA API implementation would go here
        # Placeholder for now
        logger.info(f"NOAA API not implemented yet for {location_id}")
        return None
        
    def _calculate_quality_score(self, data: Dict[str, Any]) -> float:
        """Calculate data quality score based on completeness and consistency"""
        
        required_fields = ['temp', 'humidity', 'pressure']
        optional_fields = ['wind_speed', 'visibility', 'precipitation']
        
        # Check required fields
        required_score = sum(1 for field in required_fields if field in str(data)) / len(required_fields)
        
        # Check optional fields  
        optional_score = sum(1 for field in optional_fields if field in str(data)) / len(optional_fields)
        
        # Overall quality score
        quality_score = required_score * 0.8 + optional_score * 0.2
        
        return quality_score
        
    async def _process_weather_reading(self, weather: WeatherReading):
        """Process weather reading and trigger production correlations"""
        
        # Store in MongoDB
        await self._store_weather_reading(weather)
        
        # Cache in Redis for real-time access
        await self._cache_weather_reading(weather)
        
        # Stream to Kafka for real-time processing
        await self._stream_weather_reading(weather)
        
        # Check for alerts
        alerts = await self._check_weather_alerts(weather)
        
        # Process any alerts
        for alert in alerts:
            await self._process_weather_alert(alert)
            
        # Update quality metrics
        self.quality_metrics['data_quality_scores'].append(weather.quality_score)
        
    async def _store_weather_reading(self, weather: WeatherReading):
        """Store weather reading in MongoDB"""
        
        try:
            collection = self.db.weather_readings
            document = asdict(weather)
            await asyncio.get_event_loop().run_in_executor(
                self.executor, 
                collection.insert_one, 
                document
            )
            
        except Exception as e:
            logger.error(f"Failed to store weather reading: {e}")
            
    async def _cache_weather_reading(self, weather: WeatherReading):
        """Cache latest weather reading in Redis"""
        
        try:
            cache_key = f"weather:current:{weather.location_id}"
            cache_data = asdict(weather)
            
            await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.redis_client.setex,
                cache_key,
                3600,  # 1 hour expiration
                json.dumps(cache_data, default=str)
            )
            
        except Exception as e:
            logger.error(f"Failed to cache weather reading: {e}")
            
    async def _stream_weather_reading(self, weather: WeatherReading):
        """Stream weather reading to Kafka"""
        
        try:
            kafka_message = {
                'type': 'weather_reading',
                'data': asdict(weather),
                'timestamp': datetime.now().isoformat()
            }
            
            await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.kafka_producer.send,
                'weather-data',
                kafka_message
            )
            
        except Exception as e:
            logger.error(f"Failed to stream weather reading: {e}")
            
    async def _check_weather_alerts(self, weather: WeatherReading) -> List[WeatherAlert]:
        """Check weather conditions against alert thresholds"""
        
        alerts = []
        
        # Temperature alerts
        if weather.temperature > 95:
            alerts.append(WeatherAlert(
                alert_id=f"temp_high_{weather.location_id}_{int(time.time())}",
                location_id=weather.location_id,
                alert_type="TEMPERATURE",
                severity="CRITICAL",
                message=f"Extreme temperature {weather.temperature:.1f}°F at {weather.location_name}",
                recommended_actions=[
                    "Consider production hold",
                    "Activate enhanced cooling systems", 
                    "Monitor equipment temperatures"
                ],
                production_impact="HIGH - Efficiency drop expected",
                valid_until=datetime.now() + timedelta(hours=2)
            ))
        elif weather.temperature > 85:
            alerts.append(WeatherAlert(
                alert_id=f"temp_high_{weather.location_id}_{int(time.time())}",
                location_id=weather.location_id,
                alert_type="TEMPERATURE",
                severity="HIGH",
                message=f"High temperature {weather.temperature:.1f}°F at {weather.location_name}",
                recommended_actions=[
                    "Reduce dryer temperature by 10°F",
                    "Increase cooling system load",
                    "Monitor production efficiency"
                ],
                production_impact="MEDIUM - 10-15% efficiency reduction",
                valid_until=datetime.now() + timedelta(hours=1)
            ))
            
        # Humidity alerts
        if weather.humidity > 75:
            alerts.append(WeatherAlert(
                alert_id=f"humidity_high_{weather.location_id}_{int(time.time())}",
                location_id=weather.location_id,
                alert_type="HUMIDITY",
                severity="HIGH",
                message=f"High humidity {weather.humidity:.1f}% at {weather.location_name}",
                recommended_actions=[
                    "Increase pre-mix time by 20%",
                    "Activate dehumidification systems",
                    "Monitor curing quality closely"
                ],
                production_impact="HIGH - Curing time increase expected",
                valid_until=datetime.now() + timedelta(hours=2)
            ))
            
        # Pressure change alerts (need historical data)
        pressure_cache_key = f"weather:pressure_history:{weather.location_id}"
        try:
            cached_pressures = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.redis_client.lrange,
                pressure_cache_key,
                0, 10
            )
            
            if cached_pressures:
                recent_pressures = [float(p) for p in cached_pressures]
                pressure_change = weather.pressure - recent_pressures[0] if recent_pressures else 0
                
                if abs(pressure_change) > 0.15:  # Significant pressure change
                    alerts.append(WeatherAlert(
                        alert_id=f"pressure_change_{weather.location_id}_{int(time.time())}",
                        location_id=weather.location_id,
                        alert_type="PRESSURE",
                        severity="MEDIUM",
                        message=f"Rapid pressure change {pressure_change:+.2f} inHg at {weather.location_name}",
                        recommended_actions=[
                            "Adjust hold/release timing",
                            "Monitor material handling",
                            "Prepare for weather front"
                        ],
                        production_impact="MEDIUM - Material handling affected",
                        valid_until=datetime.now() + timedelta(hours=4)
                    ))
                    
            # Update pressure history
            await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.redis_client.lpush,
                pressure_cache_key,
                weather.pressure
            )
            await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.redis_client.ltrim,
                pressure_cache_key,
                0, 20  # Keep last 20 readings
            )
            
        except Exception as e:
            logger.error(f"Failed to check pressure history: {e}")
            
        return alerts
        
    async def _process_weather_alert(self, alert: WeatherAlert):
        """Process weather alert and notify production systems"""
        
        # Store alert in database
        try:
            collection = self.db.weather_alerts
            document = asdict(alert)
            await asyncio.get_event_loop().run_in_executor(
                self.executor,
                collection.insert_one,
                document
            )
        except Exception as e:
            logger.error(f"Failed to store weather alert: {e}")
            
        # Stream alert to Kafka
        try:
            kafka_message = {
                'type': 'weather_alert',
                'data': asdict(alert),
                'timestamp': datetime.now().isoformat()
            }
            
            await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.kafka_producer.send,
                'weather-alerts',
                kafka_message
            )
            
        except Exception as e:
            logger.error(f"Failed to stream weather alert: {e}")
            
        logger.info(f"Weather alert processed: {alert.alert_type} - {alert.severity} - {alert.location_id}")
        
    async def _forecast_loop(self):
        """Periodic weather forecast updates"""
        logger.info("Starting weather forecast monitoring loop")
        
        while True:
            try:
                # Fetch forecasts for all locations
                for location_id, location_data in self.locations.items():
                    forecast = await self._fetch_weather_forecast(location_id, location_data)
                    if forecast:
                        await self._process_weather_forecast(location_id, forecast)
                        
                await asyncio.sleep(self.config['polling_intervals']['forecast'])
                
            except Exception as e:
                logger.error(f"Error in forecast loop: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retry
                
    async def _fetch_weather_forecast(self, location_id: str, location_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Fetch weather forecast for production planning"""
        
        # Implementation for forecast fetching
        # Would fetch 48-hour forecast from weather APIs
        logger.info(f"Fetching forecast for {location_id}")
        return None  # Placeholder
        
    async def _weather_alerts_loop(self):
        """Monitor for severe weather alerts"""
        logger.info("Starting weather alerts monitoring loop")
        
        while True:
            try:
                # Check for severe weather alerts
                await asyncio.sleep(self.config['polling_intervals']['alerts'])
                
            except Exception as e:
                logger.error(f"Error in alerts loop: {e}")
                await asyncio.sleep(60)
                
    async def _data_quality_monitor(self):
        """Monitor data quality and API performance"""
        logger.info("Starting data quality monitoring")
        
        while True:
            try:
                # Calculate quality metrics
                if self.quality_metrics['api_response_times']:
                    avg_response_time = np.mean(self.quality_metrics['api_response_times'][-100:])
                    success_rate = (self.quality_metrics['successful_requests'] / 
                                  max(1, self.quality_metrics['total_requests']))
                    avg_quality_score = np.mean(self.quality_metrics['data_quality_scores'][-100:])
                    
                    logger.info(f"Data Quality Metrics - Success Rate: {success_rate:.2%}, "
                              f"Avg Response Time: {avg_response_time:.2f}s, "
                              f"Avg Quality Score: {avg_quality_score:.2f}")
                              
                await asyncio.sleep(3600)  # Report every hour
                
            except Exception as e:
                logger.error(f"Error in quality monitor: {e}")
                await asyncio.sleep(300)
                
    async def _production_correlation_processor(self):
        """Process weather-production correlations in real-time"""
        logger.info("Starting production correlation processor")
        
        while True:
            try:
                # This would integrate with production systems
                # to correlate weather with production performance
                await asyncio.sleep(300)  # Process every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in correlation processor: {e}")
                await asyncio.sleep(60)
                
    async def shutdown(self):
        """Gracefully shutdown the pipeline"""
        logger.info("Shutting down weather data pipeline...")
        
        # Close HTTP sessions
        for session in self.api_sessions.values():
            await session.close()
            
        # Close other connections
        self.kafka_producer.close()
        self.redis_client.close()
        self.mongo_client.close()
        
        logger.info("Weather data pipeline shutdown complete")


async def main():
    """Main pipeline execution"""
    
    pipeline = WeatherDataPipeline()
    
    try:
        await pipeline.start_pipeline()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        await pipeline.shutdown()


if __name__ == "__main__":
    asyncio.run(main())