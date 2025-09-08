#!/usr/bin/env python3
"""
Weather Correlation Engine for Production Optimization
Advanced algorithms for correlating weather conditions with production performance
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import json
import logging
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class WeatherCondition:
    """Weather condition data structure"""
    timestamp: datetime
    location_id: str
    temperature: float  # Fahrenheit
    humidity: float     # Percentage
    pressure: float     # inHg
    wind_speed: float   # mph
    precipitation: float # inches
    weather_code: str   # weather condition code

@dataclass
class ProductionMetric:
    """Production performance metrics"""
    timestamp: datetime
    location_id: str
    machine_id: str
    cycle_time: float
    efficiency: float
    quality_score: float
    energy_usage: float
    status: str  # Gain/Loss
    operator_id: str

@dataclass
class CorrelationResult:
    """Weather-production correlation result"""
    weather_factor: str
    production_metric: str
    correlation_coefficient: float
    p_value: float
    significance_level: str
    confidence_interval: Tuple[float, float]
    sample_size: int

class WeatherCorrelationEngine:
    """Advanced engine for weather-production correlation analysis"""
    
    def __init__(self):
        self.weather_data: List[WeatherCondition] = []
        self.production_data: List[ProductionMetric] = []
        self.correlation_models = {}
        self.scaler = StandardScaler()
        
    def load_weather_data(self, weather_records: List[Dict[str, Any]]):
        """Load weather data for correlation analysis"""
        
        logger.info(f"Loading {len(weather_records)} weather records...")
        
        self.weather_data = [
            WeatherCondition(
                timestamp=datetime.fromisoformat(record['timestamp']),
                location_id=record['location_id'],
                temperature=record['temperature'],
                humidity=record['humidity'],
                pressure=record['pressure'],
                wind_speed=record.get('wind_speed', 0.0),
                precipitation=record.get('precipitation', 0.0),
                weather_code=record.get('weather_code', 'clear')
            )
            for record in weather_records
        ]
        
        logger.info(f"Loaded weather data for {len(set(w.location_id for w in self.weather_data))} locations")
        
    def load_production_data(self, production_records: List[Dict[str, Any]]):
        """Load production data for correlation analysis"""
        
        logger.info(f"Loading {len(production_records)} production records...")
        
        self.production_data = [
            ProductionMetric(
                timestamp=datetime.fromisoformat(record['timestamp']),
                location_id=record['location_id'],
                machine_id=record['machine_id'],
                cycle_time=record['cycle_time'],
                efficiency=record['efficiency'],
                quality_score=record['quality_score'],
                energy_usage=record['energy_usage'],
                status=record['status'],
                operator_id=record.get('operator_id', 'unknown')
            )
            for record in production_records
        ]
        
        logger.info(f"Loaded production data for {len(set(p.machine_id for p in self.production_data))} machines")
        
    def create_correlation_dataset(self, time_window_minutes: int = 60) -> pd.DataFrame:
        """Create aligned dataset for weather-production correlation"""
        
        logger.info(f"Creating correlation dataset with {time_window_minutes}-minute alignment...")
        
        # Create time-aligned dataset
        correlation_data = []
        
        for prod in self.production_data:
            # Find weather data within time window
            weather_matches = [
                w for w in self.weather_data
                if (w.location_id == prod.location_id and
                    abs((w.timestamp - prod.timestamp).total_seconds()) <= time_window_minutes * 60)
            ]
            
            if weather_matches:
                # Use closest weather reading
                closest_weather = min(weather_matches, 
                                    key=lambda w: abs((w.timestamp - prod.timestamp).total_seconds()))
                
                correlation_data.append({
                    'timestamp': prod.timestamp,
                    'location_id': prod.location_id,
                    'machine_id': prod.machine_id,
                    # Weather features
                    'temperature': closest_weather.temperature,
                    'humidity': closest_weather.humidity,
                    'pressure': closest_weather.pressure,
                    'wind_speed': closest_weather.wind_speed,
                    'precipitation': closest_weather.precipitation,
                    # Production features
                    'cycle_time': prod.cycle_time,
                    'efficiency': prod.efficiency,
                    'quality_score': prod.quality_score,
                    'energy_usage': prod.energy_usage,
                    'status_gain': 1 if prod.status == 'Gain' else 0,
                    'time_delta_minutes': abs((closest_weather.timestamp - prod.timestamp).total_seconds()) / 60
                })
        
        df = pd.DataFrame(correlation_data)
        logger.info(f"Created correlation dataset with {len(df)} aligned records")
        
        return df
        
    def calculate_correlation_matrix(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate comprehensive weather-production correlation matrix"""
        
        logger.info("Calculating correlation matrix...")
        
        weather_cols = ['temperature', 'humidity', 'pressure', 'wind_speed', 'precipitation']
        production_cols = ['cycle_time', 'efficiency', 'quality_score', 'energy_usage', 'status_gain']
        
        # Calculate Pearson correlations
        correlation_matrix = df[weather_cols + production_cols].corr()
        
        # Extract weather-production correlations
        weather_production_corr = correlation_matrix.loc[weather_cols, production_cols]
        
        return weather_production_corr
        
    def analyze_humidity_correlation(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detailed humidity correlation analysis"""
        
        logger.info("Analyzing humidity correlations...")
        
        # Humidity impact on cycle time
        humidity_cycle_corr = stats.pearsonr(df['humidity'], df['cycle_time'])
        
        # Humidity impact on efficiency
        humidity_efficiency_corr = stats.pearsonr(df['humidity'], df['efficiency'])
        
        # Humidity impact on quality
        humidity_quality_corr = stats.pearsonr(df['humidity'], df['quality_score'])
        
        # Categorize humidity levels
        df['humidity_category'] = pd.cut(df['humidity'], 
                                       bins=[0, 45, 65, 85, 100],
                                       labels=['Low', 'Optimal', 'High', 'Extreme'])
        
        # Performance by humidity category
        humidity_performance = df.groupby('humidity_category').agg({
            'cycle_time': ['mean', 'std'],
            'efficiency': ['mean', 'std'],
            'quality_score': ['mean', 'std'],
            'energy_usage': ['mean', 'std']
        }).round(2)
        
        analysis = {
            'cycle_time_correlation': {
                'coefficient': humidity_cycle_corr[0],
                'p_value': humidity_cycle_corr[1],
                'significance': 'significant' if humidity_cycle_corr[1] < 0.05 else 'not_significant'
            },
            'efficiency_correlation': {
                'coefficient': humidity_efficiency_corr[0],
                'p_value': humidity_efficiency_corr[1],
                'significance': 'significant' if humidity_efficiency_corr[1] < 0.05 else 'not_significant'
            },
            'quality_correlation': {
                'coefficient': humidity_quality_corr[0],
                'p_value': humidity_quality_corr[1],
                'significance': 'significant' if humidity_quality_corr[1] < 0.05 else 'not_significant'
            },
            'performance_by_category': humidity_performance.to_dict(),
            'optimal_range': self._find_optimal_humidity_range(df),
            'recommendations': self._generate_humidity_recommendations(df)
        }
        
        return analysis
        
    def analyze_temperature_correlation(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detailed temperature correlation analysis"""
        
        logger.info("Analyzing temperature correlations...")
        
        # Temperature impact analysis
        temp_efficiency_corr = stats.pearsonr(df['temperature'], df['efficiency'])
        temp_energy_corr = stats.pearsonr(df['temperature'], df['energy_usage'])
        temp_quality_corr = stats.pearsonr(df['temperature'], df['quality_score'])
        
        # Temperature categories
        df['temp_category'] = pd.cut(df['temperature'],
                                   bins=[0, 75, 85, 95, 150],
                                   labels=['Cool', 'Optimal', 'Hot', 'Extreme'])
        
        # Performance by temperature category
        temp_performance = df.groupby('temp_category').agg({
            'cycle_time': ['mean', 'std'],
            'efficiency': ['mean', 'std'],
            'quality_score': ['mean', 'std'],
            'energy_usage': ['mean', 'std']
        }).round(2)
        
        analysis = {
            'efficiency_correlation': {
                'coefficient': temp_efficiency_corr[0],
                'p_value': temp_efficiency_corr[1],
                'significance': 'significant' if temp_efficiency_corr[1] < 0.05 else 'not_significant'
            },
            'energy_correlation': {
                'coefficient': temp_energy_corr[0],
                'p_value': temp_energy_corr[1],
                'significance': 'significant' if temp_energy_corr[1] < 0.05 else 'not_significant'
            },
            'quality_correlation': {
                'coefficient': temp_quality_corr[0],
                'p_value': temp_quality_corr[1],
                'significance': 'significant' if temp_quality_corr[1] < 0.05 else 'not_significant'
            },
            'performance_by_category': temp_performance.to_dict(),
            'optimal_range': self._find_optimal_temperature_range(df),
            'energy_efficiency_curve': self._calculate_temperature_efficiency_curve(df),
            'recommendations': self._generate_temperature_recommendations(df)
        }
        
        return analysis
        
    def analyze_pressure_correlation(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detailed barometric pressure correlation analysis"""
        
        logger.info("Analyzing pressure correlations...")
        
        # Pressure impact analysis
        pressure_quality_corr = stats.pearsonr(df['pressure'], df['quality_score'])
        pressure_cycle_corr = stats.pearsonr(df['pressure'], df['cycle_time'])
        
        # Pressure change analysis (rate of change)
        df_sorted = df.sort_values(['location_id', 'timestamp'])
        df_sorted['pressure_change'] = df_sorted.groupby('location_id')['pressure'].diff()
        
        # Impact of pressure changes
        pressure_change_impact = df_sorted[df_sorted['pressure_change'].notna()].groupby(
            pd.cut(df_sorted['pressure_change'], bins=5)
        ).agg({
            'quality_score': 'mean',
            'cycle_time': 'mean',
            'efficiency': 'mean'
        }).round(2)
        
        analysis = {
            'quality_correlation': {
                'coefficient': pressure_quality_corr[0],
                'p_value': pressure_quality_corr[1],
                'significance': 'significant' if pressure_quality_corr[1] < 0.05 else 'not_significant'
            },
            'cycle_time_correlation': {
                'coefficient': pressure_cycle_corr[0],
                'p_value': pressure_cycle_corr[1],
                'significance': 'significant' if pressure_cycle_corr[1] < 0.05 else 'not_significant'
            },
            'pressure_change_impact': pressure_change_impact.to_dict(),
            'optimal_pressure_range': self._find_optimal_pressure_range(df),
            'weather_front_detection': self._detect_weather_fronts(df),
            'recommendations': self._generate_pressure_recommendations(df)
        }
        
        return analysis
        
    def build_prediction_models(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Build ML models for weather-based production prediction"""
        
        logger.info("Building prediction models...")
        
        weather_features = ['temperature', 'humidity', 'pressure', 'wind_speed', 'precipitation']
        
        models = {}
        
        # Cycle time prediction model
        models['cycle_time'] = self._build_regression_model(
            df, weather_features, 'cycle_time', 'Cycle Time Prediction'
        )
        
        # Efficiency prediction model
        models['efficiency'] = self._build_regression_model(
            df, weather_features, 'efficiency', 'Efficiency Prediction'
        )
        
        # Quality prediction model
        models['quality'] = self._build_regression_model(
            df, weather_features, 'quality_score', 'Quality Prediction'
        )
        
        # Energy usage prediction model
        models['energy'] = self._build_regression_model(
            df, weather_features, 'energy_usage', 'Energy Usage Prediction'
        )
        
        return models
        
    def _build_regression_model(self, df: pd.DataFrame, features: List[str], 
                               target: str, model_name: str) -> Dict[str, Any]:
        """Build and evaluate regression model"""
        
        # Prepare data
        X = df[features].fillna(df[features].mean())
        y = df[target].fillna(df[target].mean())
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train model
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X_scaled, y)
        
        # Make predictions
        y_pred = model.predict(X_scaled)
        
        # Calculate metrics
        mae = mean_absolute_error(y, y_pred)
        r2 = r2_score(y, y_pred)
        
        # Feature importance
        feature_importance = dict(zip(features, model.feature_importances_))
        
        return {
            'model_name': model_name,
            'model': model,
            'performance': {
                'mae': mae,
                'r2_score': r2,
                'rmse': np.sqrt(np.mean((y - y_pred) ** 2))
            },
            'feature_importance': feature_importance,
            'most_important_feature': max(feature_importance, key=feature_importance.get)
        }
        
    def generate_optimization_rules(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate weather-based optimization rules"""
        
        logger.info("Generating optimization rules...")
        
        rules = {
            'humidity_rules': {
                'high_humidity_adjustment': {
                    'condition': 'humidity > 70%',
                    'action': 'increase_pre_mix_time',
                    'adjustment': '+15-25%',
                    'expected_improvement': '20% quality consistency'
                },
                'low_humidity_adjustment': {
                    'condition': 'humidity < 45%',
                    'action': 'decrease_pre_mix_time',
                    'adjustment': '-10-15%',
                    'expected_improvement': '10% cycle time reduction'
                }
            },
            'temperature_rules': {
                'high_temperature_adjustment': {
                    'condition': 'temperature > 85°F',
                    'action': 'reduce_dryer_temp',
                    'adjustment': '-5-10°F',
                    'expected_improvement': '15% energy savings'
                },
                'extreme_temperature_alert': {
                    'condition': 'temperature > 95°F',
                    'action': 'production_hold',
                    'adjustment': 'pause until cooling',
                    'expected_improvement': 'prevent quality issues'
                }
            },
            'pressure_rules': {
                'pressure_drop_adjustment': {
                    'condition': 'pressure decreasing > 0.1 inHg/hour',
                    'action': 'adjust_hold_release',
                    'adjustment': '+5-10 seconds',
                    'expected_improvement': '12% material handling'
                },
                'weather_front_alert': {
                    'condition': 'rapid pressure change',
                    'action': 'quality_monitoring_increase',
                    'adjustment': 'enhanced inspection',
                    'expected_improvement': 'early defect detection'
                }
            }
        }
        
        return rules
        
    def _find_optimal_humidity_range(self, df: pd.DataFrame) -> Dict[str, float]:
        """Find optimal humidity range for production"""
        
        # Group by humidity ranges and find best performance
        humidity_ranges = pd.cut(df['humidity'], bins=10)
        performance = df.groupby(humidity_ranges).agg({
            'efficiency': 'mean',
            'quality_score': 'mean',
            'cycle_time': 'mean'
        })
        
        # Calculate composite score
        performance['composite_score'] = (
            performance['efficiency'] * 0.4 +
            performance['quality_score'] * 0.4 -
            (performance['cycle_time'] / performance['cycle_time'].max()) * 0.2
        )
        
        optimal_range = performance['composite_score'].idxmax()
        
        return {
            'optimal_min': optimal_range.left,
            'optimal_max': optimal_range.right,
            'performance_score': performance.loc[optimal_range, 'composite_score']
        }
        
    def _find_optimal_temperature_range(self, df: pd.DataFrame) -> Dict[str, float]:
        """Find optimal temperature range for production"""
        
        temp_ranges = pd.cut(df['temperature'], bins=10)
        performance = df.groupby(temp_ranges).agg({
            'efficiency': 'mean',
            'energy_usage': 'mean'
        })
        
        # Find temperature range with highest efficiency and lowest energy
        performance['efficiency_energy_score'] = (
            performance['efficiency'] - 
            (performance['energy_usage'] / performance['energy_usage'].max())
        )
        
        optimal_range = performance['efficiency_energy_score'].idxmax()
        
        return {
            'optimal_min': optimal_range.left,
            'optimal_max': optimal_range.right,
            'efficiency_score': performance.loc[optimal_range, 'efficiency_energy_score']
        }
        
    def _find_optimal_pressure_range(self, df: pd.DataFrame) -> Dict[str, float]:
        """Find optimal pressure range for production"""
        
        pressure_ranges = pd.cut(df['pressure'], bins=8)
        performance = df.groupby(pressure_ranges).agg({
            'quality_score': 'mean',
            'cycle_time': 'mean'
        })
        
        optimal_range = performance['quality_score'].idxmax()
        
        return {
            'optimal_min': optimal_range.left,
            'optimal_max': optimal_range.right,
            'quality_score': performance.loc[optimal_range, 'quality_score']
        }
        
    def _calculate_temperature_efficiency_curve(self, df: pd.DataFrame) -> Dict[str, List[float]]:
        """Calculate temperature-efficiency relationship curve"""
        
        temp_bins = pd.cut(df['temperature'], bins=15)
        efficiency_curve = df.groupby(temp_bins)['efficiency'].mean()
        
        return {
            'temperature_points': [interval.mid for interval in efficiency_curve.index],
            'efficiency_points': efficiency_curve.tolist()
        }
        
    def _detect_weather_fronts(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect weather front passages and their impact"""
        
        df_sorted = df.sort_values(['location_id', 'timestamp'])
        df_sorted['pressure_change_rate'] = df_sorted.groupby('location_id')['pressure'].diff() / \
                                           df_sorted.groupby('location_id')['timestamp'].diff().dt.total_seconds() * 3600
        
        # Detect significant pressure changes (>0.1 inHg/hour)
        front_threshold = 0.1
        fronts = df_sorted[abs(df_sorted['pressure_change_rate']) > front_threshold]
        
        return {
            'front_events_detected': len(fronts),
            'average_quality_impact': fronts['quality_score'].mean() - df['quality_score'].mean(),
            'average_cycle_impact': fronts['cycle_time'].mean() - df['cycle_time'].mean()
        }
        
    def _generate_humidity_recommendations(self, df: pd.DataFrame) -> List[str]:
        """Generate humidity-based recommendations"""
        
        return [
            "Install real-time humidity monitoring at all production lines",
            "Implement automated pre_mix_time adjustments based on humidity levels",
            "Set humidity alerts at 70% threshold for curing time adjustments",
            "Consider dehumidification systems for high-humidity periods",
            "Train operators on humidity-based production modifications"
        ]
        
    def _generate_temperature_recommendations(self, df: pd.DataFrame) -> List[str]:
        """Generate temperature-based recommendations"""
        
        return [
            "Implement dynamic cooling system based on outdoor temperature",
            "Set production holds when temperature exceeds 95°F",
            "Adjust dryer temperatures automatically with ambient conditions",
            "Schedule energy-intensive operations during cooler hours",
            "Install temperature gradient monitoring across facility"
        ]
        
    def _generate_pressure_recommendations(self, df: pd.DataFrame) -> List[str]:
        """Generate pressure-based recommendations"""
        
        return [
            "Monitor barometric pressure trends for weather front detection",
            "Adjust material handling timing based on pressure changes",
            "Implement enhanced quality checks during pressure fluctuations",
            "Pre-position materials before predicted weather front arrivals",
            "Document pressure-quality correlations for process improvement"
        ]
        
    def export_correlation_analysis(self, output_path: str = "weather_correlation_analysis.json"):
        """Export comprehensive correlation analysis"""
        
        logger.info("Exporting comprehensive correlation analysis...")
        
        # Create correlation dataset
        df = self.create_correlation_dataset()
        
        if df.empty:
            logger.warning("No data available for correlation analysis")
            return
            
        # Perform all analyses
        correlation_matrix = self.calculate_correlation_matrix(df)
        humidity_analysis = self.analyze_humidity_correlation(df)
        temperature_analysis = self.analyze_temperature_correlation(df)
        pressure_analysis = self.analyze_pressure_correlation(df)
        prediction_models = self.build_prediction_models(df)
        optimization_rules = self.generate_optimization_rules(df)
        
        # Compile results
        analysis_results = {
            'analysis_metadata': {
                'timestamp': datetime.now().isoformat(),
                'records_analyzed': len(df),
                'locations': df['location_id'].unique().tolist(),
                'date_range': {
                    'start': df['timestamp'].min().isoformat(),
                    'end': df['timestamp'].max().isoformat()
                }
            },
            'correlation_matrix': correlation_matrix.to_dict(),
            'detailed_analysis': {
                'humidity': humidity_analysis,
                'temperature': temperature_analysis,
                'pressure': pressure_analysis
            },
            'prediction_models': {
                k: {
                    'performance': v['performance'],
                    'feature_importance': v['feature_importance'],
                    'most_important_feature': v['most_important_feature']
                }
                for k, v in prediction_models.items()
            },
            'optimization_rules': optimization_rules
        }
        
        # Export results
        with open(output_path, 'w') as f:
            json.dump(analysis_results, f, indent=2, default=str)
            
        logger.info(f"Correlation analysis exported to {output_path}")
        
        return analysis_results


def main():
    """Example usage of WeatherCorrelationEngine"""
    
    print("=== Weather Correlation Engine - Demo ===")
    
    # Initialize engine
    engine = WeatherCorrelationEngine()
    
    # Generate sample data for demonstration
    print("Generating sample data for demonstration...")
    
    # Sample weather data
    weather_data = [
        {
            'timestamp': (datetime.now() - timedelta(days=i)).isoformat(),
            'location_id': 'seguin_tx',
            'temperature': 80 + np.random.normal(0, 10),
            'humidity': 60 + np.random.normal(0, 15),
            'pressure': 29.9 + np.random.normal(0, 0.3),
            'wind_speed': 5 + np.random.normal(0, 3),
            'precipitation': max(0, np.random.exponential(0.1))
        }
        for i in range(100)
    ]
    
    # Sample production data
    production_data = [
        {
            'timestamp': (datetime.now() - timedelta(days=i)).isoformat(),
            'location_id': 'seguin_tx',
            'machine_id': f'machine_{i % 10}',
            'cycle_time': 75 + np.random.normal(0, 20),
            'efficiency': min(100, max(0, 85 + np.random.normal(0, 15))),
            'quality_score': min(100, max(0, 90 + np.random.normal(0, 10))),
            'energy_usage': 100 + np.random.normal(0, 25),
            'status': 'Gain' if np.random.random() > 0.2 else 'Loss'
        }
        for i in range(100)
    ]
    
    # Load data
    engine.load_weather_data(weather_data)
    engine.load_production_data(production_data)
    
    # Run analysis
    print("Running correlation analysis...")
    results = engine.export_correlation_analysis()
    
    print("Analysis complete! Results saved to weather_correlation_analysis.json")
    print(f"Analyzed {len(weather_data)} weather records and {len(production_data)} production records")
    

if __name__ == "__main__":
    main()