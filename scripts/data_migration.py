#!/usr/bin/env python3
"""
Weather AI Profile - Data Migration and Backfill Tool
Handles migration of existing APMS data and backfilling weather data
"""

import asyncio
import argparse
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import sys
import os

# Add project root to Python path
sys.path.append(str(Path(__file__).parent.parent))

from pymongo import MongoClient
import pandas as pd
import aiohttp
import numpy as np
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/data_migration.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class WeatherDataMigration:
    """Handles weather data migration and backfill operations"""
    
    def __init__(self, config_file: str = "config/development.json"):
        self.config = self._load_config(config_file)
        self.mongo_client = MongoClient(self.config['mongodb']['uri'])
        self.db = self.mongo_client[self.config['mongodb']['database']]
        
        # Weather API configuration
        self.weather_api_key = os.getenv('OPENWEATHERMAP_API_KEY')
        if not self.weather_api_key or self.weather_api_key == 'your_api_key_here':
            logger.warning("Weather API key not configured - using mock data")
            self.use_mock_data = True
        else:
            self.use_mock_data = False
            
        self.locations = self.config['locations']
        
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Configuration file {config_file} not found")
            sys.exit(1)
            
    def migrate_apms_data(self, dump_path: str = "./dump/") -> bool:
        """Migrate existing APMS data to weather AI collections"""
        
        logger.info("Starting APMS data migration...")
        
        try:
            # Migrate timerlogs
            self._migrate_timerlogs(dump_path)
            
            # Migrate machines
            self._migrate_machines(dump_path)
            
            # Migrate parts
            self._migrate_parts(dump_path)
            
            # Migrate locations
            self._migrate_locations(dump_path)
            
            # Create indexes for performance
            self._create_indexes()
            
            logger.info("APMS data migration completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"APMS data migration failed: {e}")
            return False
    
    def _migrate_timerlogs(self, dump_path: str):
        """Migrate timerlog data from BSON dumps"""
        
        logger.info("Migrating timerlogs...")
        
        # Check for different dump locations
        timerlog_files = [
            f"{dump_path}/apms/timerlogs.bson",
            f"{dump_path}/apms-today/timerlogs.bson"
        ]
        
        total_migrated = 0
        
        for file_path in timerlog_files:
            if os.path.exists(file_path):
                logger.info(f"Processing {file_path}...")
                
                # Use bsondump to convert to JSON and process
                import subprocess
                
                result = subprocess.run(
                    ['bsondump', file_path],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    # Process each line (JSON document)
                    for line in result.stdout.split('\n'):
                        if line.strip():
                            try:
                                doc = json.loads(line)
                                
                                # Enhance document with weather correlation placeholders
                                enhanced_doc = self._enhance_timerlog(doc)
                                
                                # Insert into weather AI collection
                                self.db.enhanced_production_events.insert_one(enhanced_doc)
                                total_migrated += 1
                                
                                if total_migrated % 1000 == 0:
                                    logger.info(f"Migrated {total_migrated} timerlogs...")
                                    
                            except json.JSONDecodeError:
                                logger.warning(f"Skipping invalid JSON line")
                                continue
                else:
                    logger.error(f"Failed to process {file_path}: {result.stderr}")
        
        logger.info(f"Total timerlogs migrated: {total_migrated}")
    
    def _enhance_timerlog(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance timerlog with weather correlation structure"""
        
        enhanced = doc.copy()
        
        # Add weather context placeholder
        enhanced['weather_context'] = {
            'temperature': None,
            'humidity': None,
            'pressure': None,
            'data_source': 'backfill_pending',
            'correlation_ready': False
        }
        
        # Add analysis fields
        enhanced['analysis'] = {
            'weather_correlation_score': None,
            'primary_weather_factor': None,
            'optimization_potential': None,
            'processed_at': datetime.now()
        }
        
        # Convert timestamp fields
        if 'createdAt' in enhanced and '$date' in enhanced['createdAt']:
            enhanced['timestamp'] = datetime.fromtimestamp(
                enhanced['createdAt']['$date']['$numberLong'] / 1000
            )
        
        return enhanced
    
    def _migrate_machines(self, dump_path: str):
        """Migrate machine data"""
        
        logger.info("Migrating machines...")
        
        machines_file = f"{dump_path}/apms/machines.bson"
        if os.path.exists(machines_file):
            
            import subprocess
            result = subprocess.run(['bsondump', machines_file], capture_output=True, text=True)
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.strip():
                        try:
                            doc = json.loads(line)
                            
                            # Enhance with weather sensitivity data
                            enhanced = self._enhance_machine(doc)
                            
                            self.db.machines.insert_one(enhanced)
                            
                        except json.JSONDecodeError:
                            continue
                            
        logger.info("Machine migration completed")
    
    def _enhance_machine(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance machine with weather sensitivity profile"""
        
        enhanced = doc.copy()
        
        # Determine weather sensitivity based on machine name/class
        machine_name = enhanced.get('name', '').upper()
        
        if 'RP' in machine_name:
            # RP Series - High humidity sensitivity
            weather_profile = {
                'weather_sensitivity': 'HIGH',
                'primary_factors': ['humidity', 'temperature'],
                'correlation_coefficients': {
                    'humidity_cycle_time': 0.73,
                    'temperature_efficiency': -0.47,
                    'pressure_quality': 0.31
                },
                'optimal_conditions': {
                    'temperature_range': [75, 85],
                    'humidity_range': [45, 65],
                    'pressure_range': [29.8, 30.2]
                }
            }
        elif 'VARIANT' in machine_name:
            # Variant Series - Temperature sensitive
            weather_profile = {
                'weather_sensitivity': 'MEDIUM',
                'primary_factors': ['temperature', 'humidity'],
                'correlation_coefficients': {
                    'temperature_efficiency': -0.68,
                    'humidity_cycle_time': 0.45,
                    'pressure_quality': 0.25
                },
                'optimal_conditions': {
                    'temperature_range': [70, 82],
                    'humidity_range': [40, 70],
                    'pressure_range': [29.7, 30.3]
                }
            }
        elif 'MBK' in machine_name:
            # MBK Series - Pressure sensitive
            weather_profile = {
                'weather_sensitivity': 'MEDIUM',
                'primary_factors': ['pressure', 'humidity'],
                'correlation_coefficients': {
                    'pressure_quality': 0.65,
                    'humidity_cycle_time': 0.52,
                    'temperature_efficiency': -0.35
                },
                'optimal_conditions': {
                    'temperature_range': [72, 88],
                    'humidity_range': [35, 75],
                    'pressure_range': [29.9, 30.1]
                }
            }
        else:
            # Default profile
            weather_profile = {
                'weather_sensitivity': 'LOW',
                'primary_factors': ['temperature'],
                'correlation_coefficients': {
                    'temperature_efficiency': -0.25,
                    'humidity_cycle_time': 0.15,
                    'pressure_quality': 0.10
                },
                'optimal_conditions': {
                    'temperature_range': [65, 90],
                    'humidity_range': [30, 80],
                    'pressure_range': [29.5, 30.5]
                }
            }
        
        enhanced['weather_profile'] = weather_profile
        enhanced['migration_timestamp'] = datetime.now()
        
        return enhanced
    
    def _migrate_parts(self, dump_path: str):
        """Migrate parts data with weather sensitivity"""
        
        logger.info("Migrating parts...")
        
        parts_file = f"{dump_path}/apms/parts.bson"
        if os.path.exists(parts_file):
            
            import subprocess
            result = subprocess.run(['bsondump', parts_file], capture_output=True, text=True)
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.strip():
                        try:
                            doc = json.loads(line)
                            enhanced = self._enhance_part(doc)
                            self.db.parts.insert_one(enhanced)
                            
                        except json.JSONDecodeError:
                            continue
                            
        logger.info("Parts migration completed")
    
    def _enhance_part(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance part with weather-sensitive properties"""
        
        enhanced = doc.copy()
        
        # Add weather sensitivity based on material type
        part_name = enhanced.get('name', '').upper()
        
        if 'RUBBER' in part_name or 'GASKET' in part_name:
            weather_sensitivity = {
                'material_type': 'rubber',
                'humidity_sensitive': True,
                'temperature_sensitive': True,
                'pressure_sensitive': False,
                'weather_adjustments': {
                    'high_humidity_cure_factor': 1.25,
                    'low_humidity_cure_factor': 0.90,
                    'high_temp_expansion_factor': 1.15,
                    'low_temp_shrinkage_factor': 0.95
                }
            }
        else:
            weather_sensitivity = {
                'material_type': 'standard',
                'humidity_sensitive': False,
                'temperature_sensitive': True,
                'pressure_sensitive': False,
                'weather_adjustments': {
                    'high_temp_expansion_factor': 1.05,
                    'low_temp_shrinkage_factor': 0.98
                }
            }
        
        enhanced['weather_sensitivity'] = weather_sensitivity
        enhanced['migration_timestamp'] = datetime.now()
        
        return enhanced
    
    def _migrate_locations(self, dump_path: str):
        """Migrate location data"""
        
        logger.info("Migrating locations...")
        
        # Use configured locations with weather enhancement
        for location_id, location_data in self.locations.items():
            enhanced_location = location_data.copy()
            
            # Add weather monitoring configuration
            enhanced_location.update({
                'location_id': location_id,
                'weather_monitoring': {
                    'enabled': True,
                    'update_frequency': 900,  # 15 minutes
                    'data_sources': ['openweathermap', 'noaa'],
                    'sensor_integration': False  # To be enabled when sensors installed
                },
                'alert_thresholds': {
                    'temperature': {'high': 85, 'critical': 95},
                    'humidity': {'high': 70, 'critical': 85},
                    'pressure_change_rate': {'medium': 0.10, 'high': 0.20}
                },
                'production_priority': self._get_location_priority(location_id),
                'migration_timestamp': datetime.now()
            })
            
            self.db.locations.insert_one(enhanced_location)
            
        logger.info("Locations migration completed")
    
    def _get_location_priority(self, location_id: str) -> str:
        """Determine production priority for location"""
        if location_id == 'seguin_tx':
            return 'HIGH'
        elif location_id == 'conroe_tx':
            return 'MEDIUM'
        else:
            return 'MEDIUM'
    
    def _create_indexes(self):
        """Create database indexes for performance"""
        
        logger.info("Creating database indexes...")
        
        # Enhanced production events indexes
        self.db.enhanced_production_events.create_index([
            ('location_id', 1),
            ('timestamp', -1)
        ])
        self.db.enhanced_production_events.create_index([
            ('machine_id', 1),
            ('timestamp', -1)
        ])
        self.db.enhanced_production_events.create_index([
            ('weather_context.correlation_ready', 1),
            ('timestamp', -1)
        ])
        
        # Weather readings indexes
        self.db.weather_readings.create_index([
            ('location_id', 1),
            ('timestamp', -1)
        ])
        self.db.weather_readings.create_index([
            ('data_source', 1),
            ('timestamp', -1)
        ])
        
        # Optimization indexes
        self.db.production_optimizations.create_index([
            ('location_id', 1),
            ('timestamp', -1)
        ])
        self.db.production_optimizations.create_index([
            ('confidence_score', -1),
            ('timestamp', -1)
        ])
        
        logger.info("Database indexes created")
    
    async def backfill_weather_data(self, start_date: datetime, end_date: datetime, 
                                   batch_size: int = 100) -> bool:
        """Backfill historical weather data"""
        
        logger.info(f"Starting weather data backfill from {start_date} to {end_date}")
        
        if self.use_mock_data:
            return await self._backfill_mock_weather_data(start_date, end_date)
        else:
            return await self._backfill_real_weather_data(start_date, end_date, batch_size)
    
    async def _backfill_mock_weather_data(self, start_date: datetime, end_date: datetime) -> bool:
        """Generate mock weather data for development"""
        
        logger.info("Generating mock weather data...")
        
        current_date = start_date
        total_records = 0
        
        while current_date <= end_date:
            for location_id, location_data in self.locations.items():
                
                # Generate realistic weather data for Texas
                mock_weather = self._generate_mock_weather(current_date, location_data)
                
                # Insert weather reading
                self.db.weather_readings.insert_one({
                    'timestamp': current_date,
                    'location_id': location_id,
                    'location_name': location_data['name'],
                    'latitude': location_data['latitude'],
                    'longitude': location_data['longitude'],
                    'temperature': mock_weather['temperature'],
                    'humidity': mock_weather['humidity'],
                    'pressure': mock_weather['pressure'],
                    'wind_speed': mock_weather['wind_speed'],
                    'precipitation': mock_weather['precipitation'],
                    'weather_condition': mock_weather['condition'],
                    'data_source': 'mock_generator',
                    'quality_score': 1.0
                })
                
                total_records += 1
                
                if total_records % 1000 == 0:
                    logger.info(f"Generated {total_records} mock weather records...")
            
            # Move to next hour
            current_date += timedelta(hours=1)
        
        logger.info(f"Mock weather data generation completed: {total_records} records")
        return True
    
    def _generate_mock_weather(self, timestamp: datetime, location_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate realistic mock weather data for Texas location"""
        
        # Base seasonal patterns for Texas
        month = timestamp.month
        hour = timestamp.hour
        
        # Temperature patterns (Fahrenheit)
        if month in [6, 7, 8]:  # Summer
            base_temp = 85 + np.random.normal(0, 8)
        elif month in [12, 1, 2]:  # Winter
            base_temp = 55 + np.random.normal(0, 12)
        elif month in [3, 4, 5]:  # Spring
            base_temp = 72 + np.random.normal(0, 10)
        else:  # Fall
            base_temp = 68 + np.random.normal(0, 8)
            
        # Daily temperature variation
        daily_variation = 15 * np.cos((hour - 14) * np.pi / 12)  # Peak at 2 PM
        temperature = base_temp + daily_variation
        
        # Humidity patterns (higher in summer)
        if month in [6, 7, 8]:
            base_humidity = 65 + np.random.normal(0, 15)
        else:
            base_humidity = 55 + np.random.normal(0, 12)
            
        humidity = max(20, min(95, base_humidity))
        
        # Pressure patterns
        base_pressure = 29.95 + np.random.normal(0, 0.15)
        pressure = max(29.5, min(30.5, base_pressure))
        
        # Wind and precipitation
        wind_speed = max(0, np.random.exponential(8))
        precipitation = max(0, np.random.exponential(0.1)) if np.random.random() < 0.15 else 0
        
        # Weather condition based on other factors
        if precipitation > 0.1:
            condition = "Rain"
        elif humidity > 80:
            condition = "Cloudy"
        elif temperature > 90:
            condition = "Hot"
        else:
            condition = "Clear"
        
        return {
            'temperature': round(temperature, 1),
            'humidity': round(humidity, 1),
            'pressure': round(pressure, 2),
            'wind_speed': round(wind_speed, 1),
            'precipitation': round(precipitation, 2),
            'condition': condition
        }
    
    async def _backfill_real_weather_data(self, start_date: datetime, end_date: datetime,
                                         batch_size: int) -> bool:
        """Backfill real weather data from APIs"""
        
        logger.info("Backfilling real weather data...")
        
        # Note: OpenWeatherMap's free plan doesn't provide extensive historical data
        # This would require a paid plan or alternative data source
        
        logger.warning("Real weather data backfill requires paid API plan - using mock data")
        return await self._backfill_mock_weather_data(start_date, end_date)
    
    def correlate_production_weather(self, batch_size: int = 1000) -> bool:
        """Correlate existing production events with weather data"""
        
        logger.info("Starting production-weather correlation...")
        
        try:
            # Find production events without weather correlation
            uncorrelated_events = self.db.enhanced_production_events.find({
                'weather_context.correlation_ready': False
            }).limit(batch_size)
            
            correlated_count = 0
            
            for event in uncorrelated_events:
                # Find weather data within 30 minutes of production event
                event_time = event.get('timestamp')
                if not event_time:
                    continue
                    
                location_id = event.get('location_id')
                if not location_id:
                    continue
                
                # Find closest weather reading
                weather_data = self.db.weather_readings.find_one({
                    'location_id': location_id,
                    'timestamp': {
                        '$gte': event_time - timedelta(minutes=30),
                        '$lte': event_time + timedelta(minutes=30)
                    }
                }, sort=[('timestamp', 1)])
                
                if weather_data:
                    # Update event with weather context
                    self.db.enhanced_production_events.update_one(
                        {'_id': event['_id']},
                        {
                            '$set': {
                                'weather_context': {
                                    'temperature': weather_data['temperature'],
                                    'humidity': weather_data['humidity'],
                                    'pressure': weather_data['pressure'],
                                    'weather_condition': weather_data.get('weather_condition', 'unknown'),
                                    'data_source': weather_data['data_source'],
                                    'correlation_ready': True,
                                    'data_age_minutes': abs((weather_data['timestamp'] - event_time).total_seconds() / 60)
                                }
                            }
                        }
                    )
                    
                    correlated_count += 1
                    
                    if correlated_count % 100 == 0:
                        logger.info(f"Correlated {correlated_count} production events...")
            
            logger.info(f"Production-weather correlation completed: {correlated_count} events")
            return True
            
        except Exception as e:
            logger.error(f"Production-weather correlation failed: {e}")
            return False
    
    def generate_migration_report(self) -> Dict[str, Any]:
        """Generate migration status report"""
        
        report = {
            'migration_timestamp': datetime.now().isoformat(),
            'collections': {},
            'data_quality': {},
            'recommendations': []
        }
        
        # Check collection counts
        collections = [
            'enhanced_production_events',
            'weather_readings',
            'machines',
            'parts',
            'locations'
        ]
        
        for collection in collections:
            count = self.db[collection].count_documents({})
            report['collections'][collection] = count
            
            if count == 0:
                report['recommendations'].append(f"Collection {collection} is empty - migration may have failed")
        
        # Check data quality
        # Weather correlation coverage
        total_events = report['collections'].get('enhanced_production_events', 0)
        if total_events > 0:
            correlated_events = self.db.enhanced_production_events.count_documents({
                'weather_context.correlation_ready': True
            })
            
            correlation_coverage = correlated_events / total_events
            report['data_quality']['weather_correlation_coverage'] = correlation_coverage
            
            if correlation_coverage < 0.8:
                report['recommendations'].append("Low weather correlation coverage - consider running correlation process")
        
        # Check weather data coverage
        weather_count = report['collections'].get('weather_readings', 0)
        if weather_count > 0:
            latest_weather = self.db.weather_readings.find_one(sort=[('timestamp', -1)])
            oldest_weather = self.db.weather_readings.find_one(sort=[('timestamp', 1)])
            
            if latest_weather and oldest_weather:
                coverage_days = (latest_weather['timestamp'] - oldest_weather['timestamp']).days
                report['data_quality']['weather_coverage_days'] = coverage_days
                
                if coverage_days < 30:
                    report['recommendations'].append("Limited weather data coverage - consider extending backfill period")
        
        return report


async def main():
    """Main migration execution"""
    
    parser = argparse.ArgumentParser(description='Weather AI Profile Data Migration Tool')
    parser.add_argument('--config', default='config/development.json', 
                       help='Configuration file path')
    parser.add_argument('--dump-path', default='./dump/', 
                       help='Path to APMS dump files')
    parser.add_argument('--start-date', type=str,
                       help='Start date for weather backfill (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str,
                       help='End date for weather backfill (YYYY-MM-DD)')
    parser.add_argument('--operation', choices=['migrate', 'backfill', 'correlate', 'all'],
                       default='all', help='Migration operation to perform')
    parser.add_argument('--batch-size', type=int, default=1000,
                       help='Batch size for processing')
    
    args = parser.parse_args()
    
    # Initialize migration tool
    migrator = WeatherDataMigration(args.config)
    
    success = True
    
    if args.operation in ['migrate', 'all']:
        logger.info("=== Starting APMS Data Migration ===")
        success &= migrator.migrate_apms_data(args.dump_path)
    
    if args.operation in ['backfill', 'all'] and success:
        logger.info("=== Starting Weather Data Backfill ===")
        
        # Default to last 30 days if dates not specified
        if not args.start_date:
            start_date = datetime.now() - timedelta(days=30)
        else:
            start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
            
        if not args.end_date:
            end_date = datetime.now()
        else:
            end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
        
        success &= await migrator.backfill_weather_data(start_date, end_date, args.batch_size)
    
    if args.operation in ['correlate', 'all'] and success:
        logger.info("=== Starting Production-Weather Correlation ===")
        success &= migrator.correlate_production_weather(args.batch_size)
    
    # Generate report
    logger.info("=== Generating Migration Report ===")
    report = migrator.generate_migration_report()
    
    # Save report
    report_file = f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    logger.info(f"Migration report saved to {report_file}")
    
    # Print summary
    print("\n" + "="*60)
    print("MIGRATION SUMMARY")
    print("="*60)
    
    for collection, count in report['collections'].items():
        print(f"{collection:30}: {count:>10,} records")
    
    if report['data_quality']:
        print(f"\nData Quality:")
        for metric, value in report['data_quality'].items():
            if isinstance(value, float):
                print(f"{metric:30}: {value:>10.1%}")
            else:
                print(f"{metric:30}: {value:>10}")
    
    if report['recommendations']:
        print(f"\nRecommendations:")
        for i, rec in enumerate(report['recommendations'], 1):
            print(f"{i}. {rec}")
    
    print("="*60)
    
    if success:
        logger.info("Migration completed successfully!")
        sys.exit(0)
    else:
        logger.error("Migration completed with errors!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())