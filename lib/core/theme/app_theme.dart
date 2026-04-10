import 'package:flutter/material.dart';

// ── Dark palette ───────────────────────────────────────────────────────────────
class AppColors {
  static const Color background        = Color(0xFF060A12);
  static const Color bg                = Color(0xFF060A12);
  static const Color surface           = Color(0xFF0C1420);
  static const Color surfaceCard       = Color(0xFF111C2E);
  static const Color surfaceHighlight  = Color(0xFF182538);
  static const Color surfaceElevated   = Color(0xFF14203A);

  static const Color primary           = Color(0xFF38BDF8);
  static const Color primaryDark       = Color(0xFF0EA5E9);
  static const Color accent            = Color(0xFF38BDF8);
  static const Color teal              = Color(0xFF2DD4BF);
  static const Color purple            = Color(0xFFA78BFA);
  static const Color success           = Color(0xFF34D399);
  static const Color successBg         = Color(0xFF042A1C);
  static const Color warning           = Color(0xFFFBBF24);
  static const Color warningBg         = Color(0xFF1C1509);
  static const Color error             = Color(0xFFF87171);
  static const Color errorBg           = Color(0xFF2A0F0F);
  static const Color info              = Color(0xFF60A5FA);

  static const Color textPrimary       = Color(0xFFF0F6FF);
  static const Color textLight         = Color(0xFFF0F6FF);
  static const Color textSecondary     = Color(0xFF94A3B8);
  static const Color textMuted         = Color(0xFF4B6280);

  static const Color border            = Color(0xFF1A2A40);
  static const Color borderBright      = Color(0xFF253A55);

  static const Gradient primaryGradient = LinearGradient(
    colors: [Color(0xFF38BDF8), Color(0xFF6366F1)],
    begin: Alignment.topLeft, end: Alignment.bottomRight,
  );
  static const Gradient accentGradient = LinearGradient(
    colors: [Color(0xFF2DD4BF), Color(0xFF0EA5E9)],
    begin: Alignment.topLeft, end: Alignment.bottomRight,
  );
  static const Gradient dangerGradient = LinearGradient(
    colors: [Color(0xFFF87171), Color(0xFFEF4444)],
    begin: Alignment.topLeft, end: Alignment.bottomRight,
  );
  static const Gradient glassGradient = LinearGradient(
    colors: [Color(0x18FFFFFF), Color(0x04FFFFFF)],
    begin: Alignment.topLeft, end: Alignment.bottomRight,
  );
  static const Gradient sidebarGradient = LinearGradient(
    colors: [Color(0xFF0C1420), Color(0xFF080E1A)],
    begin: Alignment.topCenter, end: Alignment.bottomCenter,
  );

  static const List<BoxShadow> premiumShadow = [
    BoxShadow(color: Color(0x40000000), blurRadius: 24, offset: Offset(0, 8)),
    BoxShadow(color: Color(0x1438BDF8), blurRadius: 48, offset: Offset(0, 4)),
  ];
  static const List<BoxShadow> cardShadow = [
    BoxShadow(color: Color(0x30000000), blurRadius: 12, offset: Offset(0, 4)),
  ];
}

// ── Light palette ──────────────────────────────────────────────────────────────
class LightColors {
  static const Color background        = Color(0xFFF4F7FC);
  static const Color surface           = Color(0xFFFFFFFF);
  static const Color surfaceCard       = Color(0xFFFFFFFF);
  static const Color surfaceHighlight  = Color(0xFFF0F4FA);
  static const Color surfaceElevated   = Color(0xFFEBEFF8);

  static const Color primary           = Color(0xFF0284C7);
  static const Color primaryDark       = Color(0xFF0369A1);
  static const Color teal              = Color(0xFF0D9488);
  static const Color purple            = Color(0xFF7C3AED);
  static const Color success           = Color(0xFF16A34A);
  static const Color successBg         = Color(0xFFDCFCE7);
  static const Color warning           = Color(0xFFD97706);
  static const Color warningBg         = Color(0xFFFEF3C7);
  static const Color error             = Color(0xFFDC2626);
  static const Color errorBg           = Color(0xFFFEE2E2);
  static const Color info              = Color(0xFF2563EB);

  static const Color textPrimary       = Color(0xFF0F172A);
  static const Color textSecondary     = Color(0xFF475569);
  static const Color textMuted         = Color(0xFF94A3B8);

  static const Color border            = Color(0xFFE2E8F0);
  static const Color borderBright      = Color(0xFFCBD5E1);

  static const List<BoxShadow> cardShadow = [
    BoxShadow(color: Color(0x0A000000), blurRadius: 8, offset: Offset(0, 2)),
    BoxShadow(color: Color(0x06000000), blurRadius: 16, offset: Offset(0, 4)),
  ];
  static const List<BoxShadow> premiumShadow = [
    BoxShadow(color: Color(0x10000000), blurRadius: 20, offset: Offset(0, 6)),
    BoxShadow(color: Color(0x080284C7), blurRadius: 30, offset: Offset(0, 3)),
  ];
}

// Helper: Inter-equivalent TextStyle (uses system sans-serif on web)
TextStyle _inter({
  Color? color,
  double? fontSize,
  FontWeight? fontWeight,
  double? letterSpacing,
}) =>
    TextStyle(
      color: color,
      fontSize: fontSize,
      fontWeight: fontWeight,
      letterSpacing: letterSpacing,
    );

// ── Theme builder ──────────────────────────────────────────────────────────────
class AppTheme {
  static const Color background  = AppColors.background;
  static const Color surface     = AppColors.surface;
  static const Color primary     = AppColors.primary;
  static const Color primaryDark = AppColors.primaryDark;
  static const Color textLight   = AppColors.textPrimary;
  static const Color textMuted   = AppColors.textMuted;
  static const Color border      = AppColors.border;
  static const Color error       = AppColors.error;
  static const Color success     = AppColors.success;
  static const Color warning     = AppColors.warning;
  static const Color teal        = AppColors.teal;
  static const Color warning2    = AppColors.warning;

  static ThemeData get darkTheme {
    final base = ThemeData.dark(useMaterial3: true);
    return base.copyWith(
      scaffoldBackgroundColor: AppColors.background,
      primaryColor: AppColors.primary,
      colorScheme: const ColorScheme.dark(
        primary: AppColors.primary,
        secondary: AppColors.teal,
        surface: AppColors.surface,
        error: AppColors.error,
        onPrimary: Colors.white,
        onSurface: AppColors.textPrimary,
        tertiary: AppColors.purple,
        outline: AppColors.border,
      ),
      textTheme: base.textTheme.apply(
        bodyColor: AppColors.textPrimary,
        displayColor: AppColors.textPrimary,
      ),
      appBarTheme: AppBarTheme(
        backgroundColor: AppColors.surface,
        elevation: 0,
        centerTitle: false,
        iconTheme: const IconThemeData(color: AppColors.textPrimary),
        titleTextStyle: _inter(
          color: AppColors.textPrimary, fontSize: 17, fontWeight: FontWeight.w700,
        ),
        surfaceTintColor: Colors.transparent,
        shadowColor: Colors.transparent,
      ),
      drawerTheme: const DrawerThemeData(backgroundColor: AppColors.surface),
      cardTheme: CardThemeData(
        color: AppColors.surfaceCard,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(14),
          side: const BorderSide(color: AppColors.border),
        ),
      ),
      dividerTheme: const DividerThemeData(
          color: AppColors.border, thickness: 1, space: 1),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.primary,
          foregroundColor: Colors.white,
          elevation: 0,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 13),
          textStyle: _inter(fontWeight: FontWeight.w600, fontSize: 13.5),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: AppColors.textPrimary,
          side: const BorderSide(color: AppColors.borderBright),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 13),
          textStyle: _inter(fontWeight: FontWeight.w500, fontSize: 13.5),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AppColors.surfaceHighlight,
        border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: const BorderSide(color: AppColors.border)),
        enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: const BorderSide(color: AppColors.border)),
        focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: const BorderSide(color: AppColors.primary, width: 1.5)),
        labelStyle: const TextStyle(color: AppColors.textMuted),
        hintStyle: const TextStyle(color: AppColors.textMuted, fontSize: 13),
        prefixIconColor: AppColors.textMuted,
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 13),
        isDense: true,
      ),
      tabBarTheme: TabBarThemeData(
        labelColor: AppColors.primary,
        unselectedLabelColor: AppColors.textMuted,
        indicatorColor: AppColors.primary,
        indicatorSize: TabBarIndicatorSize.label,
        labelStyle: _inter(fontWeight: FontWeight.w700, fontSize: 13),
        unselectedLabelStyle: _inter(fontWeight: FontWeight.w500, fontSize: 13),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: AppColors.surfaceHighlight,
        labelStyle: _inter(color: AppColors.textSecondary, fontSize: 12),
        side: const BorderSide(color: AppColors.border),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      ),
      progressIndicatorTheme:
          const ProgressIndicatorThemeData(color: AppColors.primary),
      switchTheme: SwitchThemeData(
        thumbColor: WidgetStateProperty.resolveWith((s) =>
            s.contains(WidgetState.selected)
                ? AppColors.primary
                : AppColors.textMuted),
        trackColor: WidgetStateProperty.resolveWith((s) =>
            s.contains(WidgetState.selected)
                ? AppColors.primary.withValues(alpha: 0.3)
                : AppColors.surfaceHighlight),
        trackOutlineColor: WidgetStateProperty.resolveWith((s) =>
            s.contains(WidgetState.selected)
                ? AppColors.primary.withValues(alpha: 0.4)
                : AppColors.border),
      ),
      dataTableTheme: DataTableThemeData(
        headingTextStyle: _inter(
            color: AppColors.textMuted,
            fontSize: 11,
            fontWeight: FontWeight.w700,
            letterSpacing: 0.8),
        dataTextStyle: _inter(color: AppColors.textPrimary, fontSize: 13),
        headingRowColor: WidgetStateProperty.all(AppColors.surface),
        dataRowColor: WidgetStateProperty.resolveWith((s) =>
            s.contains(WidgetState.hovered)
                ? AppColors.surfaceHighlight
                : Colors.transparent),
        dividerThickness: 1,
        columnSpacing: 24,
      ),
      tooltipTheme: TooltipThemeData(
        decoration: BoxDecoration(
          color: AppColors.surfaceHighlight,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: AppColors.border),
        ),
        textStyle: const TextStyle(color: AppColors.textPrimary, fontSize: 12),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      ),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: AppColors.surfaceCard,
        contentTextStyle: _inter(color: AppColors.textPrimary, fontSize: 13),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(10),
          side: const BorderSide(color: AppColors.border),
        ),
        behavior: SnackBarBehavior.floating,
        elevation: 4,
      ),
    );
  }

  static ThemeData get lightTheme {
    final base = ThemeData.light(useMaterial3: true);
    return base.copyWith(
      scaffoldBackgroundColor: LightColors.background,
      primaryColor: LightColors.primary,
      colorScheme: ColorScheme.fromSeed(
        seedColor: LightColors.primary,
        brightness: Brightness.light,
        surface: LightColors.surface,
        error: LightColors.error,
      ).copyWith(
        primary: LightColors.primary,
        secondary: LightColors.teal,
        tertiary: LightColors.purple,
        onSurface: LightColors.textPrimary,
        outline: LightColors.border,
      ),
      textTheme: base.textTheme.apply(
        bodyColor: LightColors.textPrimary,
        displayColor: LightColors.textPrimary,
      ),
      appBarTheme: AppBarTheme(
        backgroundColor: LightColors.surface,
        elevation: 0,
        centerTitle: false,
        iconTheme: const IconThemeData(color: LightColors.textPrimary),
        titleTextStyle: _inter(
          color: LightColors.textPrimary, fontSize: 17, fontWeight: FontWeight.w700,
        ),
        surfaceTintColor: Colors.transparent,
        shadowColor: Colors.transparent,
      ),
      cardTheme: CardThemeData(
        color: LightColors.surfaceCard,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(14),
          side: const BorderSide(color: LightColors.border),
        ),
        shadowColor: const Color(0x10000000),
      ),
      drawerTheme: const DrawerThemeData(backgroundColor: LightColors.surface),
      dividerTheme: const DividerThemeData(
          color: LightColors.border, thickness: 1, space: 1),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: LightColors.primary,
          foregroundColor: Colors.white,
          elevation: 0,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 13),
          textStyle: _inter(fontWeight: FontWeight.w600, fontSize: 13.5),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: LightColors.textPrimary,
          side: const BorderSide(color: LightColors.borderBright),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 13),
          textStyle: _inter(fontWeight: FontWeight.w500, fontSize: 13.5),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: LightColors.surfaceHighlight,
        border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: const BorderSide(color: LightColors.border)),
        enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: const BorderSide(color: LightColors.border)),
        focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: const BorderSide(color: LightColors.primary, width: 1.5)),
        labelStyle: const TextStyle(color: LightColors.textMuted, fontSize: 13),
        hintStyle: const TextStyle(color: LightColors.textMuted, fontSize: 13),
        prefixIconColor: LightColors.textMuted,
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 13),
        isDense: true,
      ),
      switchTheme: SwitchThemeData(
        thumbColor: WidgetStateProperty.resolveWith((s) =>
            s.contains(WidgetState.selected) ? LightColors.primary : LightColors.textMuted),
        trackColor: WidgetStateProperty.resolveWith((s) =>
            s.contains(WidgetState.selected)
                ? LightColors.primary.withValues(alpha: 0.25)
                : LightColors.border),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: LightColors.surfaceHighlight,
        labelStyle: _inter(color: LightColors.textSecondary, fontSize: 12),
        side: const BorderSide(color: LightColors.border),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
      tooltipTheme: TooltipThemeData(
        decoration: BoxDecoration(
          color: LightColors.textPrimary,
          borderRadius: BorderRadius.circular(8),
        ),
        textStyle: const TextStyle(color: Colors.white, fontSize: 12),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      ),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: LightColors.surface,
        contentTextStyle: _inter(color: LightColors.textPrimary, fontSize: 13),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(10),
          side: const BorderSide(color: LightColors.border),
        ),
        behavior: SnackBarBehavior.floating,
        elevation: 4,
      ),
    );
  }
}
