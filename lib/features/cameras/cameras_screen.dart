import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_mjpeg/flutter_mjpeg.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/ui_kit.dart';
import '../../data/providers/app_providers.dart';
import '../../data/models/models.dart';
import '../../data/services/api_service.dart';
import 'local_camera_widget.dart';

class CamerasScreen extends ConsumerWidget {
  const CamerasScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final camerasAsync = ref.watch(camerasProvider);
    final isDesktop = MediaQuery.of(context).size.width > 800;

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text(
          'Live Cameras',
          style: TextStyle(
            color: AppColors.textPrimary,
            fontWeight: FontWeight.w800,
          ),
        ),
        backgroundColor: AppColors.surface,
        elevation: 0,
        actions: [
          IconButton(
            tooltip: 'Refresh',
            icon: const Icon(
              Icons.refresh_rounded,
              color: AppColors.textSecondary,
            ),
            onPressed: () => ref.invalidate(camerasProvider),
          ),
          const SizedBox(width: 8),
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 8.0, horizontal: 8.0),
            child: ElevatedButton.icon(
              onPressed: () => _showAddCameraDialog(context, ref),
              icon: const Icon(Icons.add_rounded, size: 18),
              label: const Text('Add Camera'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.primary,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 16),
              ),
            ),
          ),
          const SizedBox(width: 16),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async => ref.invalidate(camerasProvider),
        color: AppColors.primary,
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: EdgeInsets.all(isDesktop ? 28 : 16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              camerasAsync.when(
                loading: () => const Center(child: CircularProgressIndicator()),
                error:
                    (e, _) => EmptyState(
                      icon: Icons.videocam_off_rounded,
                      title: 'No cameras loaded',
                      subtitle: e.toString(),
                    ),
                data: (cams) {
                  if (cams.isEmpty)
                    return const EmptyState(
                      icon: Icons.videocam_off_rounded,
                      title: 'No cameras found',
                    );
                  final cols = isDesktop ? 4 : 2;
                  return GridView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: cols,
                      childAspectRatio: 16 / 10,
                      mainAxisSpacing: 16,
                      crossAxisSpacing: 16,
                    ),
                    itemCount: cams.length,
                    itemBuilder: (_, i) {
                      final cam = cams[i];
                      final isOnline = cam.status == CameraStatus.online;
                      final isWebcam = cam.id.trim() == '8';
                      return _CameraCard(
                        cam: cam,
                        isOnline: isOnline,
                        isWebcam: isWebcam,
                      );
                    },
                  );
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _showAddCameraDialog(BuildContext context, WidgetRef ref) {
    final nameCtrl = TextEditingController();
    final urlCtrl = TextEditingController();
    final locCtrl = TextEditingController();

    showDialog(
      context: context,
      builder:
          (ctx) => StatefulBuilder(
            builder:
                (ctx, setState) => AlertDialog(
                  backgroundColor: AppColors.surface,
                  title: const Text(
                    'Register New Camera',
                    style: TextStyle(color: AppColors.textPrimary),
                  ),
                  content: SingleChildScrollView(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Text(
                          'Enter camera details and stream URL (RTSP or local index).',
                          style: TextStyle(
                            color: AppColors.textMuted,
                            fontSize: 12,
                          ),
                        ),
                        const SizedBox(height: 20),
                        TextField(
                          controller: nameCtrl,
                          style: const TextStyle(color: AppColors.textPrimary),
                          decoration: const InputDecoration(
                            labelText: 'Camera Name',
                            hintText: 'Main Gate',
                          ),
                        ),
                        const SizedBox(height: 16),
                        TextField(
                          controller: urlCtrl,
                          style: const TextStyle(color: AppColors.textPrimary),
                          decoration: const InputDecoration(
                            labelText: 'Stream URL / index',
                            hintText: 'rtsp://... or 0',
                          ),
                        ),
                        const SizedBox(height: 16),
                        TextField(
                          controller: locCtrl,
                          style: const TextStyle(color: AppColors.textPrimary),
                          decoration: const InputDecoration(
                            labelText: 'Location',
                            hintText: 'Front door',
                          ),
                        ),
                      ],
                    ),
                  ),
                  actions: [
                    TextButton(
                      onPressed: () => Navigator.pop(ctx),
                      child: const Text('Cancel'),
                    ),
                    ElevatedButton(
                      onPressed: () async {
                        try {
                          final name = nameCtrl.text.trim();
                          final url = urlCtrl.text.trim();
                          final loc = locCtrl.text.trim();
                          if (name.isEmpty || url.isEmpty) return;
                          try {
                            await ApiService.instance.post('/cameras', {
                              'name': name,
                              'stream_url': url,
                              'location': loc.isEmpty ? 'Default' : loc,
                            });
                          } catch (_) {}
                          if (ctx.mounted) Navigator.pop(ctx);
                          ref.invalidate(camerasProvider);
                        } catch (e) {
                          debugPrint('Registration Error: $e');
                          if (ctx.mounted) {
                            ScaffoldMessenger.of(ctx).showSnackBar(
                              SnackBar(
                                content: Text('Failed to register: $e'),
                                backgroundColor: AppColors.error,
                              ),
                            );
                          }
                        }
                      },
                      child: const Text('Register'),
                    ),
                  ],
                ),
          ),
    );
  }
}

class _CameraCard extends StatelessWidget {
  final CameraModel cam;
  final bool isOnline;
  final bool isWebcam;

  const _CameraCard({
    required this.cam,
    required this.isOnline,
    required this.isWebcam,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(12),
      onTap: () => context.go('/cameras/${cam.id}'),
      child: Container(
        decoration: BoxDecoration(
          color: AppColors.surfaceCard,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color:
                isOnline
                    ? AppColors.border
                    : AppColors.error.withValues(alpha: 0.4),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Expanded(
              child: Stack(
                children: [
                  ClipRRect(
                    borderRadius: const BorderRadius.vertical(
                      top: Radius.circular(12),
                    ),
                    child:
                        isWebcam
                            ? const LocalCameraWidget()
                            : Center(
                              child:
                                  isOnline && cam.streamUrl != null
                                      ? Mjpeg(
                                        isLive: true,
                                        stream: cam.streamUrl!,
                                        fit: BoxFit.cover,
                                        width: double.infinity,
                                        height: double.infinity,
                                        error:
                                            (_, __, ___) => const Icon(
                                              Icons.videocam_off_rounded,
                                              color: AppColors.error,
                                              size: 32,
                                            ),
                                      )
                                      : isOnline
                                      ? const Center(
                                        child: Column(
                                          mainAxisAlignment:
                                              MainAxisAlignment.center,
                                          children: [
                                            Icon(
                                              Icons.videocam_rounded,
                                              color: AppColors.primary,
                                            ),
                                            SizedBox(height: 8),
                                            Text(
                                              'LIVE',
                                              style: TextStyle(
                                                color: AppColors.primary,
                                                fontSize: 10,
                                                fontWeight: FontWeight.w800,
                                                letterSpacing: 2,
                                              ),
                                            ),
                                          ],
                                        ),
                                      )
                                      : const Center(
                                        child: Column(
                                          mainAxisAlignment:
                                              MainAxisAlignment.center,
                                          children: [
                                            Icon(
                                              Icons.videocam_off_rounded,
                                              color: AppColors.error,
                                              size: 32,
                                            ),
                                            SizedBox(height: 8),
                                            Text(
                                              'OFFLINE',
                                              style: TextStyle(
                                                color: AppColors.error,
                                                fontSize: 10,
                                                fontWeight: FontWeight.w700,
                                                letterSpacing: 1,
                                              ),
                                            ),
                                          ],
                                        ),
                                      ),
                            ),
                  ),
                  Positioned(
                    top: 10,
                    right: 10,
                    child: StatusBadge(
                      isWebcam ? 'WEBCAM' : (isOnline ? 'LIVE' : 'OFFLINE'),
                      color:
                          isWebcam
                              ? AppColors.primary
                              : (isOnline
                                  ? AppColors.success
                                  : AppColors.error),
                    ),
                  ),
                  Positioned(
                    bottom: 10,
                    left: 10,
                    child: Text(
                      cam.location,
                      style: const TextStyle(
                        color: Colors.white70,
                        fontSize: 10,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            Container(
              padding: const EdgeInsets.all(12),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      cam.name,
                      style: const TextStyle(
                        color: AppColors.textPrimary,
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  Text(
                    isWebcam ? 'webcam' : '${cam.fps} fps',
                    style: const TextStyle(
                      color: AppColors.textMuted,
                      fontSize: 10,
                    ),
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
