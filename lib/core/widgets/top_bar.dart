import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../theme/app_theme.dart';
import '../responsive/responsive_layout.dart';
import '../../data/providers/app_providers.dart';
import '../../data/providers/upscaling_providers.dart';

class TopBar extends ConsumerWidget implements PreferredSizeWidget {
  const TopBar({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final backendStatus = ref.watch(backendOnlineProvider);
    final themeMode    = ref.watch(themeProvider);
    final unread       = ref.watch(unreadCountProvider);
    final criticalCount = ref.watch(criticalAlertsCountProvider);
    final isMobile     = ResponsiveLayout.isMobile(context);
    final isDark       = themeMode == ThemeMode.dark;

    final barColor  = isDark ? AppColors.surface     : LightColors.surface;
    final borderCol = isDark ? AppColors.border      : LightColors.border;
    final textCol   = isDark ? AppColors.textPrimary : LightColors.textPrimary;
    final mutedCol  = isDark ? AppColors.textSecondary : LightColors.textSecondary;

    return Container(
      height: 64,
      decoration: BoxDecoration(
        color: barColor,
        border: Border(bottom: BorderSide(color: borderCol)),
        boxShadow: isDark
            ? const [BoxShadow(color: Color(0x20000000), blurRadius: 8)]
            : const [BoxShadow(color: Color(0x08000000), blurRadius: 6)],
      ),
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Row(children: [
        // Mobile: hamburger + logo
        if (isMobile) ...[
          IconButton(
            icon: Icon(Icons.menu_rounded, color: textCol),
            onPressed: () => Scaffold.of(context).openDrawer(),
          ),
          const SizedBox(width: 4),
          Icon(Icons.security_rounded,
              color: isDark ? AppColors.primary : LightColors.primary, size: 22),
          const SizedBox(width: 8),
          Text('SecureVision',
              style: TextStyle(
                  fontWeight: FontWeight.w800, fontSize: 15, color: textCol)),
        ] else ...[
          // Desktop: backend status pill
          backendStatus.when(
            loading: () => _pill(null, isDark),
            error:   (_, _) => _pill(false, isDark),
            data:    (v) => _pill(v, isDark),
          ),
          // Critical alert badge
          if (criticalCount > 0) ...[
            const SizedBox(width: 10),
            GestureDetector(
              onTap: () => context.go('/lmptx'),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                decoration: BoxDecoration(
                  color: isDark ? AppColors.errorBg : LightColors.errorBg,
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(
                      color: (isDark ? AppColors.error : LightColors.error)
                          .withValues(alpha: 0.4)),
                ),
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  Icon(Icons.warning_rounded,
                      color: isDark ? AppColors.error : LightColors.error,
                      size: 13),
                  const SizedBox(width: 5),
                  Text('$criticalCount critical',
                      style: TextStyle(
                          color: isDark ? AppColors.error : LightColors.error,
                          fontSize: 12,
                          fontWeight: FontWeight.w700)),
                ]),
              ),
            ),
          ],
        ],
        const Spacer(),

        // ── Theme toggle ─────────────────────────────────────────────────────
        _ThemeToggle(isDark: isDark, mutedCol: mutedCol, onToggle: () =>
            ref.read(themeProvider.notifier).toggle()),

        const SizedBox(width: 4),

        // ── Notification bell ─────────────────────────────────────────────────
        Stack(children: [
          IconButton(
            icon: Icon(Icons.notifications_outlined, color: mutedCol, size: 22),
            onPressed: () => _showNotifications(context, ref),
            tooltip: 'Notifications',
          ),
          if (unread > 0)
            Positioned(
              top: 8, right: 8,
              child: Container(
                width: 8, height: 8,
                decoration: BoxDecoration(
                    color: isDark ? AppColors.error : LightColors.error,
                    shape: BoxShape.circle),
              ),
            ),
        ]),

        const SizedBox(width: 4),

        // ── User avatar ───────────────────────────────────────────────────────
        GestureDetector(
          onTap: () => context.go('/profile'),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: isDark ? AppColors.surfaceElevated : LightColors.surfaceHighlight,
              borderRadius: BorderRadius.circular(22),
              border: Border.all(color: borderCol),
            ),
            child: Row(children: [
              Container(
                width: 28, height: 28,
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: isDark
                        ? [AppColors.primary, AppColors.teal]
                        : [LightColors.primary, LightColors.teal],
                  ),
                  shape: BoxShape.circle,
                ),
                child: const Icon(Icons.person_rounded, size: 16, color: Colors.white),
              ),
              if (!isMobile) ...[
                const SizedBox(width: 8),
                Text('Operator',
                    style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: textCol)),
              ],
            ]),
          ),
        ),
      ]),
    );
  }

  Widget _pill(bool? online, bool isDark) {
    if (online == null) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        decoration: BoxDecoration(
          color: isDark ? AppColors.surfaceElevated : LightColors.surfaceHighlight,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: isDark ? AppColors.border : LightColors.border),
        ),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          SizedBox(
            width: 10, height: 10,
            child: CircularProgressIndicator(
                strokeWidth: 1.5,
                color: isDark ? AppColors.textMuted : LightColors.textMuted),
          ),
          const SizedBox(width: 6),
          Text('Connecting…',
              style: TextStyle(
                  fontSize: 12,
                  color: isDark ? AppColors.textMuted : LightColors.textMuted)),
        ]),
      );
    }
    final col    = online
        ? (isDark ? AppColors.success   : LightColors.success)
        : (isDark ? AppColors.error     : LightColors.error);
    final bgCol  = online
        ? (isDark ? AppColors.successBg : LightColors.successBg)
        : (isDark ? AppColors.errorBg   : LightColors.errorBg);
    final label  = online ? 'Backend Online' : 'Backend Offline';
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: bgCol,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: col.withValues(alpha: 0.3)),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Container(
          width: 6, height: 6,
          decoration: BoxDecoration(color: col, shape: BoxShape.circle),
        ),
        const SizedBox(width: 6),
        Text(label,
            style: TextStyle(
                fontSize: 12, color: col, fontWeight: FontWeight.w600)),
      ]),
    );
  }

  void _showNotifications(BuildContext context, WidgetRef ref) {
    final notifs = ref.read(notificationProvider);
    ref.read(notificationProvider.notifier).markAllRead();
    final isDark = ref.read(themeProvider) == ThemeMode.dark;

    showModalBottomSheet(
      context: context,
      backgroundColor: isDark ? AppColors.surfaceCard : LightColors.surface,
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (_) => _NotificationsSheet(notifications: notifs, isDark: isDark),
    );
  }

  @override
  Size get preferredSize => const Size.fromHeight(64);
}

// ── Animated theme toggle ─────────────────────────────────────────────────────
class _ThemeToggle extends StatelessWidget {
  final bool isDark;
  final Color mutedCol;
  final VoidCallback onToggle;
  const _ThemeToggle(
      {required this.isDark, required this.mutedCol, required this.onToggle});

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: isDark ? 'Switch to light mode' : 'Switch to dark mode',
      child: GestureDetector(
        onTap: onToggle,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeInOut,
          width: 52,
          height: 28,
          padding: const EdgeInsets.all(3),
          decoration: BoxDecoration(
            color: isDark
                ? AppColors.surfaceHighlight
                : LightColors.surfaceHighlight,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
              color: isDark ? AppColors.border : LightColors.border,
              width: 1,
            ),
          ),
          child: Stack(children: [
            AnimatedAlign(
              duration: const Duration(milliseconds: 280),
              curve: Curves.easeInOutCubic,
              alignment: isDark ? Alignment.centerRight : Alignment.centerLeft,
              child: Container(
                width: 22, height: 22,
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: isDark
                        ? [AppColors.primary, AppColors.purple]
                        : [LightColors.warning, const Color(0xFFF59E0B)],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(11),
                  boxShadow: [
                    BoxShadow(
                      color: (isDark ? AppColors.primary : LightColors.warning)
                          .withValues(alpha: 0.4),
                      blurRadius: 6,
                    ),
                  ],
                ),
                child: Icon(
                  isDark ? Icons.dark_mode_rounded : Icons.light_mode_rounded,
                  color: Colors.white,
                  size: 13,
                ),
              ),
            ),
          ]),
        ),
      ),
    );
  }
}

// ── Notifications sheet ───────────────────────────────────────────────────────
class _NotificationsSheet extends StatelessWidget {
  final List<dynamic> notifications;
  final bool isDark;
  const _NotificationsSheet(
      {required this.notifications, required this.isDark});

  @override
  Widget build(BuildContext context) {
    final textColor  = isDark ? AppColors.textPrimary  : LightColors.textPrimary;
    final mutedColor = isDark ? AppColors.textMuted    : LightColors.textMuted;
    final borderCol  = isDark ? AppColors.border       : LightColors.border;

    return Column(mainAxisSize: MainAxisSize.min, children: [
      // Handle
      Padding(
        padding: const EdgeInsets.only(top: 10, bottom: 4),
        child: Container(
          width: 36, height: 4,
          decoration: BoxDecoration(
              color: isDark ? AppColors.border : LightColors.border,
              borderRadius: BorderRadius.circular(2)),
        ),
      ),
      Container(
        padding: const EdgeInsets.fromLTRB(20, 12, 12, 12),
        decoration: BoxDecoration(
            border: Border(bottom: BorderSide(color: borderCol))),
        child: Row(children: [
          Text('Notifications',
              style: TextStyle(
                  color: textColor, fontSize: 16, fontWeight: FontWeight.w700)),
          const Spacer(),
          IconButton(
            icon: Icon(Icons.close_rounded, color: mutedColor, size: 20),
            onPressed: () => Navigator.pop(context),
          ),
        ]),
      ),
      if (notifications.isEmpty)
        Padding(
          padding: const EdgeInsets.all(40),
          child: Column(children: [
            Icon(Icons.notifications_none_rounded, size: 48, color: mutedColor),
            const SizedBox(height: 12),
            Text('All caught up!',
                style: TextStyle(
                    color: mutedColor, fontSize: 14, fontWeight: FontWeight.w600)),
            const SizedBox(height: 4),
            Text('No new notifications',
                style: TextStyle(color: mutedColor, fontSize: 12)),
          ]),
        )
      else
        ConstrainedBox(
          constraints: const BoxConstraints(maxHeight: 400),
          child: ListView.separated(
            shrinkWrap: true,
            padding: const EdgeInsets.symmetric(vertical: 8),
            itemCount: notifications.length,
            separatorBuilder: (_, _) =>
                Divider(height: 1, color: borderCol),
            itemBuilder: (_, i) {
              final n = notifications[i];
              final title   = n is Map ? (n['title'] ?? '') : (n.title ?? '');
              final message = n is Map ? (n['message'] ?? '') : (n.message ?? '');
              final col = isDark ? AppColors.warning : LightColors.warning;
              return ListTile(
                dense: true,
                leading: Container(
                  padding: const EdgeInsets.all(7),
                  decoration: BoxDecoration(
                      color: col.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(8)),
                  child: Icon(Icons.warning_amber_rounded, color: col, size: 16),
                ),
                title: Text(title.toString(),
                    style: TextStyle(
                        color: textColor,
                        fontSize: 13,
                        fontWeight: FontWeight.w600)),
                subtitle: message.toString().isNotEmpty
                    ? Text(message.toString(),
                        style: TextStyle(color: mutedColor, fontSize: 11))
                    : null,
              );
            },
          ),
        ),
    ]);
  }
}
