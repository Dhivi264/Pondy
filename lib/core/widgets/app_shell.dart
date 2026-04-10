import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../theme/app_theme.dart';
import '../responsive/responsive_layout.dart';
import '../../data/providers/upscaling_providers.dart';
import 'sidebar.dart';
import 'top_bar.dart';
import 'shared_widgets.dart';
import 'ai_assistant.dart';

class AppShell extends ConsumerWidget {
  final Widget child;
  const AppShell({super.key, required this.child});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final themeMode = ref.watch(themeProvider);
    final isDark    = themeMode == ThemeMode.dark;

    return Scaffold(
      backgroundColor: isDark ? AppColors.background : LightColors.background,
      appBar: const TopBar(),
      drawer: ResponsiveLayout.isMobile(context) ? const Sidebar() : null,
      floatingActionButton: const AiAssistantFab(),
      floatingActionButtonLocation: FloatingActionButtonLocation.endFloat,
      body: Row(children: [
        if (ResponsiveLayout.isDesktop(context)) const Sidebar(),
        if (ResponsiveLayout.isTablet(context))  const Sidebar(),
        Expanded(
          child: Column(children: [
            const BackendStatusBanner(),
            Expanded(child: child),
          ]),
        ),
      ]),
    );
  }
}
