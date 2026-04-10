import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../theme/app_theme.dart';

class SideNavigation extends StatelessWidget {
  const SideNavigation({super.key});

  @override
  Widget build(BuildContext context) {
    final String location = GoRouterState.of(context).uri.path;
    return Container(
      width: 250,
      color: AppColors.surface,
      child: Column(
        children: [
          const SizedBox(height: 32),
          const Icon(Icons.security, size: 48, color: AppColors.primary),
          const SizedBox(height: 16),
          const Text('SecureVision', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
          const Text('ENTERPRISE CCTV', style: TextStyle(fontSize: 10, color: AppColors.textMuted, letterSpacing: 2)),
          const SizedBox(height: 32),
          const Divider(),
          _NavItem(
            icon: Icons.dashboard,
            title: 'Dashboard',
            isSelected: location.startsWith('/dashboard') || location.startsWith('/cameras'),
            onTap: () => _navigate(context, '/dashboard'),
          ),
          _NavItem(
            icon: Icons.people,
            title: 'Employees',
            isSelected: location.startsWith('/employees'),
            onTap: () => _navigate(context, '/employees'),
          ),
          _NavItem(
            icon: Icons.assignment_turned_in,
            title: 'Attendance',
            isSelected: location.startsWith('/attendance'),
            onTap: () => _navigate(context, '/attendance'),
          ),
          _NavItem(
            icon: Icons.video_library,
            title: 'CCTV Footage',
            isSelected: location.startsWith('/footage'),
            onTap: () => _navigate(context, '/footage'),
          ),
          const Spacer(),
          const Divider(),
          _NavItem(
            icon: Icons.settings,
            title: 'Settings',
            isSelected: location.startsWith('/settings'),
            onTap: () => _navigate(context, '/settings'),
          ),
          _NavItem(
            icon: Icons.person,
            title: 'Profile',
            isSelected: location.startsWith('/profile'),
            onTap: () => _navigate(context, '/profile'),
          ),
          const SizedBox(height: 16),
        ],
      ),
    );
  }

  void _navigate(BuildContext context, String path) {
    if (Scaffold.of(context).isDrawerOpen) {
      Navigator.pop(context); // close drawer
    }
    context.go(path);
  }
}

class _NavItem extends StatelessWidget {
  final IconData icon;
  final String title;
  final bool isSelected;
  final VoidCallback onTap;

  const _NavItem({
    required this.icon,
    required this.title,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final color = isSelected ? AppColors.primary : AppColors.textSecondary;
    return InkWell(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
        decoration: BoxDecoration(
          border: isSelected ? const Border(left: BorderSide(color: AppColors.primary, width: 4)) : null,
          color: isSelected ? AppColors.primary.withValues(alpha: 0.1) : Colors.transparent,
        ),
        child: Row(
          children: [
            Icon(icon, color: color, size: 24),
            const SizedBox(width: 16),
            Text(title, style: TextStyle(color: color, fontSize: 16, fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal)),
          ],
        ),
      ),
    );
  }
}
