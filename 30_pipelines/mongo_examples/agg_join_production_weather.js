// agg_join_production_weather.js
// Purpose: Join production events with weather data by timestamp and location

db.timerlogs.aggregate([
  // **Stage 1: Filter recent production events**
  {
    $match: {
      "createdAt": {
        $gte: ISODate("2023-09-01T00:00:00Z"),
        $lte: ISODate("2023-09-30T23:59:59Z")
      },
      "deletedAt": { $exists: false },
      "status": { $in: ["Gain", "Loss"] }  // Filter to actual production events
    }
  },
  
  // **Stage 2: Add computed time windows for weather correlation**
  {
    $addFields: {
      "weather_timestamp_6h_ago": { 
        $dateSubtract: { 
          startDate: "$createdAt", 
          unit: "hour", 
          amount: 6 
        }
      },
      "weather_timestamp_24h_ago": { 
        $dateSubtract: { 
          startDate: "$createdAt", 
          unit: "hour", 
          amount: 24 
        }
      },
      "production_duration_hours": { 
        $divide: ["$time", 3600] 
      }
    }
  },
  
  // **Stage 3: Join with parts collection for baseline performance**
  {
    $lookup: {
      from: "parts",
      localField: "partId", 
      foreignField: "_id",
      as: "part_specs"
    }
  },
  
  // **Stage 4: Join with machines collection for equipment context**
  {
    $lookup: {
      from: "machines",
      localField: "machineId",
      foreignField: "_id", 
      as: "machine_info"
    }
  },
  
  // **Stage 5: Join with locations for geographic context**
  {
    $lookup: {
      from: "locations",
      localField: "locationId",
      foreignField: "_id",
      as: "location_info"
    }
  },
  
  // **Stage 6: Join with weather data (PLACEHOLDER - External collection)**
  {
    $lookup: {
      from: "weather_historical",  // PLACEHOLDER COLLECTION
      let: { 
        loc_id: "$locationId", 
        prod_time: "$createdAt",
        time_6h_ago: "$weather_timestamp_6h_ago",
        time_24h_ago: "$weather_timestamp_24h_ago"
      },
      pipeline: [
        {
          $match: {
            $expr: {
              $and: [
                { $eq: ["$location_id", "$$loc_id"] },
                { $gte: ["$timestamp", "$$time_24h_ago"] },
                { $lte: ["$timestamp", "$$prod_time"] }
              ]
            }
          }
        },
        {
          $sort: { "timestamp": -1 }
        },
        {
          $limit: 48  // 24 hours of hourly weather data
        }
      ],
      as: "weather_data"
    }
  },
  
  // **Stage 7: Calculate production performance metrics**
  {
    $addFields: {
      "efficiency_ratio": {
        $cond: {
          if: { $gt: [{ $arrayElemAt: ["$part_specs.time", 0] }, 0] },
          then: { 
            $divide: [
              { $arrayElemAt: ["$part_specs.time", 0] },
              "$time"
            ]
          },
          else: 1.0
        }
      },
      "material_variance_pct": {
        $cond: {
          if: { $gt: [{ $arrayElemAt: ["$part_specs.tons", 0] }, 0] },
          then: {
            $multiply: [
              {
                $divide: [
                  { 
                    $subtract: [
                      "$details.tons", 
                      { $arrayElemAt: ["$part_specs.tons", 0] }
                    ]
                  },
                  { $arrayElemAt: ["$part_specs.tons", 0] }
                ]
              },
              100
            ]
          },
          else: 0
        }
      }
    }
  },
  
  // **Stage 8: Aggregate weather conditions for analysis periods**
  {
    $addFields: {
      "weather_summary": {
        "rainfall_24h_total": {
          $sum: {
            $map: {
              input: "$weather_data",
              as: "weather_point",
              in: "$$weather_point.precipitation_inches"
            }
          }
        },
        "temperature_24h_avg": {
          $avg: {
            $map: {
              input: "$weather_data", 
              as: "weather_point",
              in: "$$weather_point.temperature_f"
            }
          }
        },
        "humidity_24h_avg": {
          $avg: {
            $map: {
              input: "$weather_data",
              as: "weather_point", 
              in: "$$weather_point.humidity_percent"
            }
          }
        },
        "rainfall_6h_total": {
          $sum: {
            $map: {
              input: {
                $filter: {
                  input: "$weather_data",
                  as: "weather_point",
                  cond: { 
                    $gte: ["$$weather_point.timestamp", "$weather_timestamp_6h_ago"]
                  }
                }
              },
              as: "recent_weather",
              in: "$$recent_weather.precipitation_inches"
            }
          }
        }
      }
    }
  },
  
  // **Stage 9: Project final canonical structure**
  {
    $project: {
      "_id": 1,
      "event_timestamp": "$createdAt", 
      "site_location": {
        "site_id": "$locationId",
        "site_name": { $arrayElemAt: ["$location_info.name", 0] },
        "coordinates": { $arrayElemAt: ["$location_info.coordinates", 0] }  // PLACEHOLDER
      },
      "production": {
        "session_id": "$timerId",
        "cycle_number": "$cycle",
        "global_cycle": "$globalCycle", 
        "machine_id": "$machineId",
        "machine_class": { $arrayElemAt: ["$machine_info.name", 0] },
        "operator_id": "$operator",
        "job_id": "$jobId",
        "part_id": "$partId"
      },
      "metrics": {
        "duration_actual_sec": "$time",
        "duration_standard_sec": { $arrayElemAt: ["$part_specs.time", 0] },
        "efficiency_ratio": "$efficiency_ratio",
        "material_weight_actual": "$details.tons",
        "material_weight_standard": { $arrayElemAt: ["$part_specs.tons", 0] },
        "material_variance_pct": "$material_variance_pct",
        "production_status": "$status",
        "stop_reasons": "$stopReason"
      },
      "weather": {
        "conditions_24h": {
          "rainfall_total_in": "$weather_summary.rainfall_24h_total",
          "temperature_avg_f": "$weather_summary.temperature_24h_avg",
          "humidity_avg_pct": "$weather_summary.humidity_24h_avg"
        },
        "conditions_6h": {
          "rainfall_total_in": "$weather_summary.rainfall_6h_total"
        }
      },
      "created_at": new Date()
    }
  },
  
  // **Stage 10: Output to canonical collection**
  {
    $merge: {
      into: "weather_production_events",
      whenMatched: "replace",
      whenNotMatched: "insert"
    }
  }
]);