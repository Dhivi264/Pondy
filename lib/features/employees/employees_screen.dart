import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/ui_kit.dart';
import '../../data/providers/app_providers.dart';
import '../../data/models/models.dart';
import '../../data/services/api_service.dart';

class EmployeesScreen extends ConsumerStatefulWidget {
  const EmployeesScreen({super.key});
  @override
  ConsumerState<EmployeesScreen> createState() => _EmployeesScreenState();
}

class _EmployeesScreenState extends ConsumerState<EmployeesScreen> {
  String _dept = 'all';
  final _depts = ['all', 'IT', 'HR', 'Security', 'Operations', 'Finance'];

  @override
  Widget build(BuildContext context) {
    final employees = ref.watch(employeesProvider);
    final isDark = Theme.of(context).brightness == Brightness.dark;
    
    final background = isDark ? AppColors.background : LightColors.background;
    final textPrimary = isDark ? AppColors.textPrimary : LightColors.textPrimary;
    final surfaceCard = isDark ? AppColors.surfaceCard : LightColors.surfaceCard;
    final border = isDark ? AppColors.border : LightColors.border;
    final primary = isDark ? AppColors.primary : LightColors.primary;
    final success = isDark ? AppColors.success : LightColors.success;
    final warning = isDark ? AppColors.warning : LightColors.warning;
    final teal = isDark ? AppColors.teal : LightColors.teal;
    final textMuted = isDark ? AppColors.textMuted : LightColors.textMuted;
    final surfaceHighlight = isDark ? AppColors.surfaceHighlight : LightColors.surfaceHighlight;
    final textSecondary = isDark ? AppColors.textSecondary : LightColors.textSecondary;
    final error = isDark ? AppColors.error : LightColors.error;

    return Scaffold(
      backgroundColor: background,
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          // Header
          Row(children: [
            Text('Personnel Database', style: TextStyle(color: textPrimary, fontSize: 22, fontWeight: FontWeight.w800)),
            const Spacer(),
            ElevatedButton.icon(
              onPressed: () => context.go('/employees/add'),
              icon: const Icon(Icons.person_add_rounded, size: 16),
              label: const Text('Add Employee'),
            ),
          ]),
          const SizedBox(height: 20),

          // Stats row
          employees.when(
            loading: () => const SizedBox.shrink(),
            error: (_, _) => const SizedBox.shrink(),
            data: (emps) {
              final faceReg = emps.where((e) => e.hasRegisteredFace).length;
              return Row(children: [
                _QuickStat(label: 'Total', value: '${emps.length}', icon: Icons.people_rounded, color: primary, isDark: isDark),
                const SizedBox(width: 12),
                _QuickStat(label: 'Face Registered', value: '$faceReg', icon: Icons.face_rounded, color: success, isDark: isDark),
                const SizedBox(width: 12),
                _QuickStat(label: 'Pending', value: '${emps.length - faceReg}', icon: Icons.face_retouching_off_rounded, color: warning, isDark: isDark),
              ]);
            },
          ),
          const SizedBox(height: 16),

          // Toolbar
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(color: surfaceCard, borderRadius: BorderRadius.circular(10), border: Border.all(color: border)),
            child: Row(children: [
              SearchField(hint: 'Search by name or ID…', onChanged: (v) => ref.read(employeeSearchQueryProvider.notifier).state = v, width: 240),
              const SizedBox(width: 12),
              // Department filter
              ..._depts.map((d) => Padding(padding: const EdgeInsets.only(right: 6),
                child: GestureDetector(
                  onTap: () => setState(() => _dept = d),
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 150),
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                    decoration: BoxDecoration(
                      color: _dept == d ? teal.withValues(alpha: 0.15) : Colors.transparent,
                      borderRadius: BorderRadius.circular(6),
                      border: _dept == d ? Border.all(color: teal.withValues(alpha: 0.4)) : Border.all(color: Colors.transparent),
                    ),
                    child: Text(d == 'all' ? 'All Depts' : d, style: TextStyle(color: _dept == d ? teal : textMuted, fontSize: 12, fontWeight: _dept == d ? FontWeight.w700 : FontWeight.w500)),
                  ),
                ))),
              const Spacer(),
              IconButton(icon: Icon(Icons.refresh_rounded, size: 18, color: textMuted),
                onPressed: () => ref.invalidate(employeesProvider), tooltip: 'Refresh'),
            ]),
          ),
          const SizedBox(height: 16),

          // Table
          Expanded(child: Container(
            decoration: BoxDecoration(color: surfaceCard, borderRadius: BorderRadius.circular(12), border: Border.all(color: border)),
            child: Column(children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                decoration: BoxDecoration(border: Border(bottom: BorderSide(color: border))),
                child: Row(children: const [
                  ThCell('EMP ID', flex: 2), ThCell('NAME', flex: 3), ThCell('DEPARTMENT', flex: 2),
                  ThCell('ROLE', flex: 2), ThCell('FACE STATUS', flex: 2), ThCell('ADDED', flex: 2), ThCell('', flex: 1),
                ]),
              ),
              Expanded(child: employees.when(
                loading: () => const ScreenLoader(message: 'Loading employees…'),
                error: (e, _) => ErrorState(message: 'Failed to load employees', onRetry: () => ref.invalidate(employeesProvider)),
                data: (emps) {
                  var filtered = _dept == 'all' ? emps : emps.where((e) => e.department == _dept).toList();
                  if (filtered.isEmpty) return const EmptyState(icon: Icons.person_off_outlined, title: 'No employees found');
                  return ListView.builder(
                    padding: EdgeInsets.zero,
                    itemCount: filtered.length,
                    itemBuilder: (ctx, i) {
                      final e = filtered[i];
                      return TrRow(
                        onTap: () => context.go('/employees/${e.id}'),
                        cells: [
                          Expanded(flex:2, child: Text(e.empId, style: TextStyle(color: primary, fontSize: 12.5, fontWeight: FontWeight.w600, fontFamily: 'monospace'))),
                          Expanded(flex:3, child: Row(children: [
                            CircleAvatar(radius: 15, backgroundColor: surfaceHighlight,
                              child: Text(e.name.isNotEmpty ? e.name[0] : '?', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: teal))),
                            const SizedBox(width: 10),
                            Expanded(child: Text(e.name, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13.5), overflow: TextOverflow.ellipsis)),
                          ])),
                          Expanded(flex:2, child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                            decoration: BoxDecoration(color: surfaceHighlight, borderRadius: BorderRadius.circular(4)),
                            child: Text(e.department, style: TextStyle(color: textSecondary, fontSize: 12)),
                          )),
                          Expanded(flex:2, child: Text(e.designation, style: TextStyle(color: textSecondary, fontSize: 13))),
                          Expanded(flex:2, child: e.hasRegisteredFace
                            ? StatusBadge('ENROLLED', color: success)
                            : StatusBadge('PENDING', color: warning)),
                          Expanded(flex:2, child: Text(DateFormat('MMM dd, yyyy').format(e.dateAdded), style: TextStyle(color: textMuted, fontSize: 12))),
                          Expanded(flex:1, child: Row(mainAxisSize: MainAxisSize.min, children: [
                            SizedBox(width: 28, height: 28, child: IconButton(padding: EdgeInsets.zero, icon: Icon(Icons.visibility_rounded, size: 15, color: textMuted), onPressed: () => context.go('/employees/${e.id}'))),
                            SizedBox(width: 28, height: 28, child: IconButton(padding: EdgeInsets.zero, icon: Icon(Icons.delete_rounded, size: 15, color: error),
                              onPressed: () => _confirmDelete(ctx, e, surfaceCard, textPrimary, textSecondary, error))),
                          ])),
                        ],
                      );
                    },
                  );
                },
              )),
            ]),
          )),
        ]),
      ),
    );
  }

  Future<void> _confirmDelete(BuildContext ctx, EmployeeModel e, Color bg, Color textPrimary, Color textSecondary, Color error) async {
    final ok = await showDialog<bool>(
      context: ctx,
      builder: (dialogCtx) => AlertDialog(
        backgroundColor: bg,
        title: Text('Delete Employee', style: TextStyle(color: textPrimary)),
        content: Text('Remove ${e.name} (${e.empId}) from the system?', style: TextStyle(color: textSecondary)),
        actions: [
          TextButton(onPressed: () => Navigator.pop(dialogCtx, false), child: const Text('Cancel')),
          ElevatedButton(onPressed: () => Navigator.pop(dialogCtx, true),
            style: ElevatedButton.styleFrom(backgroundColor: error),
            child: const Text('Delete')),
        ],
      ),
    );
    if (ok == true) {
      await ApiService.instance.deleteEmployee(e.id);
      ref.invalidate(employeesProvider);
    }
  }
}

class _QuickStat extends StatelessWidget {
  final String label, value;
  final IconData icon;
  final Color color;
  final bool isDark;
  const _QuickStat({required this.label, required this.value, required this.icon, required this.color, required this.isDark});
  @override
  Widget build(BuildContext context) {
    final surfaceCard = isDark ? AppColors.surfaceCard : LightColors.surfaceCard;
    final border = isDark ? AppColors.border : LightColors.border;
    final textMuted = isDark ? AppColors.textMuted : LightColors.textMuted;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      decoration: BoxDecoration(color: surfaceCard, borderRadius: BorderRadius.circular(10), border: Border.all(color: border)),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(icon, color: color, size: 18),
        const SizedBox(width: 10),
        Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
          Text(value, style: TextStyle(color: color, fontSize: 18, fontWeight: FontWeight.w800)),
          Text(label, style: TextStyle(color: textMuted, fontSize: 11)),
        ]),
      ]),
    );
  }
}
