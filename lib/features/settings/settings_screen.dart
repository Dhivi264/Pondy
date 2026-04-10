import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/ui_kit.dart';
import '../../data/providers/app_providers.dart';
import '../../data/providers/upscaling_providers.dart';
import '../../data/services/api_service.dart';

class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});
  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  bool _motionAlerts = true;
  bool _faceAlerts   = true;
  bool _autoStart    = false;
  bool _realtimePoll = true;
  String _grid       = '3x3';

  @override
  Widget build(BuildContext context) {
    final backend  = ref.watch(backendOnlineProvider);
    final theme    = ref.watch(themeProvider);
    final notifs   = ref.watch(notificationProvider);
    final unread   = notifs.where((n) => !n.read).length;

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          // Header
          const Text('System Settings',
              style: TextStyle(color: AppColors.textPrimary,
                  fontSize: 22, fontWeight: FontWeight.w800)),
          const SizedBox(height: 6),
          const Text('Configure platform behaviour, appearance, and connections.',
              style: TextStyle(color: AppColors.textMuted, fontSize: 13)),
          const SizedBox(height: 24),

          // Two-column grid on wide screens
          LayoutBuilder(builder: (ctx, constraints) {
            final wide = constraints.maxWidth > 800;
            final cards = [
              _backendCard(backend),
              _appearanceCard(theme),
              _notificationsCard(unread),
              _realtimeCard(),
              _cameraGridCard(),
              _platformInfoCard(),
              _dangerZoneCard(),
            ];
            if (wide) {
              return Column(children: [
                for (var i = 0; i < cards.length; i += 2)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 16),
                    child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Expanded(child: cards[i]),
                      const SizedBox(width: 16),
                      Expanded(child: i + 1 < cards.length ? cards[i + 1] : const SizedBox()),
                    ]),
                  ),
              ]);
            }
            return Column(
              children: cards.expand((c) => [c, const SizedBox(height: 16)]).toList(),
            );
          }),
        ]),
      ),
    );
  }

  // ── Cards ────────────────────────────────────────────────────────────────────

  Widget _backendCard(AsyncValue<bool> backend) => _Card('Backend Connection', [
    backend.when(
      loading: () => const Row(children: [
        SizedBox(width: 14, height: 14,
            child: CircularProgressIndicator(strokeWidth: 1.5, color: AppColors.primary)),
        SizedBox(width: 8),
        Text('Checking…', style: TextStyle(color: AppColors.textMuted, fontSize: 13)),
      ]),
      error: (_, _) => Row(children: [
        const StatusBadge('OFFLINE', color: AppColors.error),
        const Spacer(),
        Text(kBackendBase,
            style: const TextStyle(color: AppColors.textMuted, fontSize: 11, fontFamily: 'monospace')),
      ]),
      data: (v) => Row(children: [
        StatusBadge(v ? 'ONLINE' : 'OFFLINE',
            color: v ? AppColors.success : AppColors.error),
        const Spacer(),
        Text(kBackendBase,
            style: const TextStyle(color: AppColors.textMuted, fontSize: 11, fontFamily: 'monospace')),
      ]),
    ),
    const SizedBox(height: 12),
    SizedBox(
      width: double.infinity,
      child: OutlinedButton.icon(
        onPressed: () {
          ref.invalidate(backendOnlineProvider);
          ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
            content: Text('Checking backend connection…'),
            duration: Duration(seconds: 2),
          ));
        },
        icon: const Icon(Icons.refresh_rounded, size: 14),
        label: const Text('Test Connection'),
      ),
    ),
  ]);

  Widget _appearanceCard(ThemeMode theme) => _Card('Appearance', [
    Row(children: [
      const Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('Dark Mode', style: TextStyle(color: AppColors.textPrimary,
            fontSize: 13, fontWeight: FontWeight.w600)),
        Text('Toggle between dark and light interface',
            style: TextStyle(color: AppColors.textMuted, fontSize: 11)),
      ])),
      Switch(
        value: theme == ThemeMode.dark,
        onChanged: (_) => ref.read(themeProvider.notifier).toggle(),
        activeThumbColor: AppColors.primary,
      ),
    ]),
  ]);

  Widget _notificationsCard(int unread) => _Card('Notifications', [
    _SwitchRow('Motion Alerts', 'Push on motion detection',
        _motionAlerts, (v) => setState(() => _motionAlerts = v)),
    const Divider(color: AppColors.border, height: 20),
    _SwitchRow('Face Detection Alerts', 'Alert on unknown face',
        _faceAlerts, (v) => setState(() => _faceAlerts = v)),
    const Divider(color: AppColors.border, height: 20),
    Row(children: [
      const Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('Notification History',
            style: TextStyle(color: AppColors.textPrimary,
                fontSize: 13, fontWeight: FontWeight.w600)),
        Text('In-app alerts log', style: TextStyle(color: AppColors.textMuted, fontSize: 11)),
      ])),
      if (unread > 0)
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
          decoration: BoxDecoration(
            color: AppColors.error.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Text('$unread unread',
              style: const TextStyle(color: AppColors.error, fontSize: 11,
                  fontWeight: FontWeight.w700)),
        ),
      const SizedBox(width: 8),
      OutlinedButton(
        onPressed: () => ref.read(notificationProvider.notifier).markAllRead(),
        style: OutlinedButton.styleFrom(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6)),
        child: const Text('Clear', style: TextStyle(fontSize: 12)),
      ),
    ]),
  ]);

  Widget _realtimeCard() => _Card('Real-time Feed', [
    _SwitchRow('Live Polling', 'Poll backend every 8 s for anomalies & events',
        _realtimePoll, (v) {
          setState(() => _realtimePoll = v);
          // Invalidate to restart/stop the timer indirectly
          if (v) ref.invalidate(realtimeProvider);
        }),
    const SizedBox(height: 12),
    SizedBox(
      width: double.infinity,
      child: OutlinedButton.icon(
        onPressed: () {
          ref.invalidate(realtimeProvider);
          ref.invalidate(lmpAnomaliesProvider);
          ref.invalidate(lmpFusionEventsProvider);
          ref.invalidate(lmpPendingSamplesProvider);
          ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
            content: Text('All AI providers refreshed'),
            backgroundColor: AppColors.success,
            duration: Duration(seconds: 2),
          ));
        },
        icon: const Icon(Icons.sync_rounded, size: 14),
        label: const Text('Refresh All AI Data'),
      ),
    ),
  ]);

  Widget _cameraGridCard() => _Card('Camera Grid Layout', [
    const Text('Default grid density',
        style: TextStyle(color: AppColors.textSecondary,
            fontSize: 13, fontWeight: FontWeight.w600)),
    const SizedBox(height: 10),
    Wrap(spacing: 8, children: ['2x2', '3x3', '4x4', '6x6'].map((g) =>
      GestureDetector(
        onTap: () => setState(() => _grid = g),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 150),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          decoration: BoxDecoration(
            color: _grid == g
                ? AppColors.primary.withValues(alpha: 0.15)
                : AppColors.surfaceHighlight,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
                color: _grid == g ? AppColors.primary : AppColors.border),
          ),
          child: Text(g,
              style: TextStyle(
                  color: _grid == g ? AppColors.primary : AppColors.textSecondary,
                  fontWeight: FontWeight.w600, fontSize: 13)),
        ),
      ),
    ).toList()),
    const SizedBox(height: 4),
    _SwitchRow('Desktop Autostart', 'Launch on system startup',
        _autoStart, (v) => setState(() => _autoStart = v)),
  ]);

  Widget _platformInfoCard() => _Card('Platform Info', const [
    InfoRow('Version', 'v2.0.0 LMP-TX'),
    Divider(color: AppColors.border, height: 20),
    InfoRow('YOLO Backend', 'PyTorch / OpenVINO / TensorRT', valueColor: AppColors.teal),
    Divider(color: AppColors.border, height: 20),
    InfoRow('modAL Version', '0.4.1'),
    Divider(color: AppColors.border, height: 20),
    InfoRow('Active Learning', 'Enabled', valueColor: AppColors.success),
    Divider(color: AppColors.border, height: 20),
    InfoRow('RTSP Reconnect', 'Exponential back-off (2→60 s)', valueColor: AppColors.info),
  ]);

  Widget _dangerZoneCard() => _Card('Danger Zone', [
    SizedBox(
      width: double.infinity,
      child: OutlinedButton.icon(
        onPressed: () => _confirm(
          title: 'Clear Archive Data',
          message: 'This permanently deletes all video archive records.',
          onConfirm: () {},
        ),
        style: OutlinedButton.styleFrom(
            foregroundColor: AppColors.error,
            side: const BorderSide(color: AppColors.error)),
        icon: const Icon(Icons.delete_forever_rounded, size: 15),
        label: const Text('Clear All Archive Data'),
      ),
    ),
    const SizedBox(height: 8),
    SizedBox(
      width: double.infinity,
      child: OutlinedButton.icon(
        onPressed: () => _confirm(
          title: 'Reset AI Models',
          message: 'This will reset all active learning sessions and model weights.',
          onConfirm: () {
            ref.invalidate(lmpPendingSamplesProvider);
            ref.invalidate(lmpProfilesProvider);
          },
        ),
        style: OutlinedButton.styleFrom(
            foregroundColor: AppColors.warning,
            side: const BorderSide(color: AppColors.warning)),
        icon: const Icon(Icons.restart_alt_rounded, size: 15),
        label: const Text('Reset AI Models'),
      ),
    ),
  ]);

  // ── Helpers ──────────────────────────────────────────────────────────────────

  Future<void> _confirm({
    required String title,
    required String message,
    required VoidCallback onConfirm,
  }) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (dialogCtx) => AlertDialog(
        backgroundColor: AppColors.surfaceCard,
        title: Text(title, style: const TextStyle(color: AppColors.textPrimary)),
        content: Text(message, style: const TextStyle(color: AppColors.textSecondary)),
        actions: [
          TextButton(onPressed: () => Navigator.pop(dialogCtx, false),
              child: const Text('Cancel')),
          ElevatedButton(
            onPressed: () => Navigator.pop(dialogCtx, true),
            style: ElevatedButton.styleFrom(backgroundColor: AppColors.error),
            child: const Text('Confirm'),
          ),
        ],
      ),
    );
    if (ok == true) onConfirm();
  }
}

// ── Reusable sub-widgets ──────────────────────────────────────────────────────

class _Card extends StatelessWidget {
  final String title;
  final List<Widget> children;
  const _Card(this.title, this.children);

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.all(18),
    decoration: BoxDecoration(
      color: AppColors.surfaceCard,
      borderRadius: BorderRadius.circular(12),
      border: Border.all(color: AppColors.border),
    ),
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(title,
          style: const TextStyle(color: AppColors.textPrimary,
              fontSize: 14, fontWeight: FontWeight.w700)),
      const SizedBox(height: 14),
      ...children,
    ]),
  );
}

class _SwitchRow extends StatelessWidget {
  final String title, subtitle;
  final bool value;
  final ValueChanged<bool> onChanged;
  const _SwitchRow(this.title, this.subtitle, this.value, this.onChanged);

  @override
  Widget build(BuildContext context) => Row(children: [
    Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(title,
          style: const TextStyle(color: AppColors.textPrimary,
              fontSize: 13, fontWeight: FontWeight.w600)),
      Text(subtitle,
          style: const TextStyle(color: AppColors.textMuted, fontSize: 11)),
    ])),
    Switch(value: value, onChanged: onChanged, activeThumbColor: AppColors.primary),
  ]);
}
