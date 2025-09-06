# Weather Monitoring AI Profile for APMS Factory Analytics

## Overview
This project implements a weather monitoring AI profile that analyzes weather signals and cross-correlates them with factory operations to optimize production parameters.

## Quick Start
1. Review MongoDB dump analysis: `00_dump-scan/`
2. Understand system architecture: `10_architecture/`
3. Examine logic and rules: `20_logic/`
4. Deploy pipelines: `30_pipelines/`
5. Follow SOP: `40_sop/SOP_weather_profile.md`

## Implementation Status
- [x] MongoDB dump analysis complete
- [x] Canonical data model designed  
- [x] Heuristic rules defined
- [x] MongoDB pipelines created
- [x] SOP documented
- [ ] **Weather API integration** (PLACEHOLDER)
- [ ] **Sensor data integration** (PLACEHOLDER)
- [ ] Production deployment

## Placeholders
- Weather API integration points marked with ⚡
- Sensor data marked as `{moisture_level}`, `{rainfall_data}`, etc.
- Frontend integration points marked as PLACEHOLDER

## Directory Structure
```
research/weather-ai-profile/
├── 00_dump-scan/          # MongoDB analysis results
├── 10_architecture/       # System design and data models  
├── 20_logic/              # Heuristic rules and algorithms
├── 30_pipelines/          # MongoDB aggregation pipelines
├── 40_sop/                # Standard operating procedures
├── 50_implementation/     # Source code and deployment files
├── 60_documentation/      # Additional documentation
└── scripts/               # Setup and maintenance scripts
```

## Quick Setup
```bash
cd research/weather-ai-profile
./scripts/setup_environment.sh
./scripts/health_check.sh
```

## Key Files
- `40_sop/SOP_weather_profile.md` - Complete implementation guide
- `30_pipelines/mongo_examples/` - MongoDB aggregation pipelines  
- `50_implementation/source/weather_production_recommender.py` - Main algorithm
- `scripts/setup_environment.sh` - Environment setup script