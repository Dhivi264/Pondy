import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:go_router/go_router.dart';
import '../theme/app_theme.dart';
import '../responsive/responsive_layout.dart';
import '../../data/services/api_service.dart';
import '../services/backend_service.dart';

class Sidebar extends StatelessWidget {
  const Sidebar({super.key});

  @override
  Widget build(BuildContext context) {
    final loc = GoRouterState.of(context).matchedLocation;
    final isTablet = ResponsiveLayout.isTablet(context);
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Container(
      width: isTablet ? 220 : 256,
      decoration: BoxDecoration(
        color: isDark ? AppColors.surface : LightColors.surface,
        border: Border(
          right: BorderSide(
            color: isDark ? AppColors.border : LightColors.border,
          ),
        ),
        boxShadow: isDark
            ? const [BoxShadow(color: Color(0x30000000), blurRadius: 20)]
            : const [BoxShadow(color: Color(0x08000000), blurRadius: 16)],
      ),
      child: Column(children: [
        _Logo(isDark: isDark),
        const SizedBox(height: 8),
        Expanded(
          child: ListView(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            children: [
              _GroupLabel('MONITOR', isDark: isDark),
              _NavItem(icon: Icons.dashboard_rounded,    label: 'Dashboard',      route: '/dashboard',  sel: loc.startsWith('/dashboard'),  isDark: isDark),
              _NavItem(icon: Icons.videocam_rounded,     label: 'Live Cameras',   route: '/cameras',    sel: loc.startsWith('/cameras'),    isDark: isDark),
              _NavItem(icon: Icons.video_library_rounded,label: 'CCTV Footage',   route: '/footage',    sel: loc.startsWith('/footage'),    isDark: isDark),
              const SizedBox(height: 12),
              _GroupLabel('OPERATIONS', isDark: isDark),
              _NavItem(icon: Icons.people_rounded,           label: 'Employees',   route: '/employees',  sel: loc.startsWith('/employees'),  isDark: isDark),
              _NavItem(icon: Icons.event_available_rounded,  label: 'Attendance',  route: '/attendance', sel: loc.startsWith('/attendance'), isDark: isDark),
              const SizedBox(height: 12),
              _GroupLabel('SYSTEM', isDark: isDark),
              _NavItem(icon: Icons.settings_rounded, label: 'Settings', route: '/settings', sel: loc.startsWith('/settings'), isDark: isDark),
            ],
          ),
        ),
        Divider(height: 1, color: isDark ? AppColors.border : LightColors.border),
        _NavItem(
          icon: Icons.logout_rounded,
          label: 'Sign Out',
          route: '/login',
          sel: false,
          color: isDark ? AppColors.error : LightColors.error,
          isDark: isDark,
        ),
        const SizedBox(height: 10),
      ]),
    );
  }
}

class _Logo extends StatelessWidget {
  final bool isDark;
  const _Logo({required this.isDark});

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 64,
      padding: const EdgeInsets.symmetric(horizontal: 18),
      decoration: BoxDecoration(
        border: Border(
          bottom: BorderSide(
            color: isDark ? AppColors.border : LightColors.border,
          ),
        ),
      ),
      child: Row(children: [
        Container(
          width: 36, height: 36,
          decoration: BoxDecoration(
            gradient: isDark
                ? const LinearGradient(
                    colors: [AppColors.primary, AppColors.teal],
                    begin: Alignment.topLeft, end: Alignment.bottomRight)
                : const LinearGradient(
                    colors: [LightColors.primary, LightColors.teal],
                    begin: Alignment.topLeft, end: Alignment.bottomRight),
            borderRadius: BorderRadius.circular(10),
            boxShadow: [
              BoxShadow(
                color: (isDark ? AppColors.primary : LightColors.primary).withValues(alpha: 0.35),
                blurRadius: 12, offset: const Offset(0, 3),
              ),
            ],
          ),
          child: const Icon(Icons.security_rounded, color: Colors.white, size: 20),
        ),
        const SizedBox(width: 12),
        Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'SecureVision',
              style: TextStyle(
                color: isDark ? AppColors.textPrimary : LightColors.textPrimary,
                fontSize: 14,
                fontWeight: FontWeight.w800,
                letterSpacing: 0.3,
              ),
            ),
            Text(
              'LMP-TX Platform',
              style: TextStyle(
                color: isDark ? AppColors.teal : LightColors.teal,
                fontSize: 9.5,
                fontWeight: FontWeight.w700,
                letterSpacing: 1.0,
              ),
            ),
          ],
        ),
      ]),
    );
  }
}

class _GroupLabel extends StatelessWidget {
  final String text;
  final bool isDark;
  const _GroupLabel(this.text, {required this.isDark});

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(left: 10, top: 6, bottom: 4),
    child: Text(
      text,
      style: TextStyle(
        color: isDark ? AppColors.textMuted : LightColors.textMuted,
        fontSize: 10,
        fontWeight: FontWeight.w700,
        letterSpacing: 1.4,
      ),
    ),
  );
}

class _NavItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final String route;
  final bool sel;
  final Color? color;
  final bool isDark;
  const _NavItem({
    required this.icon,
    required this.label,
    required this.route,
    required this.sel,
    required this.isDark,
    this.color,
  });

  @override
  Widget build(BuildContext context) {
    final defaultAccent = isDark ? AppColors.primary : LightColors.primary;
    final c = sel ? (color ?? defaultAccent) : (isDark ? AppColors.textSecondary : LightColors.textSecondary);
    final selBg = (color ?? defaultAccent).withValues(alpha: isDark ? 0.1 : 0.08);
    final selBorder = (color ?? defaultAccent).withValues(alpha: isDark ? 0.2 : 0.15);

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 1.5),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(10),
          onTap: () => context.go(route),
          hoverColor: isDark
              ? AppColors.surfaceHighlight.withValues(alpha: 0.5)
              : LightColors.surfaceHighlight,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 180),
            curve: Curves.easeOutCubic,
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            decoration: BoxDecoration(
              color: sel ? selBg : Colors.transparent,
              borderRadius: BorderRadius.circular(10),
              border: sel ? Border.all(color: selBorder, width: 1) : null,
            ),
            child: Row(children: [
              // Left accent bar for selected state
              AnimatedContainer(
                duration: const Duration(milliseconds: 180),
                width: 3,
                height: 16,
                margin: const EdgeInsets.only(right: 10),
                decoration: BoxDecoration(
                  gradient: sel
                      ? LinearGradient(
                          colors: [color ?? defaultAccent, (color ?? defaultAccent).withValues(alpha: 0.4)],
                          begin: Alignment.topCenter,
                          end: Alignment.bottomCenter,
                        )
                      : null,
                  color: sel ? null : Colors.transparent,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
              Icon(icon, color: c, size: 18),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  label,
                  style: TextStyle(
                    color: c,
                    fontSize: 13,
                    fontWeight: sel ? FontWeight.w700 : FontWeight.w500,
                    letterSpacing: sel ? 0.1 : 0,
                  ),
                ),
              ),
            ]),
          ),
        ),
      ),
    );
  }
}

class _ActionItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;
  final Color? color;
  final bool isDark;
  
  const _ActionItem({
    required this.icon,
    required this.label,
    required this.onTap,
    required this.isDark,
    this.color,
  });

  @override
  Widget build(BuildContext context) {
    final c = color ?? (isDark ? AppColors.textSecondary : LightColors.textSecondary);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 1.5, horizontal: 10),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(10),
          onTap: onTap,
          hoverColor: isDark
              ? AppColors.surfaceHighlight.withValues(alpha: 0.5)
              : LightColors.surfaceHighlight,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            child: Row(children: [
              Icon(icon, color: c, size: 18),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  label,
                  style: TextStyle(
                    color: c,
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
            ]),
          ),
        ),
      ),
    );
  }
}
