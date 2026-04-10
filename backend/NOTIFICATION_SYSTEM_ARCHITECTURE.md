# Smart CCTV - Notification System Architecture

## Overview
The notification system provides intelligent health monitoring, failure analysis, and automated recommendations for camera management.

## Core Components

### 1. **Models** (Database Layer)
- **CameraHealthLog**: Tracks camera health metrics and failures
- **NotificationAlert**: System notifications for admins
- **SystemRecommendation**: AI-generated recommendations for updates
- **HealthCheckLog**: Records of periodic system scans

### 2. **Repositories** (Data Access Layer)
- **CameraHealthLogRepository**: CRUD operations for health logs
- **NotificationAlertRepository**: Alert management
- **SystemRecommendationRepository**: Recommendation management
- **HealthCheckLogRepository**: Scan log management

### 3. **Services** (Business Logic Layer)
- **NotificationService**: Core notification logic
  - `log_camera_health()`: Record health status
  - `analyze_camera_failure()`: Pattern analysis with learning
  - `generate_alert()`: Create alerts
  - `generate_recommendation()`: Generate recommendations
  - `perform_health_check_scan()`: 10-min scan cycle
  - `apply_auto_fix()`: Self-healing mechanism

### 4. **Workers** (Background Processing)
- **HealthCheckWorker**: Runs every 10 minutes
  - Scans all cameras
  - Analyzes failure patterns
  - Generates alerts and recommendations
  - Logs scan results

### 5. **Routers** (API Layer)
- **NotificationsRouter**: REST endpoints
  - `/notifications/health-summary`: Overall system health
  - `/notifications/alerts`: List and manage alerts
  - `/notifications/recommendations`: List and apply recommendations
  - `/notifications/scans`: View health check scans
  - `/notifications/scan-now`: Manual trigger

## System Flow

```
Every 10 Minutes:
┌─────────────────────────────────────┐
│  HealthCheckWorker Triggers Scan    │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ NotificationService.perform_health_ │
│       check_scan()                  │
└────────┬────────────────────────────┘
         │
         ├─► Fetch all cameras
         │
         ├─► Check each camera status
         │
         ├─► Log health status
         │
         ├─► Analyze failure patterns
         │
         ├─► IF critical issue:
         │   └─► Generate Alert
         │       └─► Store in DB
         │       └─► Increase severity
         │
         ├─► IF recurring patterns:
         │   └─► Generate Recommendation
         │       └─► Calculate success probability
         │       └─► Store in DB
         │
         └─► Create HealthCheckLog
             └─► Store scan results
             └─► Return summary

Admin/Frontend:
┌──────────────────────────────────┐
│ Get Health Summary               │
│ (System-wide overview)           │
├──────────────────────────────────┤
│ - Total cameras                  │
│ - Online/Offline count           │
│ - Critical alerts                │
│ - Active recommendations         │
│ - Last scan timestamp            │
└──────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│ View Alerts & Recommendations    │
│ (Per-camera or system-wide)      │
├──────────────────────────────────┤
│ - Alert type                     │
│ - Severity level                 │
│ - Recommended action             │
│ - Confidence score               │
│ - Read/Resolved status           │
└──────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│ Apply Recommendations            │
│ (Admin action)                   │
├──────────────────────────────────┤
│ - Mark as applied                │
│ - Mark as dismissed              │
│ - Auto-apply if enabled          │
└──────────────────────────────────┘
```

## Learning Mechanism

### Pattern Analysis
```
1. Historical Data Collection
   └─► Every 10 min: log camera health
   
2. Pattern Detection (24-hour window)
   └─► Count failures in past 24h
   └─► Identify recurring issues
   └─► Calculate failure rate
   
3. Confidence Scoring
   └─► pattern_score = failure_rate (0-1)
   └─► confidence = pattern_score + (0.1 × log_count)
   └─► confidence cap at 1.0
   
4. Recommendation Generation
   └─► IF confidence > 0.7:
       └─► Generate optimization recommendation
       └─► Base success probability on pattern history
       └─► Include analysis details
```

## Auto-Healing Mechanism

```
Issue Detection → Alert Generation → Auto-Fix Attempt

Fix Types:
1. Offline Camera
   └─► Attempt reconnection
   └─► Reset status to "online"
   
2. FPS Drop
   └─► Reduce frame rate (5fps minimum)
   └─► Update camera config
   
3. Memory Issues
   └─► Clear old recordings
   └─► Optimize buffer sizes
```

## Database Schema

### CameraHealthLog
- `id`: Primary key
- `camera_id`: Foreign key to Camera
- `status`: healthy, warning, critical, offline
- `uptime_percentage`: 0-100
- `failure_count`: Number of failures
- `recovery_time_seconds`: Time to recover
- `issue_type`: Type of issue detected
- `error_message`: Error details
- `is_recurring_issue`: Boolean flag
- `pattern_score`: 0-1 confidence value
- `created_at`, `timestamp`: Timestamps

### NotificationAlert
- `id`: Primary key
- `camera_id`: Optional foreign key
- `alert_type`: failure_detected, pattern_warning, config_needed, etc
- `title`, `message`: Alert content
- `severity`: critical, warning, info
- `recommended_action`: Suggested fix
- `auto_fix_applied`: Boolean
- `confidence_score`: 0-1
- `is_read`, `is_resolved`: Status flags

### SystemRecommendation
- `id`: Primary key
- `camera_id`: Optional foreign key
- `category`: config, settings, firmware, bugfix, optimization
- `title`, `description`: Recommendation details
- `based_on_patterns`: JSON analysis data
- `success_probability`: 0-1
- `recommended_update`: JSON config changes
- `apply_automatically`: Auto-apply flag
- `is_applied`, `is_dismissed`: Status flags

### HealthCheckLog
- `id`: Primary key
- `scan_timestamp`: When scan occurred
- `total_cameras`: Count
- `cameras_online/offline/with_issues`: Counts
- `new_alerts_generated`: Count
- `recommendations_generated`: Count
- `auto_fixes_applied`: Count
- `scan_results`: JSON detailed results

## API Endpoints

### Health Summary
```
GET /lmp/notifications/health-summary
GET /notifications/health-summary
Response: {
  "total_cameras": 5,
  "online_cameras": 4,
  "offline_cameras": 1,
  "critical_alerts": 2,
  "warning_alerts": 5,
  "active_recommendations": 3,
  "last_scan": {...}
}
```

### Camera Health Details
```
GET /lmp/notifications/camera/{camera_id}/health
GET /notifications/camera/{camera_id}/health
Response: {
  "camera_id": 1,
  "camera_name": "Entrance",
  "current_status": "online",
  "location": "Main Gate",
  "recent_health_logs": [...],
  "active_alerts": [...],
  "recommendations": [...]
}
```

### Manage Alerts
```
GET /lmp/notifications/alerts?unread_only=false&limit=50
GET /notifications/alerts

PUT /lmp/notifications/alerts/{alert_id}
PUT /notifications/alerts/{alert_id}
Body: {
  "is_read": true,
  "is_resolved": true
}
```

### Manage Recommendations
```
GET /lmp/notifications/recommendations?active_only=true&limit=50
GET /notifications/recommendations

PUT /lmp/notifications/recommendations/{recommendation_id}/apply
PUT /notifications/recommendations/{recommendation_id}/dismiss
```

### View Scans
```
GET /lmp/notifications/scans?limit=10
GET /notifications/scans

POST /lmp/notifications/scan-now (admin only)
POST /notifications/scan-now (admin only)
```

## Configuration

### Scan Interval
Default: 10 minutes
Location: `HealthCheckWorker(interval_minutes=10)`

### Alert Levels
- `critical`: Immediate attention required (cameras offline)
- `warning`: Performance issues detected
- `info`: Recommendations and suggestions

### Confidence Thresholds
- Alert generation: >= 0.7 confidence
- Recommendation generation: >= 0.7 confidence
- Auto-fix application: >= 0.8 confidence (configurable)

## Integration Points

1. **With StreamWorker**
   - HealthCheckWorker reads camera status from Database
   - Uses same camera list for monitoring

2. **With SystemWatchdog**
   - Watchdog handles error recovery
   - Notifications log watchdog actions
   - Shared error tracking mechanism

3. **With Camera Models**
   - Foreign keys to Camera table
   - Updates camera status based on analysis
   - Reads frame_rate and other config

4. **With Dashboard**
   - Health summary visible in dashboard
   - Recent alerts displayed
   - Pending recommendations shown

## Starting the System

In `app/main.py` startup event:
```python
# 1. Ensure directories
os.makedirs(settings.RECORDINGS_DIR, exist_ok=True)
os.makedirs(settings.FACES_DIR, exist_ok=True)

# 2. Start AI Pipeline
stream_worker.start()
watchdog.start()

# 3. Start Health Monitoring (10-min cycles)
health_check_worker.start()

# 4. Start Batch Processing
batch_engine.start()
```

## Monitoring

### Logs
```
[HealthCheck] Worker started (10-minute interval)
[HealthCheck] Starting scheduled health scan...
[HealthCheck] Scan complete: 4/5 online, 1 alerts, 2 recommendations
```

### Metrics
- `cameras_online`: Real-time count
- `failure_count_24h`: Historical metric
- `pattern_score`: 0-1 confidence value
- `confidence_score`: Final alert confidence

## Performance Considerations

- **Scale**: Handles 100+ cameras
- **Scan Time**: ~1-2 seconds per 10 cameras
- **Storage**: ~1KB per health log entry
- **Threads**: Single dedicated thread for scans
- **Blocking**: Non-blocking; scheduled independently

## Security

- Admin-only endpoints for applying recommendations
- All notifications authenticated via JWT tokens
- No sensitive data in alert messages
- Pattern analysis data stored securely
- Recommendation details kept generic

## Future Enhancements

1. **Machine Learning Integration**
   - Predictive failure detection
   - Anomaly detection algorithms
   - Self-learning from past patterns

2. **Notification Channels**
   - Email alerts
   - SMS notifications
   - Push notifications to mobile app
   - Webhook integrations

3. **Advanced Analytics**
   - Trend analysis over weeks/months
   - Comparative camera performance
   - Predictive maintenance scheduling
   - ROI analysis for recommendations

4. **Smart Auto-Healing**
   - Automatic network reconfiguration
   - Load balancing between cameras
   - Dynamic bitrate adjustment
   - Intelligent failover mechanisms
