/// Theme service — persists dark/light preference in browser localStorage.
library;

// ignore: avoid_web_libraries_in_flutter
import 'dart:html' as html;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

const _kThemeKey = 'app_theme_mode';

class ThemeNotifier extends Notifier<ThemeMode> {
  @override
  ThemeMode build() {
    final saved = html.window.localStorage[_kThemeKey];
    return saved == 'light' ? ThemeMode.light : ThemeMode.dark;
  }

  void toggle() {
    state = state == ThemeMode.dark ? ThemeMode.light : ThemeMode.dark;
    html.window.localStorage[_kThemeKey] =
        state == ThemeMode.dark ? 'dark' : 'light';
  }

  void set(ThemeMode mode) {
    state = mode;
    html.window.localStorage[_kThemeKey] =
        mode == ThemeMode.dark ? 'dark' : 'light';
  }
}

final themeProvider =
    NotifierProvider<ThemeNotifier, ThemeMode>(ThemeNotifier.new);
