# MongoDB Schema Analysis - Weather Correlation Ready

## TIMERLOGS (Primary Fact Table)
**Record Counts:**
- apms: 125,566 records (44MB)
- apms-products-inventory: 120,922 records (42MB) 
- apms-today: 11 records (5KB)

**Document Structure:**
```javascript
{
  // Identity & References
  "_id": ObjectId,
  "timerId": ObjectId,           // Timer session reference
  "cycle": Number,               // Production cycle sequence
  "globalCycle": Number,         // Global production counter
  
  // Location & Equipment Context  
  "locationId": ObjectId,        // → Seguin/Conroe/Gunter (Texas locations)
  "factoryId": ObjectId,         // Factory reference
  "machineId": ObjectId,         // → machines collection
  "machineClassId": ObjectId,    // Machine type (Variant/Radial/etc.)
  
  // Production Context
  "partId": ObjectId,            // → parts collection (product being made)
  "jobId": ObjectId,             // → jobs collection (production order)
  "operator": ObjectId,          // Operator user ID
  "operatorName": String,        // Human operator name
  
  // **Weather-Relevant Production Metrics**
  "time": Number,                // Duration in seconds ⚡ KEY FOR WEATHER CORRELATION
  "status": String,              // "Gain"/"Loss"/"Pause"/"New Session" ⚡ WEATHER-SENSITIVE
  "stopReason": Array,           // ["Material Low", "Started", "Unit Created"] ⚡ WEATHER-RELATED STOPS
  
  // Production Parameters (Material-Sensitive)
  "details": {
    "runRate": String,           // Production rate classification
    "tons": Number,              // Material weight ⚡ MOISTURE-SENSITIVE
    "targetRate": Number,        // Target production rate
    "isSplit": Boolean,
    "isMulti": Boolean,
    "isHold": Boolean            // ⚡ WEATHER-TRIGGERED HOLDS
  },
  
  // **Critical Timestamps** ⚡ PRIMARY WEATHER JOIN KEYS
  "createdAt": ISODate,          // Record creation
  "startedAt": ISODate,          // Production start
  "endedAt": ISODate,            // Production end  
  "actualCreatedAt": ISODate,    // Actual start time
  "updatedAt": ISODate           // Last modification
}
```

## PARTS (Product Specifications)
```javascript
{
  "_id": ObjectId,
  "name": String,                // "10X10X2.00 C1577 BOX CULVERT"
  "tons": Number,                // Standard material weight ⚡ MOISTURE BASELINE
  "time": Number,                // Standard production time ⚡ WEATHER PERFORMANCE BASELINE
  "targetRate": Number,          // Target rate ⚡ WEATHER ADJUSTMENT BASELINE
  "finishGoodWeight": Number,    // Quality metric ⚡ MOISTURE IMPACT DETECTION
  "locationId": ObjectId,        // Geographic context
  "machineClassId": ObjectId,    // Equipment type
  "createdAt": ISODate
}
```

## MACHINES (Equipment Information)
```javascript
{
  "_id": ObjectId,
  "name": String,               // Machine name (e.g., "Variant 4000", "50 Ton")
  "description": String,
  "factoryId": ObjectId,
  "machineClassId": ObjectId,
  "locationId": ObjectId,       // ⚡ GEOGRAPHIC WEATHER CORRELATION
  "verified": Boolean,
  "createdAt": Date
}
```

## Geographic Locations (Weather Join Points)
- **Seguin, TX**: Primary production facility - 17hr operation
- **Conroe, TX**: Secondary facility - 12hr operation  
- **Gunter, TX**: Specialized facility - 10hr operation
- **Timezone**: America/Chicago (UTC-6/-5)
- **Industry**: Concrete/Precast manufacturing (weather-sensitive materials)

## Weather Correlation Opportunities

### High Priority Fields:
1. **Timestamps**: `createdAt`, `startedAt`, `endedAt`, `actualCreatedAt`
2. **Production Duration**: `time` field in timerlogs
3. **Location Data**: `locationId` for geographic correlation
4. **Production Status**: `status` and `stopReason` for weather-related interruptions
5. **Material Variables**: `details.tons` for moisture impact analysis