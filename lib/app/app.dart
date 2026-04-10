import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/theme/app_theme.dart';
import '../data/providers/upscaling_providers.dart';
import 'router/app_router.dart';

class SmartCctvApp extends ConsumerWidget {
  const SmartCctvApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final themeMode = ref.watch(themeProvider);
    return MaterialApp.router(
      title: 'SecureVision LMP-TX',
      darkTheme:    AppTheme.darkTheme,
      theme:        AppTheme.lightTheme,
      themeMode:    themeMode,
      routerConfig: appRouter,
      debugShowCheckedModeBanner: false,
    );
  }
}
