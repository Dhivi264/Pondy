import 'package:flutter/material.dart';
import '../../data/models/models.dart';
import '../theme/app_theme.dart';
import 'ui_kit.dart';

class CameraTile extends StatelessWidget {
  final CameraModel camera;
  final VoidCallback onTap;
  const CameraTile({super.key, required this.camera, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final online = camera.status == CameraStatus.online;
    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Expanded(child: Container(
            color: Colors.black,
            child: Stack(fit: StackFit.expand, children: [
              Center(child: Icon(
                online ? Icons.videocam_rounded : Icons.videocam_off_rounded,
                color: online ? AppColors.textMuted : AppColors.error,
                size: 44,
              )),
              Positioned(top: 8, left: 8,
                  child: StatusBadge(online ? 'LIVE' : 'OFFLINE',
                      color: online ? AppColors.success : AppColors.error)),
              Positioned(top: 8, right: 8, child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(color: Colors.black54,
                    borderRadius: BorderRadius.circular(4)),
                child: Text('CH${camera.channel.toString().padLeft(2, '0')}',
                    style: const TextStyle(color: Colors.white, fontSize: 10,
                        fontWeight: FontWeight.bold)),
              )),
              if (online) Positioned(bottom: 8, right: 8, child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(color: Colors.black54,
                    borderRadius: BorderRadius.circular(4)),
                child: Text('${camera.fps} FPS',
                    style: const TextStyle(color: Colors.white, fontSize: 10)),
              )),
              if (camera.isAiActive) Positioned(bottom: 8, left: 8, child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                    color: AppColors.teal.withValues(alpha: 0.85),
                    borderRadius: BorderRadius.circular(4)),
                child: const Row(mainAxisSize: MainAxisSize.min, children: [
                  Icon(Icons.auto_awesome_rounded, color: Colors.white, size: 10),
                  SizedBox(width: 3),
                  Text('AI', style: TextStyle(color: Colors.white, fontSize: 10,
                      fontWeight: FontWeight.bold)),
                ]),
              )),
            ]),
          )),
          Container(
            padding: const EdgeInsets.all(12),
            color: AppColors.surfaceHighlight,
            child: Row(children: [
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(camera.name,
                    style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
                    maxLines: 1, overflow: TextOverflow.ellipsis),
                const SizedBox(height: 2),
                Text(camera.location,
                    style: const TextStyle(color: AppColors.textSecondary, fontSize: 12),
                    maxLines: 1, overflow: TextOverflow.ellipsis),
              ])),
              if (camera.isRecording)
                const Icon(Icons.fiber_manual_record, color: AppColors.error, size: 16),
            ]),
          ),
        ]),
      ),
    );
  }
}
