/// Export service — generates CSV and plain-text reports for attendance data.
/// PDF export requires the 'pdf' package; this version uses CSV which works
/// with the existing http package and can be opened in Excel/Sheets.
library;

import 'dart:convert';
import 'package:intl/intl.dart';
import '../../data/models/models.dart';

class ExportService {
  ExportService._();
  static final instance = ExportService._();

  // ── CSV ──────────────────────────────────────────────────────────────────────
  String buildAttendanceCsv(List<AttendanceModel> records) {
    final fmt = DateFormat('yyyy-MM-dd');
    final tfmt = DateFormat('HH:mm');

    final sb = StringBuffer();
    sb.writeln('Employee ID,Name,Date,Check In,Check Out,Duration (h),Status,AI Confidence');

    for (final r in records) {
      final dur = (r.checkInTime != null && r.checkOutTime != null)
          ? r.checkOutTime!.difference(r.checkInTime!).inMinutes / 60.0
          : 0.0;
      sb.writeln([
        r.employeeId,
        r.employeeName,
        fmt.format(r.date),
        r.checkInTime != null ? tfmt.format(r.checkInTime!) : '',
        r.checkOutTime != null ? tfmt.format(r.checkOutTime!) : '',
        dur > 0 ? dur.toStringAsFixed(2) : '',
        r.status.name,
        (r.confidenceScore * 100).toStringAsFixed(1),
      ].map(_escape).join(','));
    }
    return sb.toString();
  }

  // ── Summary text ──────────────────────────────────────────────────────────────
  String buildAttendanceSummary(List<AttendanceModel> records) {
    final present = records.where((r) => r.status == AttendanceStatus.present).length;
    final late    = records.where((r) => r.status == AttendanceStatus.late).length;
    final absent  = records.where((r) => r.status == AttendanceStatus.absent).length;
    final total   = records.length;
    final avgConf = total > 0
        ? records.map((r) => r.confidenceScore).reduce((a, b) => a + b) / total
        : 0.0;
    final date = DateFormat('EEEE, MMMM d, yyyy').format(DateTime.now());

    return '''
SecureVision LMP-TX — Attendance Report
Generated: $date
────────────────────────────────────────
Total Records : $total
Present       : $present (${_pct(present, total)})
Late          : $late (${_pct(late, total)})
Absent        : $absent (${_pct(absent, total)})
AI Confidence : ${(avgConf * 100).toStringAsFixed(1)}% avg
────────────────────────────────────────
''';
  }

  // Encode CSV cell
  String _escape(String s) =>
      s.contains(',') || s.contains('"') || s.contains('\n')
          ? '"${s.replaceAll('"', '""')}"'
          : s;

  String _pct(int part, int total) =>
      total == 0 ? '0%' : '${(part / total * 100).toStringAsFixed(0)}%';

  // Encode to data URI for web download
  String toCsvDataUri(String csv) {
    final bytes  = utf8.encode(csv);
    final b64    = base64Encode(bytes);
    return 'data:text/csv;base64,$b64';
  }
}
