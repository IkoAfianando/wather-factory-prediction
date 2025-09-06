// rolling_weather_windows.js  
// Purpose: Calculate rolling averages and trends for weather impact analysis

db.weather_production_events.aggregate([
  // **Stage 1: Sort by location and timestamp**
  {
    $sort: {
      "site_location.site_id": 1,
      "event_timestamp": 1
    }
  },
  
  // **Stage 2: Calculate rolling windows using $setWindowFields**
  {
    $setWindowFields: {
      partitionBy: "$site_location.site_id",
      sortBy: { "event_timestamp": 1 },
      output: {
        // **6-hour rolling averages**
        "efficiency_6h_avg": {
          $avg: "$metrics.efficiency_ratio",
          window: {
            range: [-6, 0],
            unit: "hour"
          }
        },
        "rainfall_6h_rolling": {
          $sum: "$weather.conditions_6h.rainfall_total_in", 
          window: {
            range: [-6, 0],
            unit: "hour"
          }
        },
        
        // **24-hour rolling averages**
        "efficiency_24h_avg": {
          $avg: "$metrics.efficiency_ratio",
          window: {
            range: [-24, 0], 
            unit: "hour"
          }
        },
        "temperature_24h_trend": {
          $avg: "$weather.conditions_24h.temperature_avg_f",
          window: {
            range: [-24, 0],
            unit: "hour"
          }
        },
        "humidity_24h_trend": {
          $avg: "$weather.conditions_24h.humidity_avg_pct",
          window: {
            range: [-24, 0],
            unit: "hour" 
          }
        },
        
        // **7-day baseline comparison**
        "efficiency_7d_baseline": {
          $avg: "$metrics.efficiency_ratio",
          window: {
            range: [-168, -24],  // 7 days ago to 1 day ago
            unit: "hour"
          }
        },
        
        // **Production count in window**
        "production_events_6h": {
          $count: {},
          window: {
            range: [-6, 0],
            unit: "hour"
          }
        }
      }
    }
  },
  
  // **Stage 3: Calculate weather impact indicators**
  {
    $addFields: {
      "indicators": {
        "efficiency_degradation_6h": {
          $cond: {
            if: { $gt: ["$efficiency_7d_baseline", 0] },
            then: {
              $divide: [
                { $subtract: ["$efficiency_7d_baseline", "$efficiency_6h_avg"] },
                "$efficiency_7d_baseline"
              ]
            },
            else: 0
          }
        },
        "weather_severity_score": {
          $add: [
            { $multiply: [{ $min: ["$rainfall_6h_rolling", 2.0] }, 0.4] },  // Rainfall impact (max 0.8)
            { 
              $multiply: [
                { 
                  $max: [
                    { $subtract: [90, "$humidity_24h_trend"] },  // High humidity penalty
                    { $subtract: ["$humidity_24h_trend", 30] }   // Low humidity penalty
                  ]
                }, 
                0.01
              ]
            }  // Humidity impact
          ]
        },
        "production_anomaly_flag": {
          $cond: {
            if: { 
              $and: [
                { $lt: ["$efficiency_6h_avg", 0.85] },  // Below 85% efficiency
                { $gt: ["$rainfall_6h_rolling", 0.5] }  // With significant rainfall
              ]
            },
            then: true,
            else: false
          }
        }
      }
    }
  },
  
  // **Stage 4: Filter to actionable insights**  
  {
    $match: {
      $or: [
        { "indicators.efficiency_degradation_6h": { $gt: 0.1 } },    // >10% efficiency loss
        { "indicators.weather_severity_score": { $gt: 0.6 } },      // High weather severity
        { "indicators.production_anomaly_flag": true }              // Anomaly detected
      ]
    }
  },
  
  // **Stage 5: Project analysis-ready features**
  {
    $project: {
      "event_timestamp": 1,
      "site_location": 1,
      "production.machine_class": 1,
      "current_metrics": {
        "efficiency_current": "$metrics.efficiency_ratio", 
        "efficiency_6h_avg": "$efficiency_6h_avg",
        "efficiency_baseline": "$efficiency_7d_baseline",
        "material_variance": "$metrics.material_variance_pct"
      },
      "weather_context": {
        "rainfall_6h": "$rainfall_6h_rolling",
        "temperature_trend": "$temperature_24h_trend", 
        "humidity_trend": "$humidity_24h_trend",
        "severity_score": "$indicators.weather_severity_score"
      },
      "actionable_insights": {
        "efficiency_degradation_pct": { 
          $multiply: ["$indicators.efficiency_degradation_6h", 100] 
        },
        "weather_correlation": {
          $cond: {
            if: { 
              $and: [
                { $gt: ["$indicators.efficiency_degradation_6h", 0.05] },
                { $gt: ["$indicators.weather_severity_score", 0.3] }
              ]
            },
            then: "LIKELY_WEATHER_RELATED",
            else: "INVESTIGATE_OTHER_CAUSES"
          }
        },
        "recommended_action": {
          $switch: {
            branches: [
              { 
                case: { $eq: ["$indicators.production_anomaly_flag", true] },
                then: "IMMEDIATE_PARAMETER_ADJUSTMENT"
              },
              {
                case: { $gt: ["$indicators.efficiency_degradation_6h", 0.15] },
                then: "SCHEDULE_MAINTENANCE_CHECK"
              },
              {
                case: { $gt: ["$indicators.weather_severity_score", 0.7] },
                then: "CONSIDER_PRODUCTION_HOLD"
              }
            ],
            default: "CONTINUE_MONITORING"
          }
        }
      },
      "analysis_timestamp": new Date()
    }
  },
  
  // **Stage 6: Output to features collection**
  {
    $merge: {
      into: "production_weather_features",
      whenMatched: "replace",
      whenNotMatched: "insert"
    }
  }
]);