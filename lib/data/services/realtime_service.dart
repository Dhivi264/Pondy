/// Real-time streaming service using periodic polling as a WebSocket fallback.
/// When the backend exposes a WebSocket endpoint, swap _pollStream() for _wsStream().
library;

import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'api_service.dart';

// ── Event model ───────────────────────────────────────────────────────────────
enum RealtimeEventType { anomaly, fusionEvent, alSample, cameraStatus, attendance }

class RealtimeEvent {
  final RealtimeEventType type;
  final Map<String, dynamic> data;
  final DateTime receivedAt;
  RealtimeEvent({required this.type, required this.data})
      : receivedAt = DateTime.now();

  String get title => switch (type) {
    RealtimeEventType.anomaly      => '⚡ ${(data['anomaly_type'] ?? 'Anomaly').toString().replaceAll('_', ' ')}',
    RealtimeEventType.fusionEvent  => '🔗 Fusion Event',
    RealtimeEventType.alSample     => '🎓 New AL Sample',
    RealtimeEventType.cameraStatus => '📷 Camera ${data['camera_id'] ?? ''}',
    RealtimeEventType.attendance   => '✅ ${data['employee_id'] ?? 'Check-in'}',
  };

  String get subtitle => switch (type) {
    RealtimeEventType.anomaly      => (data['description'] ?? '').toString(),
    RealtimeEventType.fusionEvent  => 'Score: ${((data['fusion_score'] as num? ?? 0) * 100).toStringAsFixed(0)}%',
    RealtimeEventType.alSample     => 'Uncertainty: ${((data['uncertainty_score'] as num? ?? 0) * 100).toStringAsFixed(0)}%',
    RealtimeEventType.cameraStatus => data['status']?.toString() ?? '',
    RealtimeEventType.attendance   => data['status']?.toString() ?? '',
  };

  bool get isCritical =>
      type == RealtimeEventType.anomaly &&
      (data['severity'] == 'critical' || data['severity'] == 'high');
}

// ── Stream notifier ───────────────────────────────────────────────────────────
class RealtimeNotifier extends AsyncNotifier<List<RealtimeEvent>> {
  Timer? _timer;
  final _maxEvents = 50;

  @override
  Future<List<RealtimeEvent>> build() async {
    ref.onDispose(() => _timer?.cancel());
    _startPolling();
    return [];
  }

  void _startPolling() {
    _timer?.cancel();
    _timer = Timer.periodic(const Duration(seconds: 8), (_) => _poll());
  }

  Future<void> _poll() async {
    try {
      // Anomalies
      final anomalies = await ApiService.instance.getAnomalies();
      final fusion    = await ApiService.instance.getFusionEvents(limit: 5);
      final samples   = await ApiService.instance.getPendingAlSamples(limit: 3);

      final incoming = <RealtimeEvent>[
        ...anomalies.take(3).map((a) =>
            RealtimeEvent(type: RealtimeEventType.anomaly, data: a as Map<String, dynamic>)),
        ...fusion.take(2).map((f) =>
            RealtimeEvent(type: RealtimeEventType.fusionEvent, data: f as Map<String, dynamic>)),
        ...samples.take(1).map((s) =>
            RealtimeEvent(type: RealtimeEventType.alSample, data: s as Map<String, dynamic>)),
      ];

      state = AsyncValue.data(<RealtimeEvent>[
        ...incoming,
        ...state.valueOrNull ?? [],
      ].take(_maxEvents).toList());
    } catch (_) {
      // Keep existing state on error — don't wipe the feed
    }
  }

  void clear() => state = const AsyncValue.data([]);

  void addManual(RealtimeEvent event) {
    final current = state.valueOrNull ?? [];
    state = AsyncValue.data([event, ...current].take(_maxEvents).toList());
  }
}

// ── Providers ─────────────────────────────────────────────────────────────────
final realtimeProvider =
    AsyncNotifierProvider<RealtimeNotifier, List<RealtimeEvent>>(RealtimeNotifier.new);

final criticalAlertsCountProvider = Provider<int>((ref) {
  final events = ref.watch(realtimeProvider).valueOrNull ?? [];
  return events.where((e) => e.isCritical).length;
});
