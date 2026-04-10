import 'package:flutter/material.dart';
import 'package:flutter_mjpeg/flutter_mjpeg.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/ui_kit.dart';
import '../../core/responsive/responsive_layout.dart';
import '../../data/providers/app_providers.dart';
import '../../data/models/models.dart';
import '../../data/services/api_service.dart';

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final summary   = ref.watch(dashboardSummaryProvider);
    final cameras   = ref.watch(camerasProvider);
    final anomalies = ref.watch(lmpAnomaliesProvider);
    final alSamples = ref.watch(lmpPendingSamplesProvider);
    final isDesktop = ResponsiveLayout.isDesktop(context);
    final isDark    = Theme.of(context).brightness == Brightness.dark;

    final bg        = isDark ? AppColors.background       : LightColors.background;
    final primary   = isDark ? AppColors.primary          : LightColors.primary;
    final textPrim  = isDark ? AppColors.textPrimary      : LightColors.textPrimary;
    final textSec   = isDark ? AppColors.textSecondary    : LightColors.textSecondary;
    final textMuted = isDark ? AppColors.textMuted        : LightColors.textMuted;

    return Scaffold(
      backgroundColor: bg,
      appBar: isDesktop ? null : AppBar(
        title: const Text('SYSTEM DASHBOARD'),
        actions: [
          IconButton(
            onPressed: () {
              ref.invalidate(dashboardSummaryProvider);
              ref.invalidate(camerasProvider);
            },
            icon: const Icon(Icons.refresh_rounded),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(dashboardSummaryProvider);
          ref.invalidate(camerasProvider);
          ref.invalidate(lmpAnomaliesProvider);
        },
        color: primary,
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [

            // ── Hero header ────────────────────────────────────────────────────
            Container(
              width: double.infinity,
              padding: EdgeInsets.fromLTRB(
                isDesktop ? 32 : 20,
                isDesktop ? 40 : 24,
                isDesktop ? 32 : 20,
                isDesktop ? 48 : 28,
              ),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: isDark
                      ? [primary.withValues(alpha: 0.12), Colors.transparent]
                      : [primary.withValues(alpha: 0.06), Colors.transparent],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                border: Border(
                  bottom: BorderSide(
                    color: isDark ? AppColors.border : LightColors.border,
                    width: isDark ? 1 : 0.5,
                  ),
                ),
              ),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  ref.watch(systemAiStatusProvider).when(
                    loading: () => _AiStatusPill(label: '…', color: textMuted, isDark: isDark),
                    error:   (_, _) => _AiStatusPill(label: 'ERROR', color: isDark ? AppColors.error : LightColors.error, isDark: isDark),
                    data: (active) => _AiStatusPill(
                      label: active ? 'AI ACTIVE' : 'AI STOPPED',
                      color: active ? primary : textMuted,
                      isDark: isDark,
                      canToggle: true,
                      isActive: active,
                      onTap: () => _toggleAi(context, ref, active),
                    ),
                  ),
                  const SizedBox(width: 12),
                  _WatchdogPill(isDark: isDark),
                  const SizedBox(width: 12),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: isDark ? AppColors.surfaceHighlight : LightColors.surfaceHighlight,
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      'V11.0.4-PREMIUM',
                      style: TextStyle(color: textMuted, fontSize: 9, fontWeight: FontWeight.w800, letterSpacing: 1.2),
                    ),
                  ),
                ]),
                const SizedBox(height: 18),
                Text(
                  'Real-time Surveillance Hub',
                  style: TextStyle(
                    color: textPrim,
                    fontSize: isDesktop ? 38 : 26,
                    fontWeight: FontWeight.w900,
                    letterSpacing: -1.2,
                    height: 1.1,
                  ),
                ),
                const SizedBox(height: 6),
                Row(children: [
                  Container(
                    width: 8, height: 8,
                    margin: const EdgeInsets.only(right: 6),
                    decoration: BoxDecoration(
                      color: isDark ? AppColors.success : LightColors.success,
                      shape: BoxShape.circle,
                      boxShadow: [
                        BoxShadow(
                          color: (isDark ? AppColors.success : LightColors.success).withValues(alpha: 0.4),
                          blurRadius: 6,
                          spreadRadius: 1,
                        ),
                      ],
                    ),
                  ),
                  Text(
                    'Monitoring 32 synchronized streams • Neural AI active',
                    style: TextStyle(color: textSec, fontSize: 13),
                  ),
                ]),
              ]),
            ),

            Padding(
              padding: EdgeInsets.symmetric(horizontal: isDesktop ? 32 : 16),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const SizedBox(height: 28),

                // ── KPI cards ──────────────────────────────────────────────────
                summary.when(
                  loading: () => _shimmerRow(isDesktop ? 6 : 2, isDark),
                  error:   (_, _) => _warnBanner('Backend unavailable — showing mock data', isDark),
                  data: (s) {
                    final cards = <Widget>[
                      _AdaptiveStatCard(
                        label: 'Active Cameras',
                        value: '${s['activeCameras'] ?? s['active_cameras'] ?? '--'}/${s['totalCameras'] ?? s['total_cameras'] ?? '--'}',
                        icon: Icons.videocam_rounded,
                        accent: primary,
                        sub: '${s['offlineCameras'] ?? s['offline_cameras'] ?? 0} offline',
                        isDark: isDark,
                      ),
                      _AdaptiveStatCard(
                        label: 'Present Today',
                        value: '${s['presentToday'] ?? s['present_today'] ?? s['attendance_records'] ?? '--'}',
                        icon: Icons.how_to_reg_rounded,
                        accent: isDark ? AppColors.success : LightColors.success,
                        sub: 'AI-confirmed',
                        isDark: isDark,
                      ),
                      _AdaptiveStatCard(
                        label: 'Absent',
                        value: '${s['absentToday'] ?? s['absent_today'] ?? s['absent'] ?? 0}',
                        icon: Icons.cancel_rounded,
                        accent: isDark ? AppColors.error : LightColors.error,
                        sub: 'Not verified',
                        isDark: isDark,
                      ),
                    ];
                    if (isDesktop) {
                      return Row(
                        children: cards.expand((c) => [Expanded(child: c), const SizedBox(width: 12)]).toList()..removeLast(),
                      );
                    }
                    return Column(children: [
                      Row(children: [
                        Expanded(child: cards[0]),
                        const SizedBox(width: 12),
                        Expanded(child: cards[1]),
                      ]),
                      const SizedBox(height: 12),
                      Row(children: [
                        Expanded(child: cards[2]),
                      ]),
                    ]);
                  },
                ),
                const SizedBox(height: 30),

                // ── Live feeds section ─────────────────────────────────────────
                Row(children: [
                  Text(
                    'Live Feeds',
                    style: TextStyle(
                      color: textPrim,
                      fontSize: 17,
                      fontWeight: FontWeight.w800,
                      letterSpacing: -0.3,
                    ),
                  ),
                  const SizedBox(width: 10),
                  cameras.when(
                    loading: () => const SizedBox(),
                    error:   (_, _) => const SizedBox(),
                    data: (cams) => Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: primary.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: primary.withValues(alpha: 0.2)),
                      ),
                      child: Text(
                        '${cams.length} cameras',
                        style: TextStyle(color: primary, fontSize: 11, fontWeight: FontWeight.w700),
                      ),
                    ),
                  ),
                  const Spacer(),
                  SizedBox(
                    width: 220,
                    child: TextField(
                      onChanged: (v) => ref.read(cameraSearchQueryProvider.notifier).state = v,
                      style: TextStyle(color: textPrim, fontSize: 13),
                      decoration: const InputDecoration(
                        hintText: 'Search cameras…',
                        prefixIcon: Icon(Icons.search_rounded, size: 17),
                      ),
                    ),
                  ),
                ]),
                const SizedBox(height: 16),

                // ── Camera grid ────────────────────────────────────────────────
                cameras.when(
                  loading: () => GridView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                        crossAxisCount: isDesktop ? 4 : 2,
                        childAspectRatio: 16 / 10,
                        mainAxisSpacing: 12,
                        crossAxisSpacing: 12),
                    itemCount: 8,
                    itemBuilder: (_, _) => _shimmerCard(isDark),
                  ),
                  error: (e, _) => EmptyState(
                      icon: Icons.videocam_off_rounded,
                      title: 'No cameras loaded',
                      subtitle: e.toString()),
                  data: (cams) {
                    if (cams.isEmpty) {
                      return const EmptyState(
                          icon: Icons.videocam_off_rounded,
                          title: 'No cameras found',
                          subtitle: 'Add cameras from Camera Config');
                    }
                    final cols = isDesktop ? 4 : ResponsiveLayout.isTablet(context) ? 3 : 2;
                    return GridView.builder(
                      shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                          crossAxisCount: cols,
                          childAspectRatio: 16 / 10,
                          mainAxisSpacing: 12,
                          crossAxisSpacing: 12),
                      itemCount: cams.length,
                      itemBuilder: (ctx, i) => _CameraCard(
                          cam: cams[i], isDark: isDark),
                    );
                  },
                ),
                const SizedBox(height: 30),

                // ── Bottom panels ──────────────────────────────────────────────
                // (Removed as requested by the user)
                const SizedBox(height: 28),
              ]),
            ),
          ]),
        ),
      ),
    );
  }

  Future<void> _toggleAi(BuildContext context, WidgetRef ref, bool currentlyActive) async {
    try {
      if (currentlyActive) {
        await ApiService.instance.stopSystemAi();
      } else {
        await ApiService.instance.startSystemAi();
      }
      ref.invalidate(systemAiStatusProvider);
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(currentlyActive ? 'AI System Stopped' : 'AI System Started'),
        backgroundColor: currentlyActive ? AppColors.error : AppColors.success,
      ));
    } catch (e) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Action failed: $e'), backgroundColor: AppColors.error));
    }
  }

  Widget _shimmerRow(int n, bool isDark) {
    final col = isDark ? AppColors.surfaceCard : LightColors.surfaceCard;
    final bdr = isDark ? AppColors.border      : LightColors.border;
    return Row(
      children: List.generate(n, (i) => Expanded(
        child: Container(
          height: 110,
          margin: EdgeInsets.only(right: i < n - 1 ? 12 : 0),
          decoration: BoxDecoration(
            color: col,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: bdr),
          ),
          child: Center(child: SizedBox(
            width: 18, height: 18,
            child: CircularProgressIndicator(
              strokeWidth: 1.5,
              color: isDark ? AppColors.primary : LightColors.primary,
            ),
          )),
        ),
      )),
    );
  }

  Widget _shimmerCard(bool isDark) => Container(
    decoration: BoxDecoration(
      color: isDark ? AppColors.surfaceCard : LightColors.surfaceCard,
      borderRadius: BorderRadius.circular(16),
      border: Border.all(color: isDark ? AppColors.border : LightColors.border),
    ),
  );

  Widget _warnBanner(String msg, bool isDark) => Container(
    margin: const EdgeInsets.only(bottom: 12),
    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
    decoration: BoxDecoration(
      color: isDark ? AppColors.warningBg : LightColors.warningBg,
      borderRadius: BorderRadius.circular(10),
      border: Border.all(
          color: (isDark ? AppColors.warning : LightColors.warning).withValues(alpha: 0.35)),
    ),
    child: Row(children: [
      Icon(Icons.info_outline_rounded,
          color: isDark ? AppColors.warning : LightColors.warning, size: 15),
      const SizedBox(width: 8),
      Expanded(
        child: Text(msg,
            style: TextStyle(
                color: isDark ? AppColors.warning : LightColors.warning, fontSize: 12)),
      ),
    ]),
  );
}

// ── AI Status pill ─────────────────────────────────────────────────────────────
class _AiStatusPill extends StatelessWidget {
  final String label;
  final Color color;
  final bool isDark;
  final bool canToggle;
  final bool isActive;
  final VoidCallback? onTap;
  const _AiStatusPill({
    required this.label,
    required this.color,
    required this.isDark,
    this.canToggle = false,
    this.isActive = false,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) => GestureDetector(
    onTap: onTap,
    child: AnimatedContainer(
      duration: const Duration(milliseconds: 300),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        // Animated pulse dot
        _PulseDot(color: color, active: isActive),
        const SizedBox(width: 7),
        Text(
          label,
          style: TextStyle(
            color: color,
            fontSize: 11,
            fontWeight: FontWeight.w800,
            letterSpacing: 1,
          ),
        ),
        if (canToggle) ...[
          const SizedBox(width: 6),
          Icon(
            isActive ? Icons.pause_circle_filled_rounded : Icons.play_circle_filled_rounded,
            color: color,
            size: 13,
          ),
        ],
      ]),
    ),
  );
}

class _PulseDot extends StatefulWidget {
  final Color color;
  final bool active;
  const _PulseDot({required this.color, required this.active});
  @override
  State<_PulseDot> createState() => _PulseDotState();
}

class _PulseDotState extends State<_PulseDot> with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(vsync: this, duration: const Duration(seconds: 2))
      ..repeat(reverse: true);
  }
  @override
  void dispose() { _ctrl.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
    animation: _ctrl,
    builder: (_, _) => Container(
      width: 7, height: 7,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: widget.active
            ? Color.lerp(widget.color, widget.color.withValues(alpha: 0.4), _ctrl.value)
            : widget.color,
        boxShadow: widget.active
            ? [BoxShadow(
                color: widget.color.withValues(alpha: 0.4 + _ctrl.value * 0.3),
                blurRadius: 6,
                spreadRadius: 1,
              )]
            : null,
      ),
    ),
  );
}

// ── Adaptive stat card ─────────────────────────────────────────────────────────
class _AdaptiveStatCard extends StatelessWidget {
  final String label, value;
  final IconData icon;
  final Color accent;
  final String? sub;
  final bool isDark;
  const _AdaptiveStatCard({
    required this.label,
    required this.value,
    required this.icon,
    required this.accent,
    required this.isDark,
    this.sub,
  });

  @override
  Widget build(BuildContext context) {
    final cardBg  = isDark ? AppColors.surfaceCard       : LightColors.surfaceCard;
    final border  = isDark ? AppColors.border            : LightColors.border;
    final textP   = isDark ? AppColors.textPrimary       : LightColors.textPrimary;
    final textM   = isDark ? AppColors.textMuted         : LightColors.textMuted;
    final shadows = isDark ? AppColors.cardShadow        : LightColors.cardShadow;

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: cardBg,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: border),
        boxShadow: shadows,
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [accent.withValues(alpha: isDark ? 0.2 : 0.12),
                         accent.withValues(alpha: isDark ? 0.05 : 0.03)],
                begin: Alignment.topLeft, end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: accent.withValues(alpha: 0.15)),
            ),
            child: Icon(icon, color: accent, size: 20),
          ),
          Container(
            width: 7, height: 7,
            decoration: BoxDecoration(
              color: accent,
              shape: BoxShape.circle,
              boxShadow: [BoxShadow(color: accent.withValues(alpha: 0.4), blurRadius: 8, spreadRadius: 1)],
            ),
          ),
        ]),
        const SizedBox(height: 18),
        Text(
          value,
          style: TextStyle(
              color: textP, fontSize: 28, fontWeight: FontWeight.w800, letterSpacing: -0.5),
        ),
        const SizedBox(height: 5),
        Text(
          label.toUpperCase(),
          style: TextStyle(color: textM, fontSize: 10, fontWeight: FontWeight.w700, letterSpacing: 1.2),
        ),
        if (sub != null) ...[
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
            decoration: BoxDecoration(
              color: accent.withValues(alpha: isDark ? 0.08 : 0.05),
              borderRadius: BorderRadius.circular(6),
            ),
            child: Text(sub!,
                style: TextStyle(color: accent.withValues(alpha: 0.85), fontSize: 10, fontWeight: FontWeight.w600)),
          ),
        ],
      ]),
    );
  }
}

// ── Camera card ────────────────────────────────────────────────────────────────
class _CameraCard extends StatelessWidget {
  final CameraModel cam;
  final bool isDark;
  const _CameraCard({required this.cam, required this.isDark});

  @override
  Widget build(BuildContext context) {
    final isOnline = cam.status == CameraStatus.online;
    final cardBg   = isDark ? AppColors.surfaceCard     : LightColors.surfaceCard;
    final border   = isDark ? AppColors.borderBright    : LightColors.borderBright;
    final textP    = isDark ? AppColors.textPrimary     : LightColors.textPrimary;
    final textM    = isDark ? AppColors.textMuted       : LightColors.textMuted;
    final success  = isDark ? AppColors.success         : LightColors.success;
    final error    = isDark ? AppColors.error           : LightColors.error;
    final teal     = isDark ? AppColors.teal            : LightColors.teal;
    final primary  = isDark ? AppColors.primary         : LightColors.primary;

    return InkWell(
      borderRadius: BorderRadius.circular(16),
      onTap: () => context.go('/cameras/${cam.id}'),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        decoration: BoxDecoration(
          color: cardBg,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: border.withValues(alpha: 0.5)),
          boxShadow: isDark
              ? AppColors.cardShadow
              : LightColors.cardShadow,
        ),
        clipBehavior: Clip.antiAlias,
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Expanded(child: Stack(children: [
            // Stream / placeholder
            Container(
              color: isDark ? const Color(0xFF080D17) : const Color(0xFFE8EFF8),
              width: double.infinity,
              child: isOnline && cam.streamUrl != null
                  ? Mjpeg(
                      isLive: true,
                      stream: cam.streamUrl!,
                      fit: BoxFit.cover,
                      error: (_, _, _) => Center(
                        child: Icon(Icons.videocam_off_rounded,
                            color: error.withValues(alpha: 0.5), size: 28),
                      ),
                    )
                  : Center(
                      child: Column(mainAxisSize: MainAxisSize.min, children: [
                        Icon(
                          isOnline ? Icons.videocam_rounded : Icons.videocam_off_rounded,
                          color: (isOnline ? primary : error).withValues(alpha: 0.35),
                          size: 30,
                        ),
                        if (!isOnline)
                          Padding(
                            padding: const EdgeInsets.only(top: 6),
                            child: Text(
                              'OFFLINE',
                              style: TextStyle(
                                color: error.withValues(alpha: 0.5),
                                fontSize: 9,
                                fontWeight: FontWeight.w800,
                                letterSpacing: 1.2,
                              ),
                            ),
                          ),
                      ]),
                    ),
            ),

            // Bottom gradient overlay
            Positioned.fill(
              child: DecoratedBox(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [Colors.transparent, Colors.black.withValues(alpha: isDark ? 0.55 : 0.35)],
                    begin: Alignment.topCenter, end: Alignment.bottomCenter,
                    stops: const [0.4, 1.0],
                  ),
                ),
              ),
            ),

            // Top-right badge
            Positioned(
              top: 8, right: 8,
              child: _Badge(
                label: isOnline ? 'LIVE' : 'OFF',
                color: isOnline ? success : error,
              ),
            ),

            // AI badge
            if (cam.isAiActive)
              Positioned(
                top: 8, left: 8,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
                  decoration: BoxDecoration(
                    color: teal,
                    borderRadius: BorderRadius.circular(4),
                    boxShadow: [BoxShadow(color: teal.withValues(alpha: 0.4), blurRadius: 6)],
                  ),
                  child: const Text('AI', style: TextStyle(color: Colors.white, fontSize: 9, fontWeight: FontWeight.w900)),
                ),
              ),
          ])),

          // Info row
          Container(
            padding: const EdgeInsets.fromLTRB(10, 8, 10, 8),
            decoration: BoxDecoration(
              color: isDark ? AppColors.surfaceHighlight : LightColors.surfaceHighlight,
              border: Border(
                top: BorderSide(color: isDark ? AppColors.border : LightColors.border, width: 0.5),
              ),
            ),
            child: Row(children: [
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(
                    cam.name,
                    style: TextStyle(
                        color: textP, fontSize: 12, fontWeight: FontWeight.w700),
                    overflow: TextOverflow.ellipsis,
                  ),
                  Text(cam.location,
                      style: TextStyle(color: textM, fontSize: 10)),
                ]),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: primary.withValues(alpha: isDark ? 0.1 : 0.07),
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(color: primary.withValues(alpha: 0.15)),
                ),
                child: Text(
                  '${cam.fps} FPS',
                  style: TextStyle(color: primary, fontSize: 9.5, fontWeight: FontWeight.w800),
                ),
              ),
            ]),
          ),
        ]),
      ),
    );
  }
}

class _Badge extends StatelessWidget {
  final String label;
  final Color color;
  const _Badge({required this.label, required this.color});
  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
    decoration: BoxDecoration(
      color: color.withValues(alpha: 0.2),
      borderRadius: BorderRadius.circular(4),
      border: Border.all(color: color.withValues(alpha: 0.4)),
      boxShadow: [BoxShadow(color: color.withValues(alpha: 0.25), blurRadius: 6)],
    ),
    child: Row(mainAxisSize: MainAxisSize.min, children: [
      Container(width: 5, height: 5, decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
      const SizedBox(width: 4),
      Text(label, style: TextStyle(color: color, fontSize: 9.5, fontWeight: FontWeight.w800, letterSpacing: 0.5)),
    ]),
  );
}

// ── Watchdog Action Pill ────────────────────────────────────────────────────────
class _WatchdogPill extends StatelessWidget {
  final bool isDark;
  const _WatchdogPill({required this.isDark});

  @override
  Widget build(BuildContext context) {
    final color = isDark ? AppColors.info : LightColors.info;
    return GestureDetector(
      onTap: () {
        showDialog(
          context: context,
          builder: (ctx) => AlertDialog(
            backgroundColor: isDark ? AppColors.surfaceCard : LightColors.surfaceCard,
            title: Row(
              children: [
                Icon(Icons.auto_awesome_rounded, color: color),
                const SizedBox(width: 8),
                Text('AI Watchdog Engine', style: TextStyle(color: isDark ? AppColors.textPrimary : LightColors.textPrimary, fontSize: 18, fontWeight: FontWeight.bold)),
              ],
            ),
            content: Text(
              'Autonomous Watchdog is monitoring threads in the background.\n\nUnknown errors are automatically queried online (StackExchange) and resolved via the AI self-learning knowledge base.',
              style: TextStyle(color: isDark ? AppColors.textSecondary : LightColors.textSecondary, height: 1.5),
            ),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: Text('Close', style: TextStyle(color: color, fontWeight: FontWeight.bold))
              ),
            ],
          ),
        );
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: color.withValues(alpha: 0.3)),
        ),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(Icons.hub_rounded, color: color, size: 13),
          const SizedBox(width: 6),
          Text(
            'SELF-HEAL',
            style: TextStyle(color: color, fontSize: 10, fontWeight: FontWeight.w800, letterSpacing: 0.8),
          ),
        ]),
      ),
    );
  }
}

// ── Panel box ──────────────────────────────────────────────────────────────────
class _PanelBox extends StatelessWidget {
  final String title;
  final IconData icon;
  final Color accent;
  final VoidCallback onMore;
  final Widget child;
  final bool isDark;
  const _PanelBox({
    required this.title,
    required this.icon,
    required this.accent,
    required this.onMore,
    required this.child,
    required this.isDark,
  });

  @override
  Widget build(BuildContext context) {
    final cardBg  = isDark ? AppColors.surfaceCard : LightColors.surfaceCard;
    final border  = isDark ? AppColors.border      : LightColors.border;
    final textP   = isDark ? AppColors.textPrimary : LightColors.textPrimary;

    return Container(
      decoration: BoxDecoration(
        color: cardBg,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: border),
        boxShadow: isDark ? AppColors.cardShadow : LightColors.cardShadow,
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 14, 8, 12),
          child: Row(children: [
            Container(
              padding: const EdgeInsets.all(7),
              decoration: BoxDecoration(
                color: accent.withValues(alpha: isDark ? 0.12 : 0.08),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(icon, color: accent, size: 15),
            ),
            const SizedBox(width: 10),
            Text(title,
                style: TextStyle(
                    color: textP, fontSize: 13, fontWeight: FontWeight.w700)),
            const Spacer(),
            TextButton(
              onPressed: onMore,
              child: Text('View all',
                  style: TextStyle(fontSize: 11, color: accent)),
            ),
          ]),
        ),
        Divider(height: 1, color: border),
        child,
      ]),
    );
  }
}

// ── Anomaly row ────────────────────────────────────────────────────────────────
class _AnomalyRow extends StatelessWidget {
  final Map a;
  final bool isDark;
  const _AnomalyRow({required this.a, required this.isDark});

  @override
  Widget build(BuildContext context) {
    final sev = a['severity'] as String? ?? 'low';
    final col = sev == 'critical'
        ? (isDark ? AppColors.error   : LightColors.error)
        : sev == 'high'
            ? (isDark ? AppColors.warning : LightColors.warning)
            : (isDark ? AppColors.info    : LightColors.info);
    final textP = isDark ? AppColors.textPrimary  : LightColors.textPrimary;
    final textS = isDark ? AppColors.textSecondary : LightColors.textSecondary;
    final bg    = isDark ? AppColors.background.withValues(alpha: 0.3) : LightColors.surfaceHighlight;

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: bg, borderRadius: BorderRadius.circular(10),
      ),
      child: Row(children: [
        Container(
          width: 3, height: 32,
          decoration: BoxDecoration(color: col, borderRadius: BorderRadius.circular(2)),
        ),
        const SizedBox(width: 12),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(
            (a['anomaly_type'] ?? '').toString().replaceAll('_', ' ').toUpperCase(),
            style: TextStyle(color: textP, fontSize: 11, fontWeight: FontWeight.w800, letterSpacing: 0.5),
          ),
          Text(
            a['description']?.toString() ?? '',
            style: TextStyle(color: textS, fontSize: 11),
            maxLines: 1, overflow: TextOverflow.ellipsis,
          ),
        ])),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
          decoration: BoxDecoration(
            color: col.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(4),
            border: Border.all(color: col.withValues(alpha: 0.25)),
          ),
          child: Text(sev.toUpperCase(),
              style: TextStyle(color: col, fontSize: 10, fontWeight: FontWeight.w800)),
        ),
      ]),
    );
  }
}

// ── AL sample row ──────────────────────────────────────────────────────────────
class _AlRow extends StatelessWidget {
  final Map s;
  final bool isDark;
  const _AlRow({required this.s, required this.isDark});

  @override
  Widget build(BuildContext context) {
    final unc   = (s['uncertainty_score'] as num? ?? 0).toDouble();
    final purple = isDark ? AppColors.purple : LightColors.purple;
    final textP  = isDark ? AppColors.textPrimary  : LightColors.textPrimary;
    final textM  = isDark ? AppColors.textMuted     : LightColors.textMuted;
    final bg     = isDark ? AppColors.background.withValues(alpha: 0.3) : LightColors.surfaceHighlight;

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(10)),
      child: Row(children: [
        Container(
          padding: const EdgeInsets.all(7),
          decoration: BoxDecoration(
            color: purple.withValues(alpha: isDark ? 0.1 : 0.07),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(Icons.psychology_rounded, color: purple, size: 16),
        ),
        const SizedBox(width: 12),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('CAM-0${s['camera_id'] ?? 'X'}',
              style: TextStyle(color: textP, fontSize: 12, fontWeight: FontWeight.w700)),
          Text('UNCERTAINTY ${(unc * 100).toStringAsFixed(0)}%',
              style: TextStyle(color: textM, fontSize: 10, fontWeight: FontWeight.w600)),
        ])),
        Icon(Icons.chevron_right_rounded, color: textM, size: 18),
      ]),
    );
  }
}
