/// Shared shell-level widgets (banner, etc.)
/// All reusable UI primitives live in ui_kit.dart - import that instead.
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../theme/app_theme.dart';
import '../../data/providers/app_providers.dart';
import '../../data/providers/upscaling_providers.dart';

// ── Backend offline banner ─────────────────────────────────────────────────────
class BackendStatusBanner extends ConsumerWidget {
  const BackendStatusBanner({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final status  = ref.watch(backendOnlineProvider);
    final isDark  = ref.watch(themeProvider) == ThemeMode.dark;
    return status.when(
      loading: () => const SizedBox.shrink(),
      error:   (_, _) => _banner(isDark),
      data:    (online) => online ? const SizedBox.shrink() : _banner(isDark),
    );
  }

  Widget _banner(bool isDark) => Container(
    width: double.infinity,
    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
    decoration: BoxDecoration(
      color: isDark ? AppColors.warningBg : LightColors.warningBg,
      border: Border(
        bottom: BorderSide(
          color: (isDark ? AppColors.warning : LightColors.warning).withValues(alpha: 0.25),
        ),
      ),
    ),
    child: Row(children: [
      Icon(Icons.wifi_off_rounded,
          color: isDark ? AppColors.warning : LightColors.warning, size: 15),
      const SizedBox(width: 8),
      Expanded(
        child: Text(
          'Backend offline — showing demo data. '
          'Start the FastAPI server at localhost:8000 (or check network settings).',
          style: TextStyle(
            color: isDark ? AppColors.warning : LightColors.warning,
            fontSize: 12,
          ),
        ),
      ),
    ]),
  );
}
