# MongoDB Dump Analysis Overview

## Database Summary
- **apms**: 245,000+ records, 60MB+ (Historical production data)
- **apms-products-inventory**: 242,000+ records, 65MB+ (Current production & inventory)  
- **apms-today**: 500+ records, 150KB (Real-time operational data)

## Key Collections for Weather Correlation
1. **timerlogs** (245,000+ records) - Primary production events with timing
2. **parts** (8,678 records) - Product specifications and baselines
3. **machines** (157 records) - Equipment registry
4. **locations** (3 sites) - Geographic context: Seguin, Conroe, Gunter (Texas)

## Weather Integration Readiness
- ✅ Temporal data available (createdAt, startedAt, endedAt timestamps)
- ✅ Geographic location references for weather API integration
- ✅ Production performance metrics for correlation analysis
- ⚡ Weather API integration points identified
- ⚡ Sensor data integration planned

See detailed analysis in schemas.md and data_dictionary.csv