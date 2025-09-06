// mongodb_setup.js - Initialize MongoDB collections and indexes for Weather AI Profile

print("Setting up Weather AI Profile MongoDB collections...");

// Create collections
db.createCollection("weather_production_events");
db.createCollection("production_weather_features"); 
db.createCollection("weather_ai_audit_log");
db.createCollection("parameter_recommendations");
db.createCollection("weather_historical");  // PLACEHOLDER for weather API data

print("Collections created successfully.");

// Create indexes for performance
print("Creating performance indexes...");

// Primary event collection indexes
db.weather_production_events.createIndex({"event_timestamp": 1, "site_location.site_id": 1});
db.weather_production_events.createIndex({"site_location.site_id": 1, "production.machine_id": 1});
db.weather_production_events.createIndex({"event_timestamp": 1});
db.weather_production_events.createIndex({"metrics.production_status": 1, "event_timestamp": -1});

// Features collection indexes  
db.production_weather_features.createIndex({"event_timestamp": 1});
db.production_weather_features.createIndex({"site_location.site_id": 1, "event_timestamp": -1});
db.production_weather_features.createIndex({"actionable_insights.weather_correlation": 1});

// Audit collection indexes
db.weather_ai_audit_log.createIndex({"timestamp": 1});
db.weather_ai_audit_log.createIndex({"timestamp": -1}, {"expireAfterSeconds": 220752000});  // 7 years TTL

// Recommendations collection indexes
db.parameter_recommendations.createIndex({"timestamp": 1, "site_id": 1});
db.parameter_recommendations.createIndex({"alert_level": 1, "timestamp": -1});

// Weather data collection indexes (PLACEHOLDER)
db.weather_historical.createIndex({"location_id": 1, "timestamp": 1});
db.weather_historical.createIndex({"timestamp": -1});

print("Indexes created successfully.");

// Create validation rules
print("Setting up data validation...");

// Validation for weather_production_events
db.runCommand({
  collMod: "weather_production_events",
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["event_timestamp", "site_location", "production", "metrics"],
      properties: {
        event_timestamp: { bsonType: "date" },
        "site_location.site_id": { bsonType: "objectId" },
        "metrics.efficiency_ratio": { bsonType: "number", minimum: 0, maximum: 3 }
      }
    }
  },
  validationAction: "warn"  // Log validation failures but allow inserts
});

print("✅ Weather AI Profile MongoDB setup complete!");
print("Collections created: weather_production_events, production_weather_features, weather_ai_audit_log, parameter_recommendations");
print("Indexes optimized for time-series queries and geographic filtering");
print("Data validation rules active (warning mode)");