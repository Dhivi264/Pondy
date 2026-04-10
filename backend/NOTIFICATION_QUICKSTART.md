"""
Quick Start Guide for Notification System
"""

# ============================================================================
# STEP 1: Database Setup (Automatic on startup)
# ============================================================================
# When the backend starts, it automatically creates all tables:
# - camera_health_logs
# - notification_alerts
# - system_recommendations
# - health_check_logs
#
# This is handled by app/main.py:
# ```python
# Base.metadata.create_all(bind=engine)
# ```


# ============================================================================
# STEP 2: System Startup Flow
# ============================================================================
# In app/main.py startup_event():
# 
# 1. Create required directories
# 2. Start StreamWorker (AI pipeline)
# 3. Start SystemWatchdog (error recovery)
# 4. Start HealthCheckWorker (health monitoring) ← NEW
# 5. Start BatchEngine (offline processing)
#
# HealthCheckWorker will automatically run a health check every 10 minutes


# ============================================================================
# STEP 3: Manual Health Check (for immediate testing)
# ============================================================================

# Endpoint: POST /lmp/notifications/scan-now
# or:       POST /notifications/scan-now
#
# Example:
# curl -X POST http://localhost:8000/lmp/notifications/scan-now \
#   -H "Authorization: Bearer YOUR_JWT_TOKEN"
#
# Response:
# {
#   "id": 1,
#   "scan_timestamp": "2026-03-31T15:30:00",
#   "total_cameras": 5,
#   "cameras_online": 4,
#   "cameras_offline": 1,
#   "cameras_with_issues": 1,
#   "new_alerts_generated": 2,
#   "recommendations_generated": 1,
#   "auto_fixes_applied": 0,
#   "scan_results": {...},
#   "created_at": "2026-03-31T15:30:00"
# }


# ============================================================================
# STEP 4: View System Health
# ============================================================================

# Endpoint: GET /lmp/notifications/health-summary
# or:       GET /notifications/health-summary
#
# Example:
# curl http://localhost:8000/lmp/notifications/health-summary \
#   -H "Authorization: Bearer YOUR_JWT_TOKEN"
#
# Response:
# {
#   "total_cameras": 5,
#   "online_cameras": 4,
#   "offline_cameras": 1,
#   "critical_alerts": 1,
#   "warning_alerts": 2,
#   "active_recommendations": 1,
#   "last_scan": {
#     "id": 1,
#     "scan_timestamp": "2026-03-31T15:30:00",
#     ...
#   }
# }


# ============================================================================
# STEP 5: View Alerts
# ============================================================================

# List all unresolved alerts:
# curl "http://localhost:8000/lmp/notifications/alerts?unread_only=false&limit=50" \
#   -H "Authorization: Bearer YOUR_JWT_TOKEN"
#
# List only unread alerts:
# curl "http://localhost:8000/lmp/notifications/alerts?unread_only=true" \
#   -H "Authorization: Bearer YOUR_JWT_TOKEN"
#
# Get alerts for specific camera:
# curl "http://localhost:8000/lmp/notifications/alerts/camera/1" \
#   -H "Authorization: Bearer YOUR_JWT_TOKEN"


# ============================================================================
# STEP 6: Mark Alert as Read/Resolved
# ============================================================================

# Mark as read:
# curl -X PUT http://localhost:8000/lmp/notifications/alerts/1 \
#   -H "Authorization: Bearer YOUR_JWT_TOKEN" \
#   -H "Content-Type: application/json" \
#   -d '{"is_read": true}'
#
# Mark as resolved:
# curl -X PUT http://localhost:8000/lmp/notifications/alerts/1 \
#   -H "Authorization: Bearer YOUR_JWT_TOKEN" \
#   -H "Content-Type: application/json" \
#   -d '{"is_resolved": true}'


# ============================================================================
# STEP 7: View Recommendations
# ============================================================================

# List active recommendations:
# curl "http://localhost:8000/lmp/notifications/recommendations?active_only=true" \
#   -H "Authorization: Bearer YOUR_JWT_TOKEN"
#
# Get recommendations for specific camera:
# curl "http://localhost:8000/lmp/notifications/recommendations/camera/1" \
#   -H "Authorization: Bearer YOUR_JWT_TOKEN"


# ============================================================================
# STEP 8: Apply or Dismiss Recommendation
# ============================================================================

# Apply a recommendation:
# curl -X PUT http://localhost:8000/lmp/notifications/recommendations/1/apply \
#   -H "Authorization: Bearer YOUR_JWT_TOKEN"
#
# Dismiss a recommendation:
# curl -X PUT http://localhost:8000/lmp/notifications/recommendations/1/dismiss \
#   -H "Authorization: Bearer YOUR_JWT_TOKEN"


# ============================================================================
# STEP 9: Get Camera Health Details
# ============================================================================

# Get detailed health for specific camera:
# curl "http://localhost:8000/lmp/notifications/camera/1/health" \
#   -H "Authorization: Bearer YOUR_JWT_TOKEN"
#
# Response includes:
# - Current status
# - Recent health logs (last 10)
# - Active alerts (last 10)
# - Recommendations (last 10)


# ============================================================================
# STEP 10: View Health Check History
# ============================================================================

# Get last 10 health check scans:
# curl "http://localhost:8000/lmp/notifications/scans?limit=10" \
#   -H "Authorization: Bearer YOUR_JWT_TOKEN"


# ============================================================================
# PYTHON USAGE EXAMPLE
# ============================================================================

import requests
import json

BASE_URL = "http://localhost:8000"
JWT_TOKEN = "YOUR_JWT_TOKEN_HERE"

headers = {"Authorization": f"Bearer {JWT_TOKEN}"}

# 1. Get health summary
response = requests.get(f"{BASE_URL}/lmp/notifications/health-summary", headers=headers)
print("System Health:", response.json())

# 2. Trigger manual scan
response = requests.post(f"{BASE_URL}/lmp/notifications/scan-now", headers=headers)
print("Scan Result:", response.json())

# 3. Get all unresolved alerts
response = requests.get(
    f"{BASE_URL}/lmp/notifications/alerts?unread_only=false&limit=50",
    headers=headers
)
alerts = response.json()
print(f"\nFound {len(alerts)} unresolved alerts:")
for alert in alerts:
    print(f"  - [{alert['severity']}] {alert['title']}")
    print(f"    Message: {alert['message']}")
    print(f"    Confidence: {alert['confidence_score']:.1%}")

# 4. Mark first alert as read
if alerts:
    alert_id = alerts[0]['id']
    response = requests.put(
        f"{BASE_URL}/lmp/notifications/alerts/{alert_id}",
        headers=headers,
        json={"is_read": True}
    )
    print(f"\nMarked alert {alert_id} as read")

# 5. Get active recommendations
response = requests.get(
    f"{BASE_URL}/lmp/notifications/recommendations?active_only=true",
    headers=headers
)
recommendations = response.json()
print(f"\nFound {len(recommendations)} active recommendations:")
for rec in recommendations:
    print(f"  - [{rec['category']}] {rec['title']}")
    print(f"    Success Probability: {rec['success_probability']:.1%}")

# 6. Apply first recommendation
if recommendations:
    rec_id = recommendations[0]['id']
    response = requests.put(
        f"{BASE_URL}/lmp/notifications/recommendations/{rec_id}/apply",
        headers=headers
    )
    print(f"\nApplied recommendation {rec_id}")


# ============================================================================
# DATABASE SCHEMA INSPECTION
# ============================================================================

# To manually check the database for notifications:
# sqlite3 db.sqlite3
#
# Show tables:
# .tables
#
# Check camera health logs:
# SELECT * FROM camera_health_logs ORDER BY created_at DESC LIMIT 10;
#
# Check alerts:
# SELECT id, alert_type, title, severity, is_read, created_at FROM notification_alerts ORDER BY created_at DESC;
#
# Check recommendations:
# SELECT id, category, title, success_probability, is_applied FROM system_recommendations ORDER BY created_at DESC;
#
# Check scan history:
# SELECT * FROM health_check_logs ORDER BY scan_timestamp DESC LIMIT 10;


# ============================================================================
# ARCHITECTURE WALK-THROUGH
# ============================================================================

# The system works like this:
#
# 1. EVERY 10 MINUTES (Automatic):
#    └─ HealthCheckWorker wakes up
#    └─ Calls NotificationService.perform_health_check_scan()
#    └─ For each camera:
#       ├─ Checks current status in database
#       ├─ Logs health (CameraHealthLog)
#       ├─ Analyzes recent failures
#       ├─ If issues detected:
#       │  ├─ Generates Alert (if confidence > 0.7)
#       │  └─ Generates Recommendation (if pattern recurring)
#       └─ Stores results in HealthCheckLog
#
# 2. LEARNING MECHANISM:
#    └─ System tracks failure patterns over 24 hours
#    └─ Calculates confidence score based on:
#       ├─ Failure rate (failures / total scans)
#       ├─ Number of data points
#       └─ Recurring nature of issues
#    └─ Higher confidence = higher alert severity
#    └─ Can trigger auto-fix if confidence > 0.8
#
# 3. ADMIN NOTIFICATIONS:
#    └─ Unread alerts appear in health dashboard
#    └─ Admin can view details per camera
#    └─ Admin can manually resolve/dismiss alerts
#    └─ Recommendations show success probability
#    └─ Admin can apply or reject recommendations
#
# 4. AUTO-HEALING (Future):
#    └─ System can automatically apply fixes
#    └─ For offline cameras: try reconnection
#    └─ For FPS drops: reduce frame rate
#    └─ For memory issues: clear old recordings


# ============================================================================
# CONFIGURATION
# ============================================================================

# To change scan interval, edit app/workers/health_check_worker.py:
# health_check_worker = HealthCheckWorker(interval_minutes=10)  # Change 10 to desired minutes
#
# To change alert confidence threshold, edit app/services/notification_service.py:
# In perform_health_check_scan():
# if analysis.get("confidence", 0) > 0.7:  # Change 0.7 to desired threshold


# ============================================================================
# MONITORING & LOGGING
# ============================================================================

# Watch the health check logs:
# tail -f logs/app.log | grep "HealthCheck"
#
# Expected output:
# [HealthCheck] Worker started (10-minute interval)
# [HealthCheck] Starting scheduled health scan...
# [HealthCheck] Scan complete: 4/5 online, 1 alerts, 2 recommendations
#
# Debug individual camera analysis:
# Enable DEBUG logging in app/config.py


# ============================================================================
# TROUBLESHOOTING
# ============================================================================

# Q: Scans not running?
# A: Check if HealthCheckWorker.start() is called in main.py startup event
#
# Q: Alerts not being generated?
# A: Check confidence threshold and ensure cameras are being marked offline
#
# Q: Recommendations not appearing?
# A: Ensure pattern_score > 0.7 and recurring issues are detected
#
# Q: Performance issues?
# A: Health checks run in separate thread, shouldn't affect main app
#
# Q: Database growing too large?
# A: Implement log rotation in notification_service.py
