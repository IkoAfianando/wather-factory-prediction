# Weather-Based Production Heuristic Rules

## Rule Priority Matrix
1. **SAFETY_RULES** (Priority 1) - Immediate halt conditions
2. **QUALITY_RULES** (Priority 2) - Product quality maintenance
3. **EFFICIENCY_RULES** (Priority 3) - Performance optimization  
4. **COST_RULES** (Priority 4) - Cost minimization

## Primary Rules

### Rule 1: Excess Moisture Compensation
**Trigger**: Material moisture >3% above baseline
**Actions**: Increase dryer temp (+5-25°F), extend mixing time (+30-90s)
**Alert Level**: MEDIUM to HIGH

### Rule 2: Active Precipitation Response  
**Trigger**: Rainfall >1.5" in 24h
**Actions**: Production HOLD, HIGH alert
**Safety Priority**: Override all other rules

### Rule 3: Predictive Precipitation Management
**Trigger**: Rain probability >70% next 6h
**Actions**: Accelerate production, reduce mixing time (-120s)
**Alert Level**: MEDIUM

### Rule 4: Hot Weather Compensation
**Trigger**: Temperature >85°F
**Actions**: Reduce dryer temp (-0.8°F per degree), extend mixing (+90s)
**Material Impact**: Prevent concrete overheating

### Rule 5: Cold Weather Compensation  
**Trigger**: Temperature <60°F
**Actions**: Increase dryer temp (+1.2°F per degree)
**Quality Impact**: Ensure proper curing conditions

### Rule 6: Efficiency Recovery
**Trigger**: Performance <85% of baseline with weather correlation
**Actions**: Aggressive parameter adjustment, +15°F dryer, +180s mixing
**Alert Level**: HIGH

### Rule 7: Safety Override (Highest Priority)
**Triggers**: Temperature <32°F OR >105°F, Combined safety score <0.3
**Actions**: Immediate production HOLD, CRITICAL alert
**Override**: All other rules suspended

## Fallback Behavior
- API failures: Use cached weather data (max 2h old)  
- Sensor failures: Revert to weather API + historical baselines ⚡
- Rule conflicts: Apply highest priority rule only
- Invalid recommendations: Default to standard operating parameters

## Algorithm Inputs
```python
inputs = {
    'rainfall_last_24h': float,           # inches
    'rain_probability_next_6h': float,    # percentage 0-100
    'moisture_level': float,              # percentage 0-100 ⚡ PLACEHOLDER
    'temperature_ambient': float,         # fahrenheit ⚡ PLACEHOLDER
    'humidity_relative': float,           # percentage 0-100 ⚡ PLACEHOLDER
    'line_speed': float,                  # units/hour current rate
    'product_type': str,                  # concrete part classification
    'machine_class': str,                 # equipment type
    'current_efficiency': float,          # current vs baseline ratio
    'material_moisture_content': float    # percentage 0-100 ⚡ PLACEHOLDER
}
```

## Algorithm Outputs
```python
recommendations = {
    'recommended_dryer_temp': float,      # fahrenheit
    'pre_mix_time_delta': int,           # seconds adjustment
    'hold_release_flag': str,            # "HOLD", "RELEASE", "CONTINUE"
    'alert_level': str,                  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    'confidence_score': float,           # 0.0 - 1.0
    'rationale': str                     # human-readable explanation
}
```

See pseudocode.md for complete algorithm implementation.