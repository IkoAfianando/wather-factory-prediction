#!/bin/bash
# health_check.sh - Validate Weather AI Profile system health

set -e

echo "=== Weather AI Profile Health Check ==="

# Load environment
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# MongoDB connectivity
echo "Checking MongoDB connectivity..."
mongo --host ${APMS_MONGODB_HOST:-localhost:27017} --eval "db.runCommand('ping')" --quiet
if [ $? -eq 0 ]; then
    echo "✅ MongoDB: Connected"
else
    echo "❌ MongoDB: Connection failed"
    exit 1
fi

# Check collection counts
echo "Checking data collections..."
EVENTS_COUNT=$(mongo --host ${APMS_MONGODB_HOST:-localhost:27017} ${APMS_DB_WEATHER_AI:-apms_weather_ai} --eval "db.weather_production_events.count()" --quiet 2>/dev/null || echo "0")
FEATURES_COUNT=$(mongo --host ${APMS_MONGODB_HOST:-localhost:27017} ${APMS_DB_WEATHER_AI:-apms_weather_ai} --eval "db.production_weather_features.count()" --quiet 2>/dev/null || echo "0")

echo "  Weather-Production Events: $EVENTS_COUNT"
echo "  Feature Records: $FEATURES_COUNT"

if [ "$EVENTS_COUNT" -gt 1000 ]; then
    echo "✅ Data: Sufficient event data available"
else
    echo "⚠️ Data: Low event count - may need backfill"
fi

# Weather API health (placeholder)
echo "Checking weather API..."
if [ -n "${WEATHER_API_KEY}" ] && [ "${WEATHER_API_KEY}" != "your_openweather_api_key_here" ]; then
    echo "⚡ Weather API: PLACEHOLDER - Add actual connectivity test"
    echo "✅ Weather API: Configuration present"
else
    echo "⚠️ Weather API: Not configured (PLACEHOLDER)"
fi

# Sensor connectivity (placeholder)
echo "Checking sensor connectivity..."
echo "⚡ Sensors: PLACEHOLDER - Add sensor connectivity tests"

# System performance
echo "Checking system performance..."
DISK_USAGE=$(df -h . | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -lt 80 ]; then
    echo "✅ Disk Space: ${DISK_USAGE}% used (healthy)"
else
    echo "⚠️ Disk Space: ${DISK_USAGE}% used (monitor closely)"
fi

# Recent audit logs
echo "Checking recent activity..."
RECENT_LOGS=$(mongo --host ${APMS_MONGODB_HOST:-localhost:27017} ${APMS_DB_WEATHER_AI:-apms_weather_ai} --eval "db.weather_ai_audit_log.count({timestamp: {\$gte: new Date(Date.now() - 24*60*60*1000)}})" --quiet 2>/dev/null || echo "0")
echo "  Audit logs (24h): $RECENT_LOGS"

if [ "$RECENT_LOGS" -gt 10 ]; then
    echo "✅ Activity: System actively processing"
else
    echo "⚠️ Activity: Low recent activity"
fi

echo ""
echo "=== Health Check Summary ==="
echo "Run this script daily to monitor system health."
echo "For detailed troubleshooting, see 60_documentation/troubleshooting_guide.md"