import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/ui_kit.dart';
import '../../data/providers/app_providers.dart';
import '../../data/services/api_service.dart';
import '../../data/models/models.dart';

class EmployeeDetailScreen extends ConsumerWidget {
  final String employeeId;
  const EmployeeDetailScreen({super.key, required this.employeeId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final employees = ref.watch(employeesProvider);
    final attendancesAsync = ref.watch(attendanceProvider);

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.surface,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_rounded, color: AppColors.textPrimary),
          onPressed: () => context.go('/employees'),
        ),
        title: const Text('Employee Profile',
            style: TextStyle(color: AppColors.textPrimary, fontWeight: FontWeight.w700)),
        actions: [
          IconButton(
            icon: const Icon(Icons.delete_outline_rounded, color: AppColors.error),
            tooltip: 'Delete Employee',
            onPressed: () async {
              final ok = await showDialog<bool>(
                context: context,
                builder: (dialogCtx) => AlertDialog(
                  backgroundColor: AppColors.surfaceCard,
                  title: const Text('Delete Employee',
                      style: TextStyle(color: AppColors.textPrimary)),
                  content: Text('Remove employee $employeeId from the system?',
                      style: const TextStyle(color: AppColors.textSecondary)),
                  actions: [
                    TextButton(onPressed: () => Navigator.pop(dialogCtx, false), child: const Text('Cancel')),
                    ElevatedButton(
                      onPressed: () => Navigator.pop(dialogCtx, true),
                      style: ElevatedButton.styleFrom(backgroundColor: AppColors.error),
                      child: const Text('Delete'),
                    ),
                  ],
                ),
              );
              if (ok == true && context.mounted) {
                await ApiService.instance.deleteEmployee(employeeId);
                ref.invalidate(employeesProvider);
                if (context.mounted) context.go('/employees');
              }
            },
          ),
          const SizedBox(width: 8),
        ],
        bottom: PreferredSize(preferredSize: const Size.fromHeight(1),
            child: Container(height: 1, color: AppColors.border)),
      ),
      body: employees.when(
        loading: () => const ScreenLoader(message: 'Loading employee data…'),
        error: (e, _) => ErrorState(message: 'Failed to load: $e',
            onRetry: () => ref.invalidate(employeesProvider)),
        data: (emps) {
          final emp = emps.firstWhere(
            (e) => e.id == employeeId || e.empId == employeeId,
            orElse: () => emps.isEmpty ? emps.first : emps.first,
          );
          return SingleChildScrollView(
            padding: const EdgeInsets.all(28),
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              // Profile card
              SizedBox(width: 280, child: Container(
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(color: AppColors.surfaceCard,
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: AppColors.border)),
                child: Column(children: [
                  Container(
                    width: 80, height: 80,
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                          colors: [AppColors.primary, AppColors.teal]),
                      shape: BoxShape.circle,
                    ),
                    child: Center(child: Text(
                      emp.name.isNotEmpty ? emp.name[0] : '?',
                      style: const TextStyle(color: Colors.white, fontSize: 32, fontWeight: FontWeight.w800),
                    )),
                  ),
                  const SizedBox(height: 16),
                  Text(emp.name, style: const TextStyle(color: AppColors.textPrimary,
                      fontSize: 18, fontWeight: FontWeight.w800)),
                  const SizedBox(height: 4),
                  Text(emp.designation, style: const TextStyle(color: AppColors.textMuted, fontSize: 13)),
                  const SizedBox(height: 16),
                  emp.hasRegisteredFace
                      ? const StatusBadge('FACE ENROLLED', color: AppColors.success)
                      : const StatusBadge('NO FACE DATA', color: AppColors.warning),
                  const SizedBox(height: 20),
                  const Divider(color: AppColors.border),
                  const SizedBox(height: 12),
                  _row(Icons.badge_rounded, 'Employee ID', emp.empId, AppColors.primary),
                  _row(Icons.business_rounded, 'Department', emp.department, AppColors.teal),
                  _row(Icons.work_rounded, 'Role', emp.designation, AppColors.textSecondary),
                  _row(Icons.calendar_today_rounded, 'Joined',
                      DateFormat('MMM dd, yyyy').format(emp.dateAdded), AppColors.textSecondary),
                ]),
              )),
              const SizedBox(width: 24),
              // Details column
              Expanded(child: Column(children: [
                _infoCard('Contact Information', [
                  _row(Icons.email_rounded, 'Email', emp.email.isNotEmpty ? emp.email : '—', AppColors.textSecondary),
                  _row(Icons.phone_rounded, 'Phone', emp.phone.isNotEmpty ? emp.phone : '—', AppColors.textSecondary),
                ]),
                const SizedBox(height: 16),
                _infoCard('Attendance Today', [
                  attendancesAsync.when(
                    data: (atts) {
                      final today = DateTime.now();
                      final todayAtt = atts.where((a) => (a.employeeId == emp.empId || a.employeeId == emp.id) && a.date.year == today.year && a.date.month == today.month && a.date.day == today.day).toList();
                      if (todayAtt.isEmpty) {
                        return Center(
                          child: Padding(
                            padding: const EdgeInsets.symmetric(vertical: 8),
                            child: const StatusBadge('ABSENT', color: AppColors.error),
                          ),
                        );
                      }
                      final att = todayAtt.last;
                      final checkIn = att.checkInTime != null ? DateFormat('hh:mm a').format(att.checkInTime!) : '—';
                      final checkOut = att.checkOutTime != null ? DateFormat('hh:mm a').format(att.checkOutTime!) : '—';
                      
                      return Column(
                        children: [
                          Row(children: [
                            const Icon(Icons.schedule_rounded, color: AppColors.textMuted, size: 16),
                            const SizedBox(width: 8),
                            const Text('Check-in: ', style: TextStyle(color: AppColors.textMuted, fontSize: 13)),
                            Text(checkIn, style: const TextStyle(color: AppColors.textPrimary, fontWeight: FontWeight.w600, fontSize: 13)),
                            const SizedBox(width: 24),
                            const Icon(Icons.logout_rounded, color: AppColors.textMuted, size: 16),
                            const SizedBox(width: 8),
                            const Text('Check-out: ', style: TextStyle(color: AppColors.textMuted, fontSize: 13)),
                            Text(checkOut, style: const TextStyle(color: AppColors.textSecondary, fontSize: 13)),
                          ]),
                          const SizedBox(height: 8),
                          Row(children: [
                            StatusBadge(
                              att.status == AttendanceStatus.present ? 'PRESENT' : 'LATE', 
                              color: att.status == AttendanceStatus.present ? AppColors.success : AppColors.warning
                            ),
                            const SizedBox(width: 10),
                            Text('Confidence: ${(att.confidenceScore * 100).toStringAsFixed(0)}%',
                                style: const TextStyle(color: AppColors.textMuted, fontSize: 12)),
                          ]),
                        ],
                      );
                    },
                    loading: () => const Center(child: CircularProgressIndicator()),
                    error: (e, _) => const Text('Failed to load attendance', style: TextStyle(color: AppColors.error)),
                  ),
                ]),
                const SizedBox(height: 16),
                _infoCard('AI Metrics', [
                  const InfoRow('Face Recognition Confidence', '91.4%', valueColor: AppColors.success),
                  const Divider(color: AppColors.border, height: 16),
                  const InfoRow('Presence Rate (30d)', '87%'),
                  const Divider(color: AppColors.border, height: 16),
                  const InfoRow('Punctuality Rate', '78%', valueColor: AppColors.warning),
                  const Divider(color: AppColors.border, height: 16),
                  const InfoRow('Risk Flag', 'None', valueColor: AppColors.success),
                ]),
              ])),
            ]),
          );
        },
      ),
    );
  }

  Widget _row(IconData icon, String label, String value, Color valueColor) =>
    Padding(padding: const EdgeInsets.symmetric(vertical: 6), child: Row(children: [
      Icon(icon, size: 15, color: AppColors.textMuted),
      const SizedBox(width: 8),
      Text('$label: ', style: const TextStyle(color: AppColors.textMuted, fontSize: 12)),
      Expanded(child: Text(value, style: TextStyle(color: valueColor, fontSize: 12,
          fontWeight: FontWeight.w600), overflow: TextOverflow.ellipsis)),
    ]));

  Widget _infoCard(String title, List<Widget> children) => Container(
    width: double.infinity, padding: const EdgeInsets.all(20),
    decoration: BoxDecoration(color: AppColors.surfaceCard,
        borderRadius: BorderRadius.circular(12), border: Border.all(color: AppColors.border)),
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(title, style: const TextStyle(color: AppColors.textPrimary, fontSize: 14, fontWeight: FontWeight.w700)),
      const SizedBox(height: 14),
      ...children,
    ]),
  );
}
