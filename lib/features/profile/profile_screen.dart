import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/ui_kit.dart';
import '../../data/providers/app_providers.dart';
import '../../data/services/api_service.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final backend = ref.watch(backendOnlineProvider);

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.surface,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_rounded, color: AppColors.textPrimary),
          onPressed: () => context.go('/dashboard'),
        ),
        title: const Text('My Profile',
            style: TextStyle(color: AppColors.textPrimary, fontWeight: FontWeight.w700)),
        bottom: PreferredSize(preferredSize: const Size.fromHeight(1),
            child: Container(height: 1, color: AppColors.border)),
      ),
      body: Center(
        child: Container(
          width: 560,
          margin: const EdgeInsets.symmetric(vertical: 36),
          child: Column(children: [
            // Avatar banner
            Container(
              width: double.infinity, padding: const EdgeInsets.all(32),
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  begin: Alignment.topLeft, end: Alignment.bottomRight,
                  colors: [Color(0xFF0F172A), Color(0xFF0B1120)]),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: AppColors.border),
              ),
              child: Column(children: [
                Container(
                  width: 80, height: 80,
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(colors: [AppColors.primary, AppColors.teal]),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(Icons.person_rounded, color: Colors.white, size: 40),
                ),
                const SizedBox(height: 14),
                const Text('System Administrator',
                    style: TextStyle(color: AppColors.textPrimary, fontSize: 20, fontWeight: FontWeight.w800)),
                const SizedBox(height: 4),
                const Text('admin@securevision.local',
                    style: TextStyle(color: AppColors.textMuted, fontSize: 13)),
                const SizedBox(height: 12),
                const StatusBadge('SUPER ADMIN', color: AppColors.primary),
              ]),
            ),
            const SizedBox(height: 20),
            // Info card
            Container(
              width: double.infinity, padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(color: AppColors.surfaceCard,
                  borderRadius: BorderRadius.circular(12), border: Border.all(color: AppColors.border)),
              child: Column(children: [
                const InfoRow('Role', 'Super Administrator', valueColor: AppColors.primary),
                const Divider(color: AppColors.border, height: 20),
                const InfoRow('Organization', 'Headquarters'),
                const Divider(color: AppColors.border, height: 20),
                const InfoRow('Platform', 'SecureVision LMP-TX v2.0'),
                const Divider(color: AppColors.border, height: 20),
                Row(children: [
                  const Text('Backend Status', style: TextStyle(color: AppColors.textMuted, fontSize: 13)),
                  const Spacer(),
                  backend.when(
                    loading: () => const SizedBox(width: 14, height: 14,
                        child: CircularProgressIndicator(strokeWidth: 1.5, color: AppColors.primary)),
                    error: (_, _) => const StatusBadge('OFFLINE', color: AppColors.error),
                    data: (v) => StatusBadge(v ? 'ONLINE' : 'OFFLINE',
                        color: v ? AppColors.success : AppColors.error),
                  ),
                ]),
              ]),
            ),
            const SizedBox(height: 20),
            // Actions
            Row(children: [
              Expanded(child: OutlinedButton.icon(
                onPressed: () {},
                icon: const Icon(Icons.edit_rounded, size: 16),
                label: const Text('Edit Profile'),
              )),
              const SizedBox(width: 12),
              Expanded(child: ElevatedButton.icon(
                onPressed: () {
                  ApiService.instance.logout();
                  ref.read(authProvider.notifier).state = false;
                  context.go('/login');
                },
                style: ElevatedButton.styleFrom(backgroundColor: AppColors.error),
                icon: const Icon(Icons.logout_rounded, size: 16),
                label: const Text('Sign Out', style: TextStyle(fontWeight: FontWeight.w700)),
              )),
            ]),
          ]),
        ),
      ),
    );
  }
}
