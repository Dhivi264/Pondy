/// In-app notification / toast service.
/// Shows snackbar-style alerts for anomalies, stream drops, and AL events.
/// Designed to be upgraded to push notifications (firebase_messaging) later.
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'realtime_service.dart';
import '../../core/theme/app_theme.dart';

// ── Notification model ────────────────────────────────────────────────────────
enum NotifLevel { info, success, warning, critical }

class AppNotification {
  final String id;
  final String title;
  final String message;
  final NotifLevel level;
  final DateTime createdAt;
  bool read;

  AppNotification({
    required this.id,
    required this.title,
    required this.message,
    required this.level,
    this.read = false,
  }) : createdAt = DateTime.now();

  Color get color => switch (level) {
    NotifLevel.info     => AppColors.info,
    NotifLevel.success  => AppColors.success,
    NotifLevel.warning  => AppColors.warning,
    NotifLevel.critical => AppColors.error,
  };

  IconData get icon => switch (level) {
    NotifLevel.info     => Icons.info_outline_rounded,
    NotifLevel.success  => Icons.check_circle_outline_rounded,
    NotifLevel.warning  => Icons.warning_amber_rounded,
    NotifLevel.critical => Icons.error_outline_rounded,
  };
}

// ── Notifier ──────────────────────────────────────────────────────────────────
class NotificationNotifier extends Notifier<List<AppNotification>> {
  @override
  List<AppNotification> build() => [];

  void add(AppNotification n) {
    state = [n, ...state].take(100).toList();
  }

  void addFromEvent(RealtimeEvent event) {
    add(AppNotification(
      id:      DateTime.now().millisecondsSinceEpoch.toString(),
      title:   event.title,
      message: event.subtitle,
      level:   event.isCritical ? NotifLevel.critical : NotifLevel.warning,
    ));
  }

  void markRead(String id) {
    state = state.map((n) => n.id == id ? (n..read = true) : n).toList();
  }

  void markAllRead() {
    state = state.map((n) => n..read = true).toList();
  }

  void clear() => state = [];

  int get unreadCount => state.where((n) => !n.read).length;
}

final notificationProvider =
    NotifierProvider<NotificationNotifier, List<AppNotification>>(
        NotificationNotifier.new);

final unreadCountProvider = Provider<int>((ref) {
  final notifs = ref.watch(notificationProvider);
  return notifs.where((n) => !n.read).length;
});

// ── Overlay helper ────────────────────────────────────────────────────────────
void showAppToast(
  BuildContext context, {
  required String message,
  NotifLevel level = NotifLevel.info,
  Duration duration = const Duration(seconds: 3),
}) {
  final color = switch (level) {
    NotifLevel.info     => AppColors.info,
    NotifLevel.success  => AppColors.success,
    NotifLevel.warning  => AppColors.warning,
    NotifLevel.critical => AppColors.error,
  };
  final icon = switch (level) {
    NotifLevel.info     => Icons.info_outline_rounded,
    NotifLevel.success  => Icons.check_circle_outline_rounded,
    NotifLevel.warning  => Icons.warning_amber_rounded,
    NotifLevel.critical => Icons.error_outline_rounded,
  };

  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(
      duration: duration,
      backgroundColor: AppColors.surfaceCard,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      behavior: SnackBarBehavior.floating,
      margin: const EdgeInsets.all(16),
      content: Row(children: [
        Icon(icon, color: color, size: 18),
        const SizedBox(width: 10),
        Expanded(child: Text(message,
            style: TextStyle(color: color, fontWeight: FontWeight.w600, fontSize: 13))),
      ]),
    ),
  );
}
