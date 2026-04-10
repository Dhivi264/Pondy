/// Single source of truth for all shared UI primitives.
/// Every screen imports this file only.
library;

import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

// ── Stat card ──────────────────────────────────────────────────────────────────
class StatCard extends StatelessWidget {
  final String label;
  final String value;
  final IconData icon;
  final Color? accent;
  final String? sub;
  const StatCard({
    super.key,
    required this.label,
    required this.value,
    required this.icon,
    this.accent,
    this.sub,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final primary = isDark ? AppColors.primary : LightColors.primary;
    final surfaceCard = isDark ? AppColors.surfaceCard : LightColors.surfaceCard;
    final border = isDark ? AppColors.border : LightColors.border;
    final textPrimary = isDark ? AppColors.textPrimary : LightColors.textPrimary;
    final textMuted = isDark ? AppColors.textMuted : LightColors.textMuted;
    final textSecondary = isDark ? AppColors.textSecondary : LightColors.textSecondary;
    final background = isDark ? AppColors.background : LightColors.background;
    final shadow = isDark ? AppColors.premiumShadow : LightColors.premiumShadow;

    final c = accent ?? primary;

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: surfaceCard,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: border.withValues(alpha: 0.5)),
        boxShadow: shadow,
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [c.withValues(alpha: 0.25), c.withValues(alpha: 0.05)],
                begin: Alignment.topLeft, end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: c.withValues(alpha: 0.2)),
            ),
            child: Icon(icon, color: c, size: 20),
          ),
          // Pulsing activity dot if connected
          Container(
            width: 8, height: 8,
            decoration: BoxDecoration(
              color: c,
              shape: BoxShape.circle,
              boxShadow: [BoxShadow(color: c.withValues(alpha: 0.4), blurRadius: 8, spreadRadius: 2)],
            ),
          ),
        ]),
        const SizedBox(height: 20),
        Text(value,
            style: TextStyle(
                color: textPrimary, fontSize: 28, fontWeight: FontWeight.w800, letterSpacing: -0.5)),
        const SizedBox(height: 6),
        Text(label.toUpperCase(),
            style: TextStyle(
                color: textMuted, fontSize: 10, fontWeight: FontWeight.w700, letterSpacing: 1.2)),
        if (sub != null) ...[
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: background.withValues(alpha: 0.5),
              borderRadius: BorderRadius.circular(6),
            ),
            child: Text(sub!,
                style: TextStyle(color: textSecondary, fontSize: 10, fontWeight: FontWeight.w500)),
          ),
        ],
      ]),
    );
  }
}

// ── Status badge ───────────────────────────────────────────────────────────────
class StatusBadge extends StatelessWidget {
  final String label;
  final Color color;
  const StatusBadge(this.label, {super.key, required this.color});

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
    decoration: BoxDecoration(
      color: color.withValues(alpha: 0.12),
      borderRadius: BorderRadius.circular(20),
      border: Border.all(color: color.withValues(alpha: 0.3)),
    ),
    child: Row(mainAxisSize: MainAxisSize.min, children: [
      Container(width: 5, height: 5,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
      const SizedBox(width: 5),
      Text(label,
          style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.w700)),
    ]),
  );
}

// ── Section header ─────────────────────────────────────────────────────────────
class SectionHeader extends StatelessWidget {
  final String title;
  final Widget? trailing;
  const SectionHeader(this.title, {super.key, this.trailing});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final textPrimary = isDark ? AppColors.textPrimary : LightColors.textPrimary;

    return Row(children: [
      Text(title,
          style: TextStyle(
              color: textPrimary, fontSize: 16, fontWeight: FontWeight.w700)),
      if (trailing != null) ...[const Spacer(), trailing!],
    ]);
  }
}

// ── Screen loader ──────────────────────────────────────────────────────────────
class ScreenLoader extends StatelessWidget {
  final String? message;
  const ScreenLoader({super.key, this.message});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final primary = isDark ? AppColors.primary : LightColors.primary;
    final textMuted = isDark ? AppColors.textMuted : LightColors.textMuted;

    return Center(
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        SizedBox(
            width: 32,
            height: 32,
            child: CircularProgressIndicator(
                strokeWidth: 2, color: primary)),
        if (message != null) ...[
          const SizedBox(height: 16),
          Text(message!,
              style: TextStyle(color: textMuted, fontSize: 13)),
        ],
      ]),
    );
  }
}

// ── Empty state ────────────────────────────────────────────────────────────────
class EmptyState extends StatelessWidget {
  final IconData icon;
  final String title;
  final String? subtitle;
  const EmptyState({super.key, required this.icon, required this.title, this.subtitle});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final textMuted = isDark ? AppColors.textMuted : LightColors.textMuted;
    final textSecondary = isDark ? AppColors.textSecondary : LightColors.textSecondary;

    return Center(
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        Icon(icon, size: 52, color: textMuted),
        const SizedBox(height: 16),
        Text(title,
            style: TextStyle(
                color: textSecondary,
                fontSize: 15,
                fontWeight: FontWeight.w600)),
        if (subtitle != null) ...[
          const SizedBox(height: 6),
          Text(subtitle!,
              style: TextStyle(color: textMuted, fontSize: 13),
              textAlign: TextAlign.center),
        ],
      ]),
    );
  }
}

// ── Error state ────────────────────────────────────────────────────────────────
class ErrorState extends StatelessWidget {
  final String message;
  final VoidCallback? onRetry;
  const ErrorState({super.key, required this.message, this.onRetry});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final error = isDark ? AppColors.error : LightColors.error;
    final textSecondary = isDark ? AppColors.textSecondary : LightColors.textSecondary;

    return Center(
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        Icon(Icons.error_outline_rounded, size: 48, color: error),
        const SizedBox(height: 12),
        Text(message,
            style: TextStyle(color: textSecondary, fontSize: 14),
            textAlign: TextAlign.center),
        if (onRetry != null) ...[
          const SizedBox(height: 16),
          OutlinedButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh, size: 16),
              label: const Text('Retry')),
        ],
      ]),
    );
  }
}

// ── Table header cell ──────────────────────────────────────────────────────────
class ThCell extends StatelessWidget {
  final String text;
  final int flex;
  const ThCell(this.text, {super.key, this.flex = 1});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final textMuted = isDark ? AppColors.textMuted : LightColors.textMuted;

    return Expanded(
      flex: flex,
      child: Text(text,
          style: TextStyle(
              color: textMuted,
              fontSize: 11,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.8)),
    );
  }
}

// ── Table data row ─────────────────────────────────────────────────────────────
class TrRow extends StatelessWidget {
  final List<Widget> cells;
  final VoidCallback? onTap;
  const TrRow({super.key, required this.cells, this.onTap});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final border = isDark ? AppColors.border : LightColors.border;

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 13),
        decoration: BoxDecoration(
            border: Border(
                bottom: BorderSide(color: border, width: 0.5))),
        child: Row(children: cells),
      ),
    );
  }
}

// ── Search field ───────────────────────────────────────────────────────────────
class SearchField extends StatelessWidget {
  final String hint;
  final ValueChanged<String> onChanged;
  final double width;
  const SearchField(
      {super.key,
      required this.hint,
      required this.onChanged,
      this.width = 260});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final textPrimary = isDark ? AppColors.textPrimary : LightColors.textPrimary;
    final textMuted = isDark ? AppColors.textMuted : LightColors.textMuted;

    return SizedBox(
      width: width,
      child: TextField(
        onChanged: onChanged,
        style: TextStyle(color: textPrimary, fontSize: 13),
        decoration: InputDecoration(
          hintText: hint,
          prefixIcon: Icon(Icons.search_rounded, size: 17, color: textMuted),
          suffixIcon: Icon(Icons.tune_rounded,
              size: 16, color: textMuted),
        ),
      ),
    );
  }
}

// ── Info row ───────────────────────────────────────────────────────────────────
class InfoRow extends StatelessWidget {
  final String label;
  final String value;
  final Color? valueColor;
  const InfoRow(this.label, this.value, {super.key, this.valueColor});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final textPrimary = isDark ? AppColors.textPrimary : LightColors.textPrimary;
    final textMuted = isDark ? AppColors.textMuted : LightColors.textMuted;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(children: [
        Text(label,
            style: TextStyle(color: textMuted, fontSize: 13)),
        const Spacer(),
        Text(value,
            style: TextStyle(
                color: valueColor ?? textPrimary,
                fontSize: 13,
                fontWeight: FontWeight.w600)),
      ]),
    );
  }
}
