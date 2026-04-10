import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/models.dart';
import '../services/api_service.dart';

final authProvider = StateProvider<bool>((ref) => false);

final backendOnlineProvider = FutureProvider<bool>((ref) async {
  return ApiService.instance.ping();
});

final dashboardSummaryProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  try {
    return await ApiService.instance.getLmpDashboard();
  } catch (_) {
    return {
      'total_cameras': 0, 'active_cameras': 0,
      'offline_cameras': 0, 'employees': 0,
      'attendance_records': 0, 'archive_items': 0,
      'fusion_events_today': 0, 'anomalies_today': 0, 'critical_anomalies': 0,
      'pending_al_samples': 0, 'avg_face_confidence': 0.0,
      'employees_at_risk': 0, 'longitudinal_coverage_days': 0,
    };
  }
});

final cameraSearchQueryProvider = StateProvider<String>((ref) => '');

final camerasProvider = FutureProvider<List<CameraModel>>((ref) async {
  final search = ref.watch(cameraSearchQueryProvider);
  try {
    final raw = await ApiService.instance.getCameras(search: search.isEmpty ? null : search);
    return raw.map<CameraModel>((j) => CameraModel(
      id: j['camera_id'] as String? ?? j['id']?.toString() ?? j['cameraId'] as String? ?? '',
      name: j['name'] as String? ?? 'Camera',
      channel: 1,
      status: ((j['status'] ?? 'online') as String) == 'online' ? CameraStatus.online : CameraStatus.offline,
      fps: j['fps'] as int? ?? j['frameRate'] as int? ?? 25,
      isAiActive: j['is_ai_active'] as bool? ?? j['isAiActive'] as bool? ?? true,
      location: j['location'] as String? ?? 'Zone A',
      isRecording: ((j['status'] ?? 'online') as String) == 'online',
      streamUrl: (j['stream_url'] ?? j['streamUrl']) != null ? '$kBackendBase${j['stream_url'] ?? j['streamUrl']}' : null,
    )).toList();
  } catch (_) {
    return [];
  }
});

final employeeSearchQueryProvider = StateProvider<String>((ref) => '');

final employeesProvider = FutureProvider<List<EmployeeModel>>((ref) async {
  final search = ref.watch(employeeSearchQueryProvider);
  try {
    final raw = await ApiService.instance.getEmployees(search: search.isEmpty ? null : search);
    return raw.map<EmployeeModel>((j) => EmployeeModel(
        id: j['id'].toString(), 
        empId: (j['employee_id'] ?? j['employee_code'] ?? '').toString(),
        name: j['name'] as String? ?? 'Employee', 
        department: j['department'] as String? ?? 'General',
        designation: j['designation'] as String? ?? j['role'] as String? ?? 'Staff', 
        phone: j['phone'] as String? ?? '', 
        email: j['email'] as String? ?? '',
        hasRegisteredFace: j['has_face_enrolled'] as bool? ?? false,
        dateAdded: j['created_at'] != null ? DateTime.tryParse(j['created_at']) ?? DateTime.now() : DateTime.now(),
      )).toList();
  } catch (e) {
    debugPrint('[EmployeesProvider] Error: $e');
    return [];
  }
});

final attendanceProvider = FutureProvider<List<AttendanceModel>>((ref) async {
  try {
    final raw = await ApiService.instance.getAttendance();
    return raw.map<AttendanceModel>((j) {
      final s = ((j['attendanceStatus'] ?? j['attendance_status'] ?? j['status'] ?? '') as String).toLowerCase();
      return AttendanceModel(
        id: j['id'].toString(), 
        employeeId: (j['employee_id'] ?? j['employeeId'] ?? '').toString(),
        employeeName: j['employeeName'] as String? ?? j['employee_id']?.toString() ?? 'Unknown',
        date: DateTime.tryParse(j['attendanceDate'] as String? ?? j['record_date'] as String? ?? '') ?? DateTime.now(),
        checkInTime: j['entryTime'] != null ? DateTime.tryParse(j['entryTime'] as String) : null,
        checkOutTime: j['exitTime'] != null ? DateTime.tryParse(j['exitTime'] as String) : null,
        status: s == 'present' ? AttendanceStatus.present : s == 'late' ? AttendanceStatus.late : AttendanceStatus.absent,
        confidenceScore: 0.9, cameraSource: 'Main Entrance',
      );
    }).toList();
  } catch (_) {
    return [];
  }
});

final attendanceStatsProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  try {
    return await ApiService.instance.getAttendanceStats();
  } catch (_) {
    return {
      'total_records': 0, 'present': 0, 'absent': 0, 'late': 0,
    };
  }
});

final archivesProvider = FutureProvider<List<ArchiveModel>>((ref) async {
  try {
    final raw = await ApiService.instance.getArchives();
    return raw.map<ArchiveModel>((j) => ArchiveModel(
      id: j['id'].toString(), cameraId: j['camera_id'] as String? ?? '',
      cameraName: j['camera_id'] as String? ?? 'Camera',
      timestamp: DateTime.tryParse(j['start_time'] as String? ?? '') ?? DateTime.now(),
      durationSeconds: 60, type: ArchiveType.all,
      description: j['record_type'] as String?,
      filePath: j['file_path'] as String?,
    )).toList();
  } catch (_) {
    return [];
  }
});

final lmpAnomaliesProvider = FutureProvider<List<dynamic>>((ref) async {
  try { return await ApiService.instance.getAnomalies(); } catch (_) { return []; }
});

final lmpProfilesProvider = FutureProvider<List<dynamic>>((ref) async {
  try { return await ApiService.instance.getLongitudinalProfiles(riskOnly: true); } catch (_) { return []; }
});

final lmpPendingSamplesProvider = FutureProvider<List<dynamic>>((ref) async {
  try { return await ApiService.instance.getPendingAlSamples(limit: 15); } catch (_) { return []; }
});

final lmpFusionEventsProvider = FutureProvider<List<dynamic>>((ref) async {
  try { return await ApiService.instance.getFusionEvents(limit: 10); } catch (_) { return []; }
});

final hardwareProfileProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  try { return await ApiService.instance.getHardwareProfile(); } catch (_) {
    return {'detected_profile': 'workstation', 'yolo_variant': 'yolov8m',
      'yolo_backend': 'pytorch', 'default_skip_rate': 2,
      'max_resolution_w': 1280, 'max_resolution_h': 720,
      'notes': 'Backend offline — showing defaults.'};
  }
});

final bufferStatsProvider = FutureProvider<List<dynamic>>((ref) async {
  try { return await ApiService.instance.getBufferStats(); } catch (_) { return []; }
});

final reconnectStatsProvider = FutureProvider<List<dynamic>>((ref) async {
  try { return await ApiService.instance.getReconnectStats(); } catch (_) { return []; }
});

final systemAiStatusProvider = FutureProvider<bool>((ref) async {
  return ApiService.instance.getSystemAiStatus();
});

final watchdogStatusProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  try {
    return await ApiService.instance.getLmpDashboard(); // Or a specific /health endpoint if preferred
  } catch (_) {
    return {'is_running': false, 'repair_history': [], 'repaired': {}};
  }
});

