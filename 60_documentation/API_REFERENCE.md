# Weather AI Profile - API Reference

## Table of Contents
1. [Authentication](#authentication)
2. [Weather Data API](#weather-data-api)
3. [Production Events API](#production-events-api)
4. [Optimization API](#optimization-api)
5. [Alerts API](#alerts-api)
6. [Analytics API](#analytics-api)
7. [Configuration API](#configuration-api)
8. [WebSocket Endpoints](#websocket-endpoints)
9. [Error Codes](#error-codes)
10. [Rate Limiting](#rate-limiting)

---

## Base URL
```
Production: https://weather-ai.yourcompany.com/api/v1
Development: http://localhost:8080/api/v1
```

## Authentication

All API endpoints require authentication using JWT tokens.

### Login
```http
POST /auth/login
Content-Type: application/json

{
  "username": "operator@company.com",
  "password": "your_password",
  "location_id": "seguin_tx"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "user123",
    "username": "operator@company.com",
    "role": "operator",
    "location_id": "seguin_tx",
    "permissions": ["read:weather", "read:production", "write:parameters"]
  }
}
```

### Refresh Token
```http
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### Authentication Header
Include the JWT token in all requests:
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## Weather Data API

### Get Current Weather
```http
GET /weather/current?location_id=seguin_tx
```

**Response:**
```json
{
  "timestamp": "2025-09-08T15:30:00Z",
  "location_id": "seguin_tx",
  "location_name": "Seguin, TX",
  "temperature": 87.2,
  "humidity": 68.5,
  "pressure": 29.92,
  "wind_speed": 12.3,
  "wind_direction": 180,
  "precipitation": 0.0,
  "weather_condition": "Partly Cloudy",
  "weather_code": 802,
  "data_source": "openweathermap",
  "quality_score": 0.95
}
```

### Get Weather History
```http
GET /weather/history?location_id=seguin_tx&start_date=2025-09-01&end_date=2025-09-08&interval=hourly
```

**Query Parameters:**
- `location_id`: Required. Location identifier
- `start_date`: Required. ISO date format (YYYY-MM-DD)
- `end_date`: Required. ISO date format (YYYY-MM-DD)
- `interval`: Optional. Values: `hourly`, `daily` (default: `hourly`)
- `limit`: Optional. Max records to return (default: 1000, max: 10000)

### Get Weather Forecast
```http
GET /weather/forecast?location_id=seguin_tx&hours=48
```

**Response:**
```json
{
  "location_id": "seguin_tx",
  "forecast_generated": "2025-09-08T15:30:00Z",
  "forecast": [
    {
      "timestamp": "2025-09-08T16:00:00Z",
      "temperature": 88.1,
      "humidity": 65.2,
      "pressure": 29.89,
      "precipitation_probability": 15,
      "weather_condition": "Sunny"
    }
  ]
}
```

### Get All Locations
```http
GET /weather/locations
```

**Response:**
```json
{
  "locations": [
    {
      "location_id": "seguin_tx",
      "name": "Seguin, TX",
      "latitude": 29.5688,
      "longitude": -97.9647,
      "timezone": "America/Chicago",
      "priority": "HIGH"
    },
    {
      "location_id": "conroe_tx",
      "name": "Conroe, TX", 
      "latitude": 30.3118,
      "longitude": -95.4560,
      "timezone": "America/Chicago",
      "priority": "MEDIUM"
    }
  ]
}
```

---

## Production Events API

### Get Production Events
```http
GET /production/events?location_id=seguin_tx&start_date=2025-09-08&limit=100
```

**Query Parameters:**
- `location_id`: Optional. Filter by location
- `machine_id`: Optional. Filter by machine
- `status`: Optional. Filter by status (`Gain`, `Loss`, `New Session`)
- `start_date`: Optional. ISO date format
- `end_date`: Optional. ISO date format
- `limit`: Optional. Max records (default: 100, max: 1000)
- `offset`: Optional. Pagination offset (default: 0)

**Response:**
```json
{
  "total": 1523,
  "limit": 100,
  "offset": 0,
  "events": [
    {
      "event_id": "evt_12345",
      "timestamp": "2025-09-08T15:25:30Z",
      "location_id": "seguin_tx",
      "machine_id": "RP-001",
      "cycle": 156,
      "global_cycle": 245623,
      "part_id": "part_abc123",
      "status": "Gain",
      "cycle_time": 78.5,
      "details": {
        "runRate": "standalone",
        "tons": 2.45,
        "targetRate": 60,
        "efficiency": 0.87
      },
      "weather_context": {
        "temperature": 87.2,
        "humidity": 68.5,
        "pressure": 29.92
      }
    }
  ]
}
```

### Create Production Event
```http
POST /production/events
Content-Type: application/json

{
  "location_id": "seguin_tx",
  "machine_id": "RP-001",
  "part_id": "part_abc123",
  "job_id": "job_456",
  "status": "Gain",
  "cycle_time": 78.5,
  "details": {
    "runRate": "standalone",
    "tons": 2.45,
    "targetRate": 60
  },
  "operator_id": "operator_789"
}
```

### Get Machine Status
```http
GET /production/machines?location_id=seguin_tx
```

**Response:**
```json
{
  "machines": [
    {
      "machine_id": "RP-001",
      "machine_class": "RP_Series",
      "location_id": "seguin_tx",
      "status": "Running",
      "current_part": "part_abc123",
      "current_cycle": 156,
      "efficiency": 0.87,
      "last_update": "2025-09-08T15:25:30Z",
      "weather_sensitivity": "HIGH"
    }
  ]
}
```

### Get Production Statistics
```http
GET /production/stats?location_id=seguin_tx&period=24h
```

**Query Parameters:**
- `location_id`: Optional. Filter by location
- `machine_id`: Optional. Filter by machine
- `period`: Optional. Time period (`1h`, `24h`, `7d`, `30d`)

**Response:**
```json
{
  "period": "24h",
  "location_id": "seguin_tx",
  "total_cycles": 1247,
  "gain_cycles": 1089,
  "loss_cycles": 158,
  "efficiency": 0.873,
  "average_cycle_time": 76.3,
  "weather_correlation": {
    "primary_factor": "humidity",
    "correlation_strength": 0.73,
    "impact_assessment": "HIGH"
  }
}
```

---

## Optimization API

### Get Current Optimizations
```http
GET /optimization/recommendations?location_id=seguin_tx&active_only=true
```

**Response:**
```json
{
  "recommendations": [
    {
      "optimization_id": "opt_789",
      "location_id": "seguin_tx",
      "machine_id": "RP-001",
      "timestamp": "2025-09-08T15:30:00Z",
      "weather_trigger": "T:87.2°F H:68.5% P:29.92inHg",
      "current_parameters": {
        "pre_mix_time": 60,
        "dryer_temp": 300,
        "hold_time": 5
      },
      "optimized_parameters": {
        "pre_mix_time": 72,
        "dryer_temp": 295,
        "hold_time": 6
      },
      "expected_improvement": {
        "quality_consistency": 0.20,
        "energy_savings": 0.08,
        "cycle_time_reduction": 0.05
      },
      "confidence_score": 0.85,
      "implementation_priority": "HIGH",
      "valid_until": "2025-09-08T17:30:00Z"
    }
  ]
}
```

### Apply Optimization
```http
POST /optimization/apply
Content-Type: application/json

{
  "optimization_id": "opt_789",
  "machine_id": "RP-001",
  "parameters": {
    "pre_mix_time": 72,
    "dryer_temp": 295
  },
  "operator_id": "operator_789",
  "notes": "Applied due to high humidity conditions"
}
```

**Response:**
```json
{
  "success": true,
  "applied_at": "2025-09-08T15:35:00Z",
  "optimization_id": "opt_789",
  "parameters_applied": {
    "pre_mix_time": 72,
    "dryer_temp": 295
  },
  "tracking_id": "track_456"
}
```

### Manual Override
```http
POST /optimization/override
Content-Type: application/json

{
  "machine_id": "RP-001",
  "parameters": {
    "pre_mix_time": 65
  },
  "reason": "Operator experience suggests different approach",
  "operator_id": "operator_789",
  "confidence": 0.9
}
```

### Get Optimization History
```http
GET /optimization/history?machine_id=RP-001&days=7
```

---

## Alerts API

### Get Active Alerts
```http
GET /alerts/active?location_id=seguin_tx
```

**Response:**
```json
{
  "alerts": [
    {
      "alert_id": "alert_123",
      "location_id": "seguin_tx",
      "alert_type": "HUMIDITY",
      "severity": "HIGH",
      "message": "High humidity 72.5% at Seguin location",
      "recommended_actions": [
        "Increase pre-mix time by 20%",
        "Activate dehumidification systems",
        "Monitor curing quality closely"
      ],
      "production_impact": "HIGH - Curing time increase expected",
      "created_at": "2025-09-08T15:20:00Z",
      "valid_until": "2025-09-08T17:20:00Z",
      "acknowledged": false
    }
  ]
}
```

### Acknowledge Alert
```http
POST /alerts/{alert_id}/acknowledge
Content-Type: application/json

{
  "operator_id": "operator_789",
  "notes": "Actions implemented, monitoring closely"
}
```

### Get Alert History
```http
GET /alerts/history?location_id=seguin_tx&days=30
```

### Create Custom Alert
```http
POST /alerts/custom
Content-Type: application/json

{
  "location_id": "seguin_tx",
  "alert_type": "MAINTENANCE",
  "severity": "MEDIUM",
  "message": "Scheduled maintenance window approaching",
  "valid_until": "2025-09-09T08:00:00Z"
}
```

---

## Analytics API

### Get Weather Correlation Analysis
```http
GET /analytics/correlation?location_id=seguin_tx&factor=humidity&days=30
```

**Response:**
```json
{
  "location_id": "seguin_tx",
  "weather_factor": "humidity",
  "analysis_period": "30 days",
  "correlation_coefficient": 0.73,
  "significance_level": "HIGH",
  "p_value": 0.001,
  "sample_size": 2845,
  "impact_metrics": {
    "cycle_time_variance": 0.25,
    "quality_correlation": 0.68,
    "efficiency_impact": 0.15
  }
}
```

### Get Performance Trends
```http
GET /analytics/trends?metric=efficiency&period=7d&location_id=seguin_tx
```

**Response:**
```json
{
  "metric": "efficiency",
  "period": "7d",
  "location_id": "seguin_tx",
  "data_points": [
    {
      "date": "2025-09-02",
      "value": 0.85,
      "weather_conditions": {
        "avg_temperature": 82.1,
        "avg_humidity": 65.2
      }
    }
  ],
  "trend_analysis": {
    "direction": "improving",
    "rate_of_change": 0.02,
    "weather_correlation": 0.78
  }
}
```

### Get ROI Analysis
```http
GET /analytics/roi?location_id=seguin_tx&start_date=2025-08-01&end_date=2025-09-01
```

### Export Analytics Data
```http
GET /analytics/export?format=csv&location_id=seguin_tx&start_date=2025-09-01&end_date=2025-09-08
```

**Query Parameters:**
- `format`: `csv`, `json`, `xlsx`
- `location_id`: Optional filter
- `include_weather`: Optional boolean (default: true)
- `include_production`: Optional boolean (default: true)

---

## Configuration API

### Get System Configuration
```http
GET /config/system
```

**Response:**
```json
{
  "weather_polling_interval": 900,
  "correlation_window_minutes": 60,
  "min_confidence_threshold": 0.7,
  "safety_overrides": {
    "max_temperature": 95,
    "max_humidity": 85,
    "min_quality_threshold": 80
  }
}
```

### Update Configuration
```http
PUT /config/system
Content-Type: application/json
Authorization: Bearer [admin_token]

{
  "min_confidence_threshold": 0.75,
  "safety_overrides": {
    "max_temperature": 98
  }
}
```

### Get Machine Configuration
```http
GET /config/machines/{machine_id}
```

### Update Machine Configuration
```http
PUT /config/machines/{machine_id}
Content-Type: application/json

{
  "weather_sensitivity": "HIGH",
  "baseline_parameters": {
    "pre_mix_time": 60,
    "dryer_temp": 300
  },
  "safety_limits": {
    "max_pre_mix_time": 120,
    "min_dryer_temp": 250
  }
}
```

---

## WebSocket Endpoints

### Real-time Weather Updates
```javascript
const ws = new WebSocket('ws://localhost:8080/ws/weather');

ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  console.log('Weather update:', data);
};

// Subscribe to specific location
ws.send(JSON.stringify({
  action: 'subscribe',
  location_id: 'seguin_tx'
}));
```

### Real-time Production Events
```javascript
const ws = new WebSocket('ws://localhost:8080/ws/production');

// Message format:
{
  "type": "production_event",
  "data": {
    "event_id": "evt_123",
    "machine_id": "RP-001",
    "status": "Gain",
    "timestamp": "2025-09-08T15:30:00Z"
  }
}
```

### Real-time Alerts
```javascript
const ws = new WebSocket('ws://localhost:8080/ws/alerts');

// Message format:
{
  "type": "alert",
  "data": {
    "alert_id": "alert_456",
    "severity": "HIGH",
    "location_id": "seguin_tx",
    "message": "High humidity detected"
  }
}
```

### Real-time Optimizations
```javascript
const ws = new WebSocket('ws://localhost:8080/ws/optimizations');

// Message format:
{
  "type": "optimization",
  "data": {
    "optimization_id": "opt_789",
    "machine_id": "RP-001",
    "confidence_score": 0.85,
    "parameters": {
      "pre_mix_time": 72
    }
  }
}
```

---

## Error Codes

### HTTP Status Codes
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `429` - Too Many Requests
- `500` - Internal Server Error
- `503` - Service Unavailable

### Custom Error Codes
```json
{
  "error": {
    "code": "WEATHER_DATA_UNAVAILABLE",
    "message": "Weather data is temporarily unavailable for the requested location",
    "details": {
      "location_id": "seguin_tx",
      "retry_after": 300
    }
  }
}
```

**Common Error Codes:**
- `INVALID_LOCATION_ID` - Location not found or invalid
- `INSUFFICIENT_PERMISSIONS` - User lacks required permissions
- `WEATHER_DATA_UNAVAILABLE` - Weather service unavailable
- `MACHINE_NOT_FOUND` - Machine ID not found
- `PARAMETER_OUT_OF_BOUNDS` - Parameter value exceeds safety limits
- `OPTIMIZATION_EXPIRED` - Optimization recommendation expired
- `CORRELATION_ENGINE_ERROR` - Error in correlation processing
- `RATE_LIMIT_EXCEEDED` - API rate limit exceeded

---

## Rate Limiting

### Rate Limits by Endpoint Category

**Authentication:** 10 requests per minute per IP
**Weather Data:** 100 requests per minute per user
**Production Events:** 1000 requests per minute per user
**Optimizations:** 50 requests per minute per user
**Analytics:** 20 requests per minute per user
**Configuration:** 10 requests per minute per user (admin only)

### Rate Limit Headers
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1694180400
X-RateLimit-Window: 60
```

### Rate Limit Exceeded Response
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "API rate limit exceeded",
    "retry_after": 45
  }
}
```

---

## SDK Examples

### Python SDK
```python
from weather_ai_client import WeatherAIClient

client = WeatherAIClient(
    base_url="https://weather-ai.yourcompany.com/api/v1",
    username="operator@company.com",
    password="your_password"
)

# Get current weather
weather = client.weather.get_current("seguin_tx")
print(f"Temperature: {weather.temperature}°F")

# Get active alerts
alerts = client.alerts.get_active("seguin_tx")
for alert in alerts:
    print(f"{alert.severity}: {alert.message}")

# Apply optimization
optimization = client.optimization.get_recommendations("seguin_tx")[0]
result = client.optimization.apply(optimization.optimization_id)
```

### JavaScript SDK
```javascript
import { WeatherAIClient } from '@yourcompany/weather-ai-client';

const client = new WeatherAIClient({
  baseURL: 'https://weather-ai.yourcompany.com/api/v1',
  username: 'operator@company.com',
  password: 'your_password'
});

// Get current weather
const weather = await client.weather.getCurrent('seguin_tx');
console.log(`Temperature: ${weather.temperature}°F`);

// Subscribe to real-time updates
client.weather.subscribe('seguin_tx', (update) => {
  console.log('Weather update:', update);
});
```

### cURL Examples
```bash
# Get current weather
curl -H "Authorization: Bearer $TOKEN" \
     "https://weather-ai.yourcompany.com/api/v1/weather/current?location_id=seguin_tx"

# Create production event
curl -X POST \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"location_id":"seguin_tx","machine_id":"RP-001","status":"Gain","cycle_time":78.5}' \
     "https://weather-ai.yourcompany.com/api/v1/production/events"

# Get optimization recommendations
curl -H "Authorization: Bearer $TOKEN" \
     "https://weather-ai.yourcompany.com/api/v1/optimization/recommendations?location_id=seguin_tx"
```

---

## API Versioning

The Weather AI Profile API uses semantic versioning. The current version is `v1`.

**Breaking Changes:** Will increment the major version (e.g., v1 → v2)
**New Features:** Will increment the minor version (maintained within v1)
**Bug Fixes:** Will increment the patch version (maintained within v1)

**Version Support Policy:**
- Current version (v1): Full support
- Previous version (v0): Security updates only for 6 months
- Legacy versions: No support

**Version Specification:**
- URL Path: `/api/v1/...` (recommended)
- Header: `API-Version: v1`
- Query Parameter: `?version=v1`

---

*This API reference is automatically updated with each release. For the most current version, see the interactive API documentation at `/docs` on your deployed instance.*