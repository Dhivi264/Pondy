import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/ui_kit.dart';
import '../../core/responsive/responsive_layout.dart';
import '../../data/providers/app_providers.dart';
import '../../data/models/models.dart';

class AttendanceScreen extends ConsumerStatefulWidget {
  const AttendanceScreen({super.key});
  @override
  ConsumerState<AttendanceScreen> createState() => _AttendanceScreenState();
}

class _AttendanceScreenState extends ConsumerState<AttendanceScreen> {
  String _search = '';
  String _filterStatus = 'All';
  static const _statusOptions = ['All', 'Present', 'Late', 'Absent'];

  @override
  Widget build(BuildContext context) {
    final stats      = ref.watch(attendanceStatsProvider);
    final attendance = ref.watch(attendanceProvider);
    final employees  = ref.watch(employeesProvider).valueOrNull ?? [];
    final isDesktop  = ResponsiveLayout.isDesktop(context);
    final isDark     = Theme.of(context).brightness == Brightness.dark;

    final background = isDark ? AppColors.background : LightColors.background;
    final textPrimary = isDark ? AppColors.textPrimary : LightColors.textPrimary;
    final primary = isDark ? AppColors.primary : LightColors.primary;
    final success = isDark ? AppColors.success : LightColors.success;
    final warning = isDark ? AppColors.warning : LightColors.warning;
    final error = isDark ? AppColors.error : LightColors.error;
    final surfaceCard = isDark ? AppColors.surfaceCard : LightColors.surfaceCard;
    final border = isDark ? AppColors.border : LightColors.border;
    final textSecondary = isDark ? AppColors.textSecondary : LightColors.textSecondary;
    final surfaceHighlight = isDark ? AppColors.surfaceHighlight : LightColors.surfaceHighlight;
    final textMuted = isDark ? AppColors.textMuted : LightColors.textMuted;

    return Scaffold(
      backgroundColor: background,
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(attendanceProvider);
          ref.invalidate(attendanceStatsProvider);
        },
        color: primary,
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: EdgeInsets.all(isDesktop ? 28 : 16),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [

            // Header
            Row(children: [
              Text('Attendance Report', style: TextStyle(color: textPrimary, fontSize: 22, fontWeight: FontWeight.w800)),
              const Spacer(),
              OutlinedButton.icon(
                onPressed: () {
                  ref.invalidate(attendanceProvider);
                  ref.invalidate(attendanceStatsProvider);
                },
                icon: const Icon(Icons.refresh_rounded, size: 15),
                label: const Text('Refresh'),
              ),
              const SizedBox(width: 10),
              ElevatedButton.icon(
                onPressed: () {},
                icon: const Icon(Icons.download_rounded, size: 15),
                label: const Text('Export CSV'),
              ),
            ]),
            const SizedBox(height: 24),

            // Stat cards
            stats.when(
              loading: () => SizedBox(height: 100, child: Row(children: List.generate(4, (i) => Expanded(child: Container(
                height: 100, margin: EdgeInsets.only(right: i < 3 ? 12 : 0),
                decoration: BoxDecoration(color: surfaceCard, borderRadius: BorderRadius.circular(12), border: Border.all(color: border)),
                child: Center(child: SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 1.5, color: primary))),
              ))))),
              error: (_, _) => const SizedBox.shrink(),
              data: (s) {
                final total = s['totalEmployees'] ?? s['total_employees'] ?? s['total_records'] as int? ?? 0;
                final present = s['presentToday'] ?? s['present_today'] ?? s['present'] as int? ?? 0;
                final absent  = s['absentToday'] ?? s['absent_today'] ?? s['absent']  as int? ?? 0;
                final cards = [
                  StatCard(label: 'Total Employees', value: '$total',   icon: Icons.people_rounded,           accent: primary),
                  StatCard(label: 'Present',       value: '$present', icon: Icons.check_circle_rounded,     accent: success, sub: total > 0 ? '${(present / total * 100).toStringAsFixed(0)}% rate' : null),
                  StatCard(label: 'Absent',        value: '$absent',  icon: Icons.cancel_rounded,           accent: error),
                ];
                if (isDesktop) return Row(children: cards.expand((c) => [Expanded(child: c), const SizedBox(width: 12)]).toList()..removeLast());
                return Column(children: [
                  Row(children: [Expanded(child: cards[0]), const SizedBox(width: 12), Expanded(child: cards[1])]),
                  const SizedBox(height: 12),
                  Row(children: [Expanded(child: cards[2])]),
                ]);
              },
            ),
            const SizedBox(height: 24),

            // Filters
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(color: surfaceCard, borderRadius: BorderRadius.circular(10), border: Border.all(color: border)),
              child: isDesktop
                ? Row(children: [
                    Expanded(flex: 3, child: _searchField(textPrimary)),
                    const SizedBox(width: 12),
                    ..._statusOptions.map((opt) => Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: _filterChip(opt, primary, surfaceHighlight, border, textSecondary),
                    )),
                    const Spacer(),
                    _datePicker(),
                  ])
                : Column(children: [
                    _searchField(textPrimary),
                    const SizedBox(height: 10),
                    SingleChildScrollView(
                      scrollDirection: Axis.horizontal,
                      child: Row(children: _statusOptions.map((o) => Padding(padding: const EdgeInsets.only(right: 8), child: _filterChip(o, primary, surfaceHighlight, border, textSecondary))).toList()),
                    ),
                  ]),
            ),
            const SizedBox(height: 20),

            // Table
            Container(
              decoration: BoxDecoration(color: surfaceCard, borderRadius: BorderRadius.circular(12), border: Border.all(color: border)),
              child: Column(children: [
                // Table header
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  decoration: BoxDecoration(border: Border(bottom: BorderSide(color: border))),
                  child: Row(children: const [
                    ThCell('EMP ID',    flex: 2),
                    ThCell('NAME',      flex: 3),
                    ThCell('DATE',      flex: 2),
                    ThCell('CHECK IN',  flex: 2),
                    ThCell('CHECK OUT', flex: 2),
                    ThCell('HOURS',     flex: 1),
                    ThCell('STATUS',    flex: 2),
                    ThCell('CONFIDENCE',flex: 2),
                  ]),
                ),

                // Rows
                attendance.when(
                  loading: () => const SizedBox(height: 200, child: ScreenLoader(message: 'Loading attendance records…')),
                  error: (e, _) => SizedBox(height: 200, child: ErrorState(message: 'Failed to load: $e', onRetry: () => ref.invalidate(attendanceProvider))),
                  data: (rows) {
                    final filtered = rows.where((r) {
                      final matchSearch = _search.isEmpty || r.employeeName.toLowerCase().contains(_search.toLowerCase()) || r.employeeId.toLowerCase().contains(_search.toLowerCase());
                      final matchStatus = _filterStatus == 'All' ||
                        (_filterStatus == 'Present' && r.status == AttendanceStatus.present) ||
                        (_filterStatus == 'Late'    && r.status == AttendanceStatus.late)    ||
                        (_filterStatus == 'Absent'  && r.status == AttendanceStatus.absent);
                      return matchSearch && matchStatus;
                    }).toList();

                    if (filtered.isEmpty) {
                      return const SizedBox(height: 160, child: EmptyState(icon: Icons.search_off_rounded, title: 'No records match your filter'));
                    }

                    return Column(children: filtered.take(50).map((r) {
                      EmployeeModel? emp;
                      try {
                        emp = employees.firstWhere((e) => e.id == r.employeeId || e.empId == r.employeeId);
                      } catch (_) {}
                      
                      final dName = emp?.name ?? (r.employeeName == r.employeeId ? 'Unknown' : r.employeeName);
                      final dId = emp?.empId ?? r.employeeId;

                      final statusColor = r.status == AttendanceStatus.present ? success
                        : r.status == AttendanceStatus.late ? warning : error;
                      final statusLabel = r.status == AttendanceStatus.present ? 'Present'
                        : r.status == AttendanceStatus.late ? 'Late' : 'Absent';

                      String hoursStr = '--';
                      if (r.checkInTime != null && r.checkOutTime != null) {
                        final diff = r.checkOutTime!.difference(r.checkInTime!);
                        hoursStr = '${diff.inHours}h ${diff.inMinutes.remainder(60)}m';
                      }

                      return TrRow(
                        cells: [
                          Expanded(flex: 2, child: Text(dId, style: TextStyle(color: primary, fontSize: 12, fontWeight: FontWeight.w700))),
                          Expanded(flex: 3, child: Row(children: [
                            CircleAvatar(radius: 13, backgroundColor: surfaceHighlight,
                              child: Text(dName.isNotEmpty ? dName[0].toUpperCase() : '?',
                                style: TextStyle(color: textPrimary, fontSize: 11, fontWeight: FontWeight.w700))),
                            const SizedBox(width: 8),
                            Expanded(child: Text(dName, style: TextStyle(color: textPrimary, fontSize: 12, fontWeight: FontWeight.w600), overflow: TextOverflow.ellipsis)),
                          ])),
                          Expanded(flex: 2, child: Text(DateFormat('MMM d, yyyy').format(r.date), style: TextStyle(color: textSecondary, fontSize: 12))),
                          Expanded(flex: 2, child: Text(r.checkInTime != null ? DateFormat('HH:mm').format(r.checkInTime!) : '--', style: TextStyle(color: textPrimary, fontSize: 12))),
                          Expanded(flex: 2, child: Text(r.checkOutTime != null ? DateFormat('HH:mm').format(r.checkOutTime!) : '--', style: TextStyle(color: textSecondary, fontSize: 12))),
                          Expanded(flex: 1, child: Text(hoursStr, style: TextStyle(color: textSecondary, fontSize: 12))),
                          Expanded(flex: 2, child: StatusBadge(statusLabel, color: statusColor)),
                          Expanded(flex: 2, child: Row(children: [
                            Container(
                              height: 4, width: 60,
                              clipBehavior: Clip.antiAlias,
                              decoration: BoxDecoration(color: border, borderRadius: BorderRadius.circular(2)),
                              child: FractionallySizedBox(
                                alignment: Alignment.centerLeft,
                                widthFactor: r.confidenceScore,
                                child: Container(color: r.confidenceScore > 0.8 ? success : r.confidenceScore > 0.6 ? warning : error),
                              ),
                            ),
                            const SizedBox(width: 6),
                            Text('${(r.confidenceScore * 100).toStringAsFixed(0)}%', style: TextStyle(color: textMuted, fontSize: 11)),
                          ])),
                        ],
                      );
                    }).toList());
                  },
                ),
              ]),
            ),
          ]),
        ),
      ),
    );
  }

  Widget _searchField(Color textPrimary) => TextField(
    onChanged: (v) => setState(() => _search = v),
    style: TextStyle(color: textPrimary, fontSize: 13),
    decoration: const InputDecoration(hintText: 'Search by name or ID…', prefixIcon: Icon(Icons.search_rounded, size: 17)),
  );

  Widget _filterChip(String label, Color primary, Color surfaceHighlight, Color border, Color textSecondary) => GestureDetector(
    onTap: () => setState(() => _filterStatus = label),
    child: AnimatedContainer(
      duration: const Duration(milliseconds: 150),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
      decoration: BoxDecoration(
        color: _filterStatus == label ? primary.withValues(alpha: 0.15) : surfaceHighlight,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: _filterStatus == label ? primary.withValues(alpha: 0.5) : border),
      ),
      child: Text(label, style: TextStyle(color: _filterStatus == label ? primary : textSecondary, fontSize: 12, fontWeight: FontWeight.w600)),
    ),
  );

  Widget _datePicker() => OutlinedButton.icon(
    onPressed: () async {
      await showDateRangePicker(context: context, firstDate: DateTime(2024), lastDate: DateTime.now(), builder: (ctx, child) => Theme(data: Theme.of(ctx), child: child!));
    },
    icon: const Icon(Icons.calendar_today_rounded, size: 14),
    label: const Text('Date Range'),
  );
}
