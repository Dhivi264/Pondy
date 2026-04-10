import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

const String kBackendBase = kReleaseMode 
    ? 'https://smart-cctv-ai-backend.onrender.com' 
    : 'http://localhost:8000';

class ApiException implements Exception {
  final int statusCode;
  final String message;
  ApiException(this.statusCode, this.message);
  @override
  String toString() => 'ApiException($statusCode): $message';
}

class ApiService {
  ApiService._();
  static final ApiService instance = ApiService._();

  String? _token;
  String? get token => _token;
  String get _base => kBackendBase;

  Map<String, String> get _headers => {
    'Content-Type': 'application/json',
    if (_token != null) 'Authorization': 'Bearer $_token',
  };

  // ── Auth ───────────────────────────────────────────────────────────────────

  Future<bool> login(String username, String password) async {
    try {
      final res = await http.post(
        Uri.parse('$_base/auth/token'),
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: {'username': username, 'password': password},
      ).timeout(const Duration(seconds: 6));
      if (res.statusCode == 200) {
        _token = jsonDecode(res.body)['access_token'] as String?;
        return true;
      }
      return false;
    } catch (_) {
      return false;
    }
  }

  void logout() => _token = null;
  bool get isLoggedIn => _token != null;

  // ── Generic helpers ────────────────────────────────────────────────────────

  Future<dynamic> _get(String path, {Map<String, String>? params}) async {
    var uri = Uri.parse('$_base$path');
    if (params != null) uri = uri.replace(queryParameters: params);
    final res = await http.get(uri, headers: _headers)
        .timeout(const Duration(seconds: 10));
    if (res.statusCode == 200) return jsonDecode(res.body);
    throw ApiException(res.statusCode, res.body);
  }

  Future<dynamic> post(String path, Map<String, dynamic> body) async {
    final res = await http.post(
      Uri.parse('$_base$path'),
      headers: _headers,
      body: jsonEncode(body),
    ).timeout(const Duration(seconds: 10));
    if (res.statusCode == 200 || res.statusCode == 201) return jsonDecode(res.body);
    throw ApiException(res.statusCode, res.body);
  }

  Future<void> _delete(String path) async {
    final res = await http.delete(Uri.parse('$_base$path'), headers: _headers)
        .timeout(const Duration(seconds: 10));
    if (res.statusCode != 200 && res.statusCode != 204) {
      throw ApiException(res.statusCode, res.body);
    }
  }

  // ── Health ─────────────────────────────────────────────────────────────────

  Future<bool> ping() async {
    try {
      final res = await http.get(Uri.parse(_base), headers: _headers)
          .timeout(const Duration(seconds: 4));
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  // ── Dashboard ──────────────────────────────────────────────────────────────

  Future<Map<String, dynamic>> getLmpDashboard() async =>
      (await _get('/lmp/dashboard/')) as Map<String, dynamic>;

  // ── Cameras ────────────────────────────────────────────────────────────────

  Future<List<dynamic>> getCameras({String? search}) async =>
      (await _get('/cameras/',
          params: search != null ? {'search': search} : null)) as List<dynamic>;

  Future<Map<String, dynamic>> stopSystemAi() async {
    final res = await http.post(Uri.parse('$_base/cameras/system/stop_ai'), headers: _headers, body: '{}');
    if (res.statusCode == 200) return jsonDecode(res.body);
    throw ApiException(res.statusCode, res.body);
  }

  Future<Map<String, dynamic>> startSystemAi() async {
    final res = await http.post(Uri.parse('$_base/cameras/system/start_ai'), headers: _headers, body: '{}');
    if (res.statusCode == 200) return jsonDecode(res.body);
    throw ApiException(res.statusCode, res.body);
  }

  Future<Map<String, dynamic>> stopCameraAi(String cameraId) async {
    final res = await http.post(Uri.parse('$_base/cameras/$cameraId/stop_ai'), headers: _headers, body: '{}');
    if (res.statusCode == 200) return jsonDecode(res.body);
    throw ApiException(res.statusCode, res.body);
  }

  Future<bool> getSystemAiStatus() async {
    try {
      final res = await http.get(Uri.parse('$_base/cameras/system/status_ai'), headers: _headers);
      if (res.statusCode == 200) return jsonDecode(res.body)['is_running'] as bool;
      return false;
    } catch (_) {
      return false;
    }
  }

  // ── Employees ──────────────────────────────────────────────────────────────

  Future<List<dynamic>> getEmployees({String? search}) async =>
      (await _get('/employees/',
          params: search != null ? {'search': search} : null)) as List<dynamic>;

  Future<Map<String, dynamic>> getEmployee(String id) async =>
      (await _get('/employees/$id')) as Map<String, dynamic>;

  Future<Map<String, dynamic>> createEmployee(Map<String, dynamic> data) async {
    if (_token == null) {
      try { await login('admin', 'admin123'); } catch (_) {}
    }
    return (await post('/employees/', data)) as Map<String, dynamic>;
  }

  Future<void> deleteCamera(String id) async {
    if (_token == null) {
      try { await login('admin', 'admin123'); } catch (_) {}
    }
    return _delete('/cameras/$id');
  }

  Future<void> deleteEmployee(String id) async {
    if (_token == null) {
      try { await login('admin', 'admin123'); } catch (_) {}
    }
    return _delete('/employees/$id');
  }

  // ── Attendance ─────────────────────────────────────────────────────────────

  Future<List<dynamic>> getAttendance() async =>
      (await _get('/attendance/')) as List<dynamic>;

  Future<Map<String, dynamic>> getAttendanceStats() async =>
      (await _get('/attendance/summary/stats')) as Map<String, dynamic>;

  // ── Archive ────────────────────────────────────────────────────────────────

  Future<List<dynamic>> getArchives() async =>
      (await _get('/archive/')) as List<dynamic>;

  // ── LMP-TX: AI Platform ────────────────────────────────────────────────────

  Future<List<dynamic>> getAnomalies({String? severity}) async =>
      (await _get('/lmp/anomalies',
          params: severity != null ? {'severity': severity} : null)) as List<dynamic>;

  Future<List<dynamic>> getLongitudinalProfiles({
    int windowDays = 30,
    bool riskOnly  = false,
  }) async =>
      (await _get('/lmp/profiles', params: {
        'window_days': '$windowDays',
        'risk_only':   '$riskOnly',
      })) as List<dynamic>;

  Future<List<dynamic>> getPendingAlSamples({int limit = 20}) async =>
      (await _get('/lmp/al/pending-samples',
          params: {'limit': '$limit'})) as List<dynamic>;

  Future<Map<String, dynamic>> startAlSession(String strategy) async {
    var uri = Uri.parse('$_base/lmp/al/start-session')
        .replace(queryParameters: {'strategy': strategy});
    final res = await http.post(uri, headers: _headers, body: '{}')
        .timeout(const Duration(seconds: 10));
    if (res.statusCode == 200) return jsonDecode(res.body) as Map<String, dynamic>;
    throw ApiException(res.statusCode, res.body);
  }

  Future<Map<String, dynamic>> submitLabel(
      String sampleId, String label, String? employeeId) async =>
      (await post('/lmp/al/label/', {
        'sample_id':   sampleId,
        'label':       label,
        'confirmed_employee_id': employeeId,
        'annotator_id': 'operator',
      })) as Map<String, dynamic>;

  Future<List<dynamic>> getFusionEvents({int limit = 20}) async =>
      (await _get('/lmp/fusion-events',
          params: {'limit': '$limit'})) as List<dynamic>;

  Future<Map<String, dynamic>> getHardwareProfile() async =>
      (await _get('/lmp/hardware/profile')) as Map<String, dynamic>;

  Future<List<dynamic>> getBufferStats() async =>
      (await _get('/lmp/diagnostics/buffers')) as List<dynamic>;

  Future<List<dynamic>> getReconnectStats() async =>
      (await _get('/lmp/diagnostics/reconnects')) as List<dynamic>;

  // ── Footage ──────────────────────────────────────────────────────────────────

  Future<List<dynamic>> getRecordingsList() async =>
      (await _get('/recordings/list')) as List<dynamic>;

  // ── Camera Config (LMP-TX) ─────────────────────────────────────────────────

  Future<Map<String, dynamic>> saveCameraConfig(Map<String, dynamic> data) async =>
      (await post('/lmp/config', data)) as Map<String, dynamic>;

  Future<List<dynamic>> listCameraConfigs() async =>
      (await _get('/lmp/config')) as List<dynamic>;

  Future<Map<String, dynamic>> getCameraConfig(String cameraId) async =>
      (await _get('/lmp/config/$cameraId')) as Map<String, dynamic>;

  Future<Map<String, dynamic>> setCameraSkipRate(String cameraId, int rate) async {
    final uri = Uri.parse('$_base/lmp/cameras/$cameraId/set-skip-rate')
        .replace(queryParameters: {'skip_rate': '$rate'});
    final res = await http.post(uri, headers: _headers, body: '{}')
        .timeout(const Duration(seconds: 10));
    if (res.statusCode == 200) return jsonDecode(res.body) as Map<String, dynamic>;
    throw ApiException(res.statusCode, res.body);
  }

  Future<Map<String, dynamic>> registerCamera(Map<String, dynamic> data) async {
    // Development fallback: automatically ensure we are logged in as admin
    if (_token == null) {
      try {
        await login('admin', 'admin123');
      } catch (e) {
        debugPrint('[ApiService] Auto-login failed: $e');
      }
    }
    return (await post('/cameras/', data)) as Map<String, dynamic>;
  }

  // ── AI Assistant ───────────────────────────────────────────────────────────

  Future<Map<String, dynamic>> askAssistant(
      String question, List<Map<String, String>> history) async =>
      (await post('/ai/ask', {
        'question': question,
        'conversation_history': history,
      })) as Map<String, dynamic>;

  Future<Map<String, dynamic>> getAssistantHealth() async =>
      (await _get('/ai/health')) as Map<String, dynamic>;

  // ── AI MONITORING: Watchdog, Detector, Tracker, Fusion ────────────────────

  /// Get comprehensive Watchdog self-healing AI metrics
  Future<Map<String, dynamic>> getWatchdogStatus() async =>
      (await _get('/ai/health/watchdog')) as Map<String, dynamic>;

  /// Get YOLO11 Detector health metrics (latency, errors, etc.)
  Future<Map<String, dynamic>> getDetectorHealth() async =>
      (await _get('/ai/health/detector')) as Map<String, dynamic>;

  /// Get Tracker state and statistics per camera
  Future<Map<String, dynamic>> getTrackerHealth() async =>
      (await _get('/ai/health/tracker')) as Map<String, dynamic>;

  /// Get multi-camera tracking fusion status
  Future<Map<String, dynamic>> getFusionStatus() async =>
      (await _get('/ai/fusion/status')) as Map<String, dynamic>;

  /// Get currently active global person tracks across all cameras
  Future<Map<String, dynamic>> getGlobalTracks({int limit = 20}) async =>
      (await _get('/ai/fusion/global-tracks', params: {'limit': '$limit'})) 
          as Map<String, dynamic>;

  /// Get camera adjacency topology for multi-camera fusion
  Future<Map<String, dynamic>> getFusionCameraTopology() async =>
      (await _get('/ai/fusion/camera-topology')) as Map<String, dynamic>;

  /// Complete AI system status dashboard
  Future<Map<String, dynamic>> getFullAiStatus() async =>
      (await _get('/ai/status/full')) as Map<String, dynamic>;

  /// Get recent security threats detected by Watchdog
  Future<Map<String, dynamic>> getSecurityThreats() async =>
      (await _get('/ai/security/threats')) as Map<String, dynamic>;

  /// Start or stop the Watchdog self-healing system
  Future<Map<String, dynamic>> toggleWatchdog(bool active) async =>
      (await post('/ai/watchdog/toggle', {'active': active})) 
          as Map<String, dynamic>;

  /// Configure camera adjacency for better fusion decisions
  Future<Map<String, dynamic>> setFusionCameraTopology(
      Map<String, List<String>> topology) async =>
      (await post('/ai/fusion/set-camera-topology', topology)) 
          as Map<String, dynamic>;

  Future<void> shutdownBackend() async {
    try {
      await http.post(Uri.parse('$_base/lmp/system/shutdown'), headers: _headers)
          .timeout(const Duration(seconds: 2));
    } catch (_) {
      // Ignore: Backend process might terminate before it succeeds to send HTTP 200 OK
    }
  }
}
