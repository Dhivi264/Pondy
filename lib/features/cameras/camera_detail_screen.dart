import 'package:flutter/material.dart';
import 'package:flutter_mjpeg/flutter_mjpeg.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/ui_kit.dart';
import '../../data/providers/app_providers.dart';
import '../../data/models/models.dart';
import '../../data/services/api_service.dart';
import 'local_camera_widget.dart';

class CameraDetailScreen extends ConsumerStatefulWidget {
  final String cameraId;
  const CameraDetailScreen({super.key, required this.cameraId});

  @override
  ConsumerState<CameraDetailScreen> createState() => _CameraDetailScreenState();
}

class _CameraDetailScreenState extends ConsumerState<CameraDetailScreen> {
  bool _isRecording = false;
  double _skipRate = 5;
  bool _probing = false;
  String? _probeMsg;

  void _showFullScreen(CameraModel c) {
    showDialog(
      context: context,
      useSafeArea: false,
      builder:
          (context) => Scaffold(
            backgroundColor: Colors.black,
            body: Stack(
              children: [
                Center(
                  child:
                      widget.cameraId == '8'
                          ? const LocalCameraWidget()
                          : c.status == CameraStatus.online &&
                              c.streamUrl != null
                          ? Mjpeg(
                            isLive: true,
                            stream: c.streamUrl!,
                            fit: BoxFit.contain,
                            width: double.infinity,
                            height: double.infinity,
                          )
                          : const Icon(
                            Icons.videocam_off_rounded,
                            color: AppColors.error,
                            size: 100,
                          ),
                ),
                Positioned(
                  top: 40,
                  right: 20,
                  child: ElevatedButton.icon(
                    icon: const Icon(Icons.close_rounded, color: Colors.white),
                    label: const Text(
                      'Cancel',
                      style: TextStyle(color: Colors.white),
                    ),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.redAccent,
                    ),
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                ),
              ],
            ),
          ),
    );
  }

  Future<void> _probeRtsp() async {
    setState(() {
      _probing = true;
      _probeMsg = null;
    });
    try {
      await ApiService.instance.setCameraSkipRate(
        widget.cameraId,
        _skipRate.round(),
      );
      setState(() => _probeMsg = 'Stream reachable — skip rate confirmed.');
    } catch (_) {
      setState(() => _probeMsg = 'Backend offline or camera not configured.');
    } finally {
      setState(() => _probing = false);
    }
  }

  Future<void> _applySkipRate(double v) async {
    try {
      await ApiService.instance.setCameraSkipRate(widget.cameraId, v.round());
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Skip rate set to ${v.round()} for ${widget.cameraId}',
            ),
            backgroundColor: AppColors.success,
            duration: const Duration(seconds: 2),
          ),
        );
      }
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    final cameras = ref.watch(camerasProvider);
    final anomalies = ref.watch(lmpAnomaliesProvider);

    final cam = cameras.whenData(
      (list) => list.firstWhere(
        (c) => c.id == widget.cameraId,
        orElse:
            () => CameraModel(
              id: widget.cameraId,
              name: 'Camera ${widget.cameraId}',
              channel: 1,
              status: CameraStatus.offline,
              fps: 0,
              isAiActive: false,
              location: '—',
              isRecording: false,
            ),
      ),
    );

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.surface,
        leading: IconButton(
          icon: const Icon(
            Icons.arrow_back_rounded,
            color: AppColors.textPrimary,
          ),
          onPressed: () => context.go('/dashboard'),
        ),
        title: Text(
          'Camera · ${widget.cameraId}',
          style: const TextStyle(
            color: AppColors.textPrimary,
            fontWeight: FontWeight.w700,
          ),
        ),
        actions: [
          cam.when(
            loading: () => const SizedBox.shrink(),
            error: (_, _) => const SizedBox.shrink(),
            data:
                (c) => Padding(
                  padding: const EdgeInsets.symmetric(
                    vertical: 14,
                    horizontal: 12,
                  ),
                  child: StatusBadge(
                    c.status == CameraStatus.online ? 'LIVE' : 'OFFLINE',
                    color:
                        c.status == CameraStatus.online
                            ? AppColors.success
                            : AppColors.error,
                  ),
                ),
          ),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Container(height: 1, color: AppColors.border),
        ),
      ),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              flex: 3,
              child: SingleChildScrollView(
                child: Column(
                  children: [
                    Container(
                      height: 340,
                      decoration: BoxDecoration(
                        color: Colors.black,
                        borderRadius: BorderRadius.circular(14),
                        border: Border.all(color: AppColors.border),
                      ),
                      child: Stack(
                        children: [
                          Center(
                            child: cam.when(
                              loading: () => const ScreenLoader(),
                              error:
                                  (_, _) => const EmptyState(
                                    icon: Icons.videocam_off_rounded,
                                    title: 'Camera unavailable',
                                  ),
                              data:
                                  (c) =>
                                      widget.cameraId == '8'
                                          ? const LocalCameraWidget()
                                          : c.status == CameraStatus.online &&
                                              c.streamUrl != null
                                          ? Mjpeg(
                                            isLive: true,
                                            stream: c.streamUrl!,
                                            fit: BoxFit.contain,
                                            width: double.infinity,
                                            height: double.infinity,
                                            error:
                                                (_, __, ___) => Column(
                                                  mainAxisAlignment:
                                                      MainAxisAlignment.center,
                                                  children: [
                                                    const Icon(
                                                      Icons
                                                          .videocam_off_rounded,
                                                      color: AppColors.error,
                                                      size: 52,
                                                    ),
                                                    const SizedBox(height: 8),
                                                    const Text(
                                                      'FEED ERROR',
                                                      style: TextStyle(
                                                        color: AppColors.error,
                                                        fontWeight:
                                                            FontWeight.w700,
                                                        letterSpacing: 2,
                                                        fontSize: 12,
                                                      ),
                                                    ),
                                                    const SizedBox(height: 4),
                                                    Text(
                                                      'Could not connect to ${c.streamUrl}',
                                                      style: const TextStyle(
                                                        color:
                                                            AppColors.textMuted,
                                                        fontSize: 10,
                                                      ),
                                                    ),
                                                  ],
                                                ),
                                          )
                                          : c.status == CameraStatus.online
                                          ? Column(
                                            mainAxisAlignment:
                                                MainAxisAlignment.center,
                                            children: [
                                              Icon(
                                                Icons.videocam_rounded,
                                                color: AppColors.primary
                                                    .withValues(alpha: 0.18),
                                                size: 60,
                                              ),
                                              const SizedBox(height: 10),
                                              const Text(
                                                'LIVE',
                                                style: TextStyle(
                                                  color: AppColors.primary,
                                                  fontWeight: FontWeight.w900,
                                                  letterSpacing: 4,
                                                  fontSize: 13,
                                                ),
                                              ),
                                              const SizedBox(height: 4),
                                              Text(
                                                '${c.fps} fps · ${c.location}',
                                                style: const TextStyle(
                                                  color: AppColors.textMuted,
                                                  fontSize: 11,
                                                ),
                                              ),
                                            ],
                                          )
                                          : const Column(
                                            mainAxisAlignment:
                                                MainAxisAlignment.center,
                                            children: [
                                              Icon(
                                                Icons.videocam_off_rounded,
                                                color: AppColors.error,
                                                size: 52,
                                              ),
                                              SizedBox(height: 8),
                                              Text(
                                                'STREAM OFFLINE',
                                                style: TextStyle(
                                                  color: AppColors.error,
                                                  fontWeight: FontWeight.w700,
                                                  letterSpacing: 2,
                                                  fontSize: 12,
                                                ),
                                              ),
                                            ],
                                          ),
                            ),
                          ),
                          cam.when(
                            loading: () => const SizedBox.shrink(),
                            error: (_, _) => const SizedBox.shrink(),
                            data:
                                (c) =>
                                    c.isAiActive
                                        ? Positioned(
                                          top: 10,
                                          left: 10,
                                          child: Container(
                                            padding: const EdgeInsets.symmetric(
                                              horizontal: 7,
                                              vertical: 3,
                                            ),
                                            decoration: BoxDecoration(
                                              color: AppColors.teal.withValues(
                                                alpha: 0.2,
                                              ),
                                              borderRadius:
                                                  BorderRadius.circular(5),
                                              border: Border.all(
                                                color: AppColors.teal
                                                    .withValues(alpha: 0.5),
                                              ),
                                            ),
                                            child: const Row(
                                              mainAxisSize: MainAxisSize.min,
                                              children: [
                                                Icon(
                                                  Icons.auto_awesome_rounded,
                                                  color: AppColors.teal,
                                                  size: 11,
                                                ),
                                                SizedBox(width: 4),
                                                Text(
                                                  'AI ACTIVE',
                                                  style: TextStyle(
                                                    color: AppColors.teal,
                                                    fontSize: 10,
                                                    fontWeight: FontWeight.w800,
                                                  ),
                                                ),
                                              ],
                                            ),
                                          ),
                                        )
                                        : const SizedBox.shrink(),
                          ),
                          Positioned(
                            top: 10,
                            right: 10,
                            child: Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 8,
                                vertical: 3,
                              ),
                              decoration: BoxDecoration(
                                color: Colors.black54,
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: Text(
                                DateFormat('HH:mm:ss').format(DateTime.now()),
                                style: const TextStyle(
                                  color: Colors.white70,
                                  fontSize: 10,
                                  fontFamily: 'monospace',
                                ),
                              ),
                            ),
                          ),
                          _isRecording
                              ? Positioned(
                                bottom: 10,
                                left: 10,
                                child: Row(
                                  children: [
                                    Container(
                                      width: 8,
                                      height: 8,
                                      decoration: const BoxDecoration(
                                        color: AppColors.error,
                                        shape: BoxShape.circle,
                                      ),
                                    ),
                                    const SizedBox(width: 5),
                                    const Text(
                                      'REC',
                                      style: TextStyle(
                                        color: AppColors.error,
                                        fontWeight: FontWeight.w900,
                                        fontSize: 11,
                                        letterSpacing: 1.5,
                                      ),
                                    ),
                                  ],
                                ),
                              )
                              : const SizedBox.shrink(),
                          Positioned(
                            bottom: 15,
                            right: 15,
                            child: Container(
                              decoration: BoxDecoration(
                                color: Colors.black54,
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: cam.when(
                                loading:
                                    () => IconButton(
                                      icon: const Icon(
                                        Icons.fullscreen_rounded,
                                        color: Colors.white,
                                        size: 28,
                                      ),
                                      onPressed: () {},
                                      tooltip: 'Full Screen',
                                    ),
                                error:
                                    (_, __) => IconButton(
                                      icon: const Icon(
                                        Icons.fullscreen_rounded,
                                        color: Colors.white,
                                        size: 28,
                                      ),
                                      onPressed: () {},
                                      tooltip: 'Full Screen',
                                    ),
                                data:
                                    (c) => IconButton(
                                      icon: const Icon(
                                        Icons.fullscreen_rounded,
                                        color: Colors.white,
                                        size: 28,
                                      ),
                                      onPressed: () => _showFullScreen(c),
                                      tooltip: 'Full Screen',
                                    ),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 14),
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: AppColors.surfaceCard,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: AppColors.border),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Wrap(
                            spacing: 14,
                            runSpacing: 14,
                            children: [
                              _CtrlBtn(
                                icon: Icons.camera_alt_rounded,
                                label: 'Snapshot',
                                color: AppColors.primary,
                                onTap: () {},
                              ),
                              _CtrlBtn(
                                icon:
                                    _isRecording
                                        ? Icons.stop_rounded
                                        : Icons.fiber_manual_record_rounded,
                                label: _isRecording ? 'Stop Rec' : 'Record',
                                color: AppColors.error,
                                onTap:
                                    () => setState(
                                      () => _isRecording = !_isRecording,
                                    ),
                              ),
                              _CtrlBtn(
                                icon:
                                    _probing
                                        ? Icons.hourglass_top_rounded
                                        : Icons.wifi_tethering_rounded,
                                label: _probing ? 'Probing…' : 'Probe RTSP',
                                color: AppColors.teal,
                                onTap: _probing ? () {} : _probeRtsp,
                              ),
                              _CtrlBtn(
                                icon: Icons.stop_screen_share_rounded,
                                label: 'Stop AI',
                                color: AppColors.error,
                                onTap: () async {
                                  try {
                                    await ApiService.instance.stopCameraAi(
                                      widget.cameraId,
                                    );
                                    if (!mounted) return;
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      const SnackBar(
                                        content: Text(
                                          'AI processing stopped for this camera',
                                        ),
                                        backgroundColor: AppColors.success,
                                        duration: Duration(seconds: 2),
                                      ),
                                    );
                                  } catch (e) {
                                    if (!mounted) return;
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      SnackBar(
                                        content: Text('Failed to stop AI: $e'),
                                        backgroundColor: AppColors.error,
                                        duration: const Duration(seconds: 2),
                                      ),
                                    );
                                  }
                                },
                              ),
                            ],
                          ),
                          if (_probeMsg != null) ...[
                            const SizedBox(height: 10),
                            Row(
                              children: [
                                Icon(
                                  _probeMsg!.contains('reachable')
                                      ? Icons.check_circle_outline_rounded
                                      : Icons.info_outline_rounded,
                                  color:
                                      _probeMsg!.contains('reachable')
                                          ? AppColors.success
                                          : AppColors.warning,
                                  size: 14,
                                ),
                                const SizedBox(width: 6),
                                Expanded(
                                  child: Text(
                                    _probeMsg!,
                                    style: TextStyle(
                                      color:
                                          _probeMsg!.contains('reachable')
                                              ? AppColors.success
                                              : AppColors.warning,
                                      fontSize: 12,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ],
                      ),
                    ),
                    const SizedBox(height: 14),
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: AppColors.surfaceCard,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: AppColors.border),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              const Icon(
                                Icons.speed_rounded,
                                color: AppColors.warning,
                                size: 15,
                              ),
                              const SizedBox(width: 6),
                              const Text(
                                'Frame Skip Rate',
                                style: TextStyle(
                                  color: AppColors.textPrimary,
                                  fontSize: 13,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                              const Spacer(),
                              Container(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 10,
                                  vertical: 3,
                                ),
                                decoration: BoxDecoration(
                                  color: AppColors.warning.withValues(
                                    alpha: 0.1,
                                  ),
                                  borderRadius: BorderRadius.circular(6),
                                ),
                                child: Text(
                                  'every ${_skipRate.round()} frame${_skipRate.round() > 1 ? "s" : ""}',
                                  style: const TextStyle(
                                    color: AppColors.warning,
                                    fontSize: 12,
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 4),
                          Slider(
                            value: _skipRate,
                            min: 1,
                            max: 10,
                            divisions: 9,
                            activeColor: AppColors.warning,
                            inactiveColor: AppColors.border,
                            onChanged: (v) => setState(() => _skipRate = v),
                            onChangeEnd: _applySkipRate,
                          ),
                          const Text(
                            '1 = every frame (Server GPU)   5 = Raspberry Pi / Intel NCS',
                            style: TextStyle(
                              color: AppColors.textMuted,
                              fontSize: 11,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(width: 20),
            SizedBox(
              width: 290,
              child: Column(
                children: [
                  cam.when(
                    loading:
                        () => const Padding(
                          padding: EdgeInsets.all(20),
                          child: ScreenLoader(),
                        ),
                    error: (_, _) => const SizedBox.shrink(),
                    data:
                        (c) => _InfoCard(
                          title: 'Stream Info',
                          children: [
                            InfoRow('Camera ID', c.id),
                            const Divider(color: AppColors.border, height: 12),
                            InfoRow('Location', c.location),
                            const Divider(color: AppColors.border, height: 12),
                            InfoRow('Channel', '#${c.channel}'),
                            const Divider(color: AppColors.border, height: 12),
                            InfoRow('Frame Rate', '${c.fps} fps'),
                            const Divider(color: AppColors.border, height: 12),
                            InfoRow(
                              'AI Active',
                              c.isAiActive ? 'Yes' : 'No',
                              valueColor:
                                  c.isAiActive
                                      ? AppColors.teal
                                      : AppColors.textMuted,
                            ),
                            const Divider(color: AppColors.border, height: 12),
                            InfoRow(
                              'Recording',
                              c.isRecording ? 'Active' : 'Idle',
                              valueColor:
                                  c.isRecording
                                      ? AppColors.error
                                      : AppColors.textMuted,
                            ),
                            const Divider(color: AppColors.border, height: 12),
                            const InfoRow('Storage', 'data/recordings'),
                          ],
                        ),
                  ),
                  const SizedBox(height: 14),
                  _InfoCard(
                    title: 'Archive Storage',
                    children: [
                      Row(
                        children: [
                          const Icon(
                            Icons.folder_rounded,
                            color: AppColors.primary,
                            size: 18,
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              'smart_cctv_app/backend/data/recordings',
                              style: const TextStyle(
                                color: AppColors.textPrimary,
                                fontSize: 11,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          const Icon(
                            Icons.folder_rounded,
                            color: AppColors.teal,
                            size: 18,
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              'smart_cctv_app/backend/data/captured_faces',
                              style: const TextStyle(
                                color: AppColors.textPrimary,
                                fontSize: 11,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                  const SizedBox(height: 14),
                  _InfoCard(
                    title: 'Recent Detections',
                    trailing: TextButton(
                      onPressed: () => context.go('/lmptx'),
                      child: const Text(
                        'View all',
                        style: TextStyle(fontSize: 11),
                      ),
                    ),
                    children: [
                      anomalies.when(
                        loading:
                            () => const SizedBox(
                              height: 60,
                              child: ScreenLoader(),
                            ),
                        error:
                            (_, _) => const Text(
                              'Unavailable',
                              style: TextStyle(
                                color: AppColors.textMuted,
                                fontSize: 12,
                              ),
                            ),
                        data: (list) {
                          if (list.isEmpty) {
                            return const Padding(
                              padding: EdgeInsets.symmetric(vertical: 12),
                              child: EmptyState(
                                icon: Icons.check_circle_outline,
                                title: 'No events',
                              ),
                            );
                          }
                          return Column(
                            children:
                                list.take(5).map<Widget>((a) {
                                  final sev = a['severity'] as String? ?? 'low';
                                  final col =
                                      sev == 'critical' || sev == 'high'
                                          ? AppColors.error
                                          : AppColors.warning;
                                  return Padding(
                                    padding: const EdgeInsets.symmetric(
                                      vertical: 6,
                                    ),
                                    child: Row(
                                      children: [
                                        Container(
                                          width: 3,
                                          height: 30,
                                          decoration: BoxDecoration(
                                            color: col,
                                            borderRadius: BorderRadius.circular(
                                              2,
                                            ),
                                          ),
                                        ),
                                        const SizedBox(width: 8),
                                        Expanded(
                                          child: Column(
                                            crossAxisAlignment:
                                                CrossAxisAlignment.start,
                                            children: [
                                              Text(
                                                (a['anomaly_type'] as String? ??
                                                        '')
                                                    .replaceAll('_', ' '),
                                                style: const TextStyle(
                                                  color: AppColors.textPrimary,
                                                  fontSize: 11,
                                                  fontWeight: FontWeight.w600,
                                                ),
                                              ),
                                              StatusBadge(
                                                sev.toUpperCase(),
                                                color: col,
                                              ),
                                            ],
                                          ),
                                        ),
                                      ],
                                    ),
                                  );
                                }).toList(),
                          );
                        },
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _CtrlBtn extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;
  const _CtrlBtn({
    required this.icon,
    required this.label,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) => GestureDetector(
    onTap: onTap,
    child: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: color.withValues(alpha: 0.3)),
          ),
          child: Icon(icon, color: color, size: 18),
        ),
        const SizedBox(height: 4),
        Text(
          label,
          style: TextStyle(
            color: color,
            fontSize: 10,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    ),
  );
}

class _InfoCard extends StatelessWidget {
  final String title;
  final List<Widget> children;
  final Widget? trailing;
  const _InfoCard({required this.title, required this.children, this.trailing});

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.all(16),
    decoration: BoxDecoration(
      color: AppColors.surfaceCard,
      borderRadius: BorderRadius.circular(12),
      border: Border.all(color: AppColors.border),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Text(
              title,
              style: const TextStyle(
                color: AppColors.textPrimary,
                fontSize: 13,
                fontWeight: FontWeight.w700,
              ),
            ),
            if (trailing != null) ...[const Spacer(), trailing!],
          ],
        ),
        const SizedBox(height: 12),
        ...children,
      ],
    ),
  );
}
