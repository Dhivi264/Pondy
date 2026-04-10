# Database Schema & Relationships

## Entity-Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Notification System ERD                         │
└─────────────────────────────────────────────────────────────────────────┘

                              CAMERAS (existing)
                              ┌──────────────┐
                              │ id (PK)      │
                              │ name         │
                              │ location     │
                              │ status       │
                              │ frame_rate   │
                              │ stream_url   │
                              │ created_at   │
                              └──────┬───────┘
                                     │
                  ┌──────────────────┼──────────────────┐
                  ▼                  ▼                  ▼
    ┌─────────────────────┐  ┌──────────────────┐  ┌──────────────────────┐
    │CAMERA_HEALTH_LOGS   │  │NOTIFICATION_ALERTS│ │SYSTEM_RECOMMENDATIONS│
    ├─────────────────────┤  ├──────────────────┤  ├──────────────────────┤
    │ id (PK)             │  │ id (PK)          │  │ id (PK)              │
    │ camera_id (FK)      │  │ camera_id (FK)   │  │ camera_id (FK)       │
    │ status              │  │ alert_type       │  │ category             │
    │ uptime_percentage   │  │ title            │  │ title                │
    │ failure_count       │  │ message          │  │ description          │
    │ recovery_time_sec   │  │ severity         │  │ success_probability  │
    │ issue_type          │  │ confidence_score │  │ recommended_update   │
    │ error_message       │  │ recommended_act  │  │ apply_automatically  │
    │ is_recurring_issue  │  │ auto_fix_applied │  │ is_applied           │
    │ pattern_score       │  │ is_read          │  │ is_dismissed         │
    │ created_at          │  │ is_resolved      │  │ created_at           │
    │ timestamp           │  │ created_at       │  │ applied_at           │
    └─────────────────────┘  │ updated_at       │  └──────────────────────┘
                              └──────────────────┘

                         ┌──────────────────────────────────┐
                         │    HEALTH_CHECK_LOGS             │
                         ├──────────────────────────────────┤
                         │ id (PK)                          │
                         │ scan_timestamp                   │
                         │ total_cameras                    │
                         │ cameras_online                   │
                         │ cameras_offline                  │
                         │ cameras_with_issues              │
                         │ new_alerts_generated             │
                         │ recommendations_generated        │
                         │ auto_fixes_applied               │
                         │ scan_results (JSON)              │
                         │ created_at                       │
                         └──────────────────────────────────┘
```

## Detailed Table Schemas

### CAMERA_HEALTH_LOGS

**Purpose**: Track health metrics and failures for each camera over time

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | Integer | NO | Primary key |
| camera_id | Integer | NO | Foreign key to cameras.id |
| status | String | NO | Current status: healthy, warning, critical, offline |
| uptime_percentage | Float | YES | 0-100 percentage uptime |
| last_frame_time | DateTime | YES | Last timestamp when frame was received |
| failure_count | Integer | YES | Number of consecutive failures |
| recovery_time_seconds | Integer | YES | Time taken to recover (seconds) |
| issue_type | String | YES | Type of issue: connection, fps_drop, blur, etc |
| error_message | String | YES | Detailed error message |
| is_recurring_issue | Boolean | YES | Flag: true if issue appears repeatedly |
| pattern_score | Float | YES | Confidence score 0-1 based on patterns |
| created_at | DateTime | NO | When log was created |
| timestamp | DateTime | NO | Actual timestamp of health check |

**Indexes**:
- PRIMARY KEY (id)
- INDEX (camera_id)
- INDEX (created_at DESC)
- INDEX (status)

**Queries**:
```sql
-- Get recent logs for camera
SELECT * FROM camera_health_logs 
WHERE camera_id = 1 
ORDER BY created_at DESC LIMIT 10;

-- Count failures in 24 hours
SELECT COUNT(*) FROM camera_health_logs 
WHERE camera_id = 1 
AND status != 'healthy' 
AND created_at >= datetime('now', '-24 hours');

-- Get recurring issues
SELECT issue_type, COUNT(*) as count
FROM camera_health_logs 
WHERE camera_id = 1 AND is_recurring_issue = 1
GROUP BY issue_type;

-- Average uptime last 7 days
SELECT AVG(uptime_percentage) as avg_uptime
FROM camera_health_logs 
WHERE camera_id = 1 
AND created_at >= datetime('now', '-7 days');
```


### NOTIFICATION_ALERTS

**Purpose**: Store alerts for system administrators about issues

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | Integer | NO | Primary key |
| camera_id | Integer | YES | Foreign key, NULL for system-wide alerts |
| alert_type | String | NO | Type: camera_offline, fps_drop, memory, etc |
| title | String | NO | Short alert title |
| message | String | NO | Detailed message |
| severity | String | NO | Level: critical, warning, info |
| recommended_action | String | YES | Suggested action to resolve |
| auto_fix_applied | Boolean | YES | Whether auto-fix was attempted |
| auto_fix_details | JSON | YES | Details about auto-fix attempt |
| is_read | Boolean | NO | Admin has seen alert |
| is_resolved | Boolean | NO | Issue has been resolved |
| confidence_score | Float | YES | 0-1 probability that alert is accurate |
| created_at | DateTime | NO | When alert was created |
| updated_at | DateTime | NO | Last update timestamp |

**Indexes**:
- PRIMARY KEY (id)
- INDEX (camera_id)
- INDEX (is_read, severity DESC)
- INDEX (is_resolved, created_at DESC)

**Queries**:
```sql
-- Get all unread critical alerts
SELECT * FROM notification_alerts
WHERE is_read = 0 AND severity = 'critical'
ORDER BY created_at DESC;

-- Count alerts by severity
SELECT severity, COUNT(*) as count
FROM notification_alerts 
WHERE is_resolved = 0
GROUP BY severity;

-- Get alerts for specific camera
SELECT * FROM notification_alerts
WHERE camera_id = 1
ORDER BY created_at DESC LIMIT 20;

-- Alerts created in last 1 hour
SELECT * FROM notification_alerts
WHERE created_at >= datetime('now', '-1 hour')
ORDER BY created_at DESC;
```


### SYSTEM_RECOMMENDATIONS

**Purpose**: Store AI-generated recommendations for config/setting changes

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | Integer | NO | Primary key |
| camera_id | Integer | YES | Foreign key, NULL for system-wide recommendations |
| category | String | NO | Type: config, settings, firmware, bugfix, optimization |
| title | String | NO | Recommendation title |
| description | String | NO | Detailed explanation |
| based_on_patterns | String | YES | JSON: analysis data that drove recommendation |
| success_probability | Float | YES | 0-1 estimated success rate |
| recommended_update | JSON | YES | Specific config changes to apply |
| apply_automatically | Boolean | YES | Can be auto-applied without approval |
| is_applied | Boolean | NO | Recommendation has been applied |
| is_dismissed | Boolean | NO | Admin dismissed the recommendation |
| applied_at | DateTime | YES | When successfully applied |
| is_read | Boolean | NO | Admin has viewed recommendation |
| created_at | DateTime | NO | When recommendation was generated |
| updated_at | DateTime | NO | Last update timestamp |

**Indexes**:
- PRIMARY KEY (id)
- INDEX (camera_id)
- INDEX (is_applied, is_dismissed)
- INDEX (success_probability DESC)

**Queries**:
```sql
-- Get active recommendations (not applied/dismissed)
SELECT * FROM system_recommendations
WHERE is_applied = 0 AND is_dismissed = 0
ORDER BY success_probability DESC;

-- High-confidence recommendations
SELECT * FROM system_recommendations
WHERE success_probability >= 0.8
AND is_applied = 0
AND is_dismissed = 0;

-- Already-applied recommendations
SELECT * FROM system_recommendations
WHERE is_applied = 1
ORDER BY applied_at DESC LIMIT 10;

-- Recommendations by category
SELECT category, COUNT(*) as count
FROM system_recommendations
WHERE is_applied = 0 AND is_dismissed = 0
GROUP BY category;
```


### HEALTH_CHECK_LOGS

**Purpose**: Record results of periodic 10-minute health check scans

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | Integer | NO | Primary key |
| scan_timestamp | DateTime | NO | When scan was performed |
| total_cameras | Integer | YES | Total cameras in system |
| cameras_online | Integer | YES | Number of online cameras |
| cameras_offline | Integer | YES | Number of offline cameras |
| cameras_with_issues | Integer | YES | Cameras with detected issues |
| new_alerts_generated | Integer | YES | Number of new alerts created |
| recommendations_generated | Integer | YES | Number of recommendations created |
| auto_fixes_applied | Integer | YES | Number of auto-fixes attempted |
| scan_results | JSON | YES | Detailed scan data and analysis |
| created_at | DateTime | NO | When log entry was created |

**Indexes**:
- PRIMARY KEY (id)
- INDEX (scan_timestamp DESC)

**Queries**:
```sql
-- Recent scans
SELECT * FROM health_check_logs
ORDER BY scan_timestamp DESC LIMIT 10;

-- Scan trend last 24 hours
SELECT 
  DATE(scan_timestamp) as date,
  TIME(scan_timestamp) as time,
  cameras_online,
  cameras_offline,
  cameras_with_issues
FROM health_check_logs
WHERE scan_timestamp >= datetime('now', '-24 hours')
ORDER BY scan_timestamp;

-- Alert generation trend
SELECT 
  DATE(scan_timestamp) as date,
  SUM(new_alerts_generated) as total_alerts,
  SUM(recommendations_generated) as total_recs
FROM health_check_logs
WHERE scan_timestamp >= datetime('now', '-7 days')
GROUP BY DATE(scan_timestamp);

-- System availability percentage
SELECT 
  ROUND(100.0 * SUM(cameras_online) / (SUM(total_cameras) * 1.0), 2) as avg_availability
FROM health_check_logs
WHERE scan_timestamp >= datetime('now', '-7 days');
```


## Data Flow Examples

### Example 1: Camera Offline Detection & Alert

```
Timeline:
Hour 15:00 - First offline detection
├─ Camera 1 status = "offline" in database
├─ HealthCheckWorker triggers
├─ CameraHealthLog created: status="offline", pattern_score=0.95
├─ NotificationAlert created: severity="critical", confidence=0.95
└─ Admin sees critical alert

Hour 15:10 - Still offline (second check)
├─ CameraHealthLog created: status="offline", failure_count=2
├─ pattern_score increases
└─ No new alert (same issue)

Hour 15:20 - Still offline (third check)
├─ CameraHealthLog created: is_recurring_issue=1
├─ SystemRecommendation created: "Check camera power"
└─ Alert now marked for admin action

Hour 15:30 - Camera comes back online
├─ Camera status changes to online
├─ CameraHealthLog created: status="healthy"
├─ Alert marked as resolved by system
└─ Recovery tracked
```

### Example 2: FPS Performance Degradation

```
Timeline:
Over 6 hours, camera FPS slowly drops from 15 to 2

Hour 12:00 - Frame rate still good
├─ CameraHealthLog: fps=15, status=healthy
└─ No action

Hour 14:00 - Slight degradation
├─ CameraHealthLog: fps=12, status=warning
└─ Minor issue noted

Hour 16:00 - Significant degradation  
├─ CameraHealthLog count reaches 3+
├─ Pattern detected: recurring fps_drop
├─ NotificationAlert created: severity=warning
├─ SystemRecommendation: "Reduce frame rate to 10"
└─ success_probability=0.75 (based on similar past issues)

Hour 16:10 - Admin takes action
├─ Admin views recommendation
├─ Clicks "Apply"
├─ Camera frame_rate updated to 10
├─ SystemRecommendation marked as_applied
├─ Next scan confirms improvement
└─ Alert severity reduced to info
```


## Maintenance & Optimization

### Index Strategy
```sql
-- Add these indexes for optimal performance
CREATE INDEX idx_health_camera_id ON camera_health_logs(camera_id);
CREATE INDEX idx_health_created_at ON camera_health_logs(created_at DESC);
CREATE INDEX idx_alert_camera_id ON notification_alerts(camera_id);
CREATE INDEX idx_alert_status ON notification_alerts(is_read, is_resolved);
CREATE INDEX idx_rec_camera_id ON system_recommendations(camera_id);
CREATE INDEX idx_rec_status ON system_recommendations(is_applied, is_applied);
CREATE INDEX idx_scan_timestamp ON health_check_logs(scan_timestamp DESC);
```

### Data Retention Policy
```python
# Auto-clean old logs (optional, in NotificationService)
def cleanup_old_logs(self, days_to_keep=30):
    cutoff = datetime.utcnow() - timedelta(days=days_to_keep)
    
    # Keep resolved alerts longer than health logs
    self.health_repo.db.query(CameraHealthLog).filter(
        CameraHealthLog.created_at < cutoff
    ).delete()
    
    # Archive old scans after 90 days
    cutoff_90 = datetime.utcnow() - timedelta(days=90)
    self.scan_repo.db.query(HealthCheckLog).filter(
        HealthCheckLog.scan_timestamp < cutoff_90
    ).delete()
```

### Backup Strategy
```bash
# Daily backup of notification data
sqlite3 db.sqlite3 ".backup 'db.backup.sqlite3'"

# Query important metrics before deletion
SELECT COUNT(*) FROM camera_health_logs;
SELECT COUNT(*) FROM notification_alerts WHERE is_resolved = 0;
SELECT AVG(uptime_percentage) FROM camera_health_logs;
```

## Monitoring Queries

### System Health Dashboard
```sql
-- Overall system status
SELECT 
  COUNT(DISTINCT camera_id) as total_cameras,
  SUM(CASE WHEN status = 'online' THEN 1 ELSE 0 END) as online,
  SUM(CASE WHEN status = 'offline' THEN 1 ELSE 0 END) as offline,
  SUM(CASE WHEN status = 'warning' THEN 1 ELSE 0 END) as warning
FROM camera_health_logs 
WHERE created_at = (SELECT MAX(created_at) FROM camera_health_logs);

-- Active alerts summary
SELECT 
  severity,
  COUNT(*) as count
FROM notification_alerts
WHERE is_resolved = 0
GROUP BY severity;

-- Alert trend (24 hours)
SELECT 
  HOUR(created_at) as hour,
  COUNT(*) as alerts_created
FROM notification_alerts
WHERE created_at >= datetime('now', '-24 hours')
GROUP BY HOUR(created_at);
```

## Schema Evolution

If you need to add new fields in the future:

```python
# In a migration file:
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('camera_health_logs', 
        sa.Column('network_latency_ms', sa.Float(), nullable=True))
    op.add_column('notification_alerts',
        sa.Column('escalation_level', sa.Integer(), nullable=True))

def downgrade():
    op.drop_column('camera_health_logs', 'network_latency_ms')
    op.drop_column('notification_alerts', 'escalation_level')
```
