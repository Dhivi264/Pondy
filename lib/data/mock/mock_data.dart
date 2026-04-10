import '../models/models.dart';
import 'dart:math';

class MockData {
  static final Random _rnd = Random(42);

  static List<CameraModel> getCameras() {
    return List.generate(32, (index) {
      final isOnline = _rnd.nextDouble() > 0.15; // 85% chance online
      return CameraModel(
        id: 'cam_${index + 1}',
        name: 'Camera ${index + 1}',
        channel: index + 1,
        status: isOnline ? CameraStatus.online : CameraStatus.offline,
        fps: isOnline ? (20 + _rnd.nextInt(11)) : 0, // 20-30 fps
        isAiActive: isOnline && _rnd.nextBool(),
        location: 'Zone ${String.fromCharCode(65 + (index % 5))}',
        isRecording: isOnline,
      );
    });
  }

  static List<EmployeeModel> getEmployees() {
    return List.generate(50, (index) {
      return EmployeeModel(
        id: 'emp_uuid_$index',
        empId: 'EMP${(index + 100).toString().padLeft(4, '0')}',
        name: 'Employee ${index + 1}',
        department: ['IT', 'HR', 'Security', 'Operations', 'Finance'][min(4, index % 5)],
        designation: ['Staff', 'Manager', 'Analyst', 'Guard'][_rnd.nextInt(4)],
        phone: '+1 555 ${_rnd.nextInt(9000) + 1000}',
        email: 'emp$index@company.com',
        hasRegisteredFace: _rnd.nextDouble() > 0.1, // 90% have faces
        dateAdded: DateTime.now().subtract(Duration(days: _rnd.nextInt(365))),
      );
    });
  }

  static List<AttendanceModel> getAttendance(List<EmployeeModel> employees) {
    final today = DateTime.now();
    return employees.map((emp) {
      final isAbsent = _rnd.nextDouble() < 0.1;
      final isLate = !isAbsent && _rnd.nextDouble() < 0.2;
      
      DateTime? checkIn;
      DateTime? checkOut;
      AttendanceStatus status = AttendanceStatus.absent;

      if (!isAbsent) {
        status = isLate ? AttendanceStatus.late : AttendanceStatus.present;
        checkIn = DateTime(today.year, today.month, today.day, 8 + (isLate ? 1 : 0), _rnd.nextInt(60));
        if (_rnd.nextBool()) {
           checkOut = checkIn.add(Duration(hours: 8, minutes: _rnd.nextInt(60)));
        }
      }

      return AttendanceModel(
        id: 'att_${emp.id}',
        employeeId: emp.empId,
        employeeName: emp.name,
        date: today,
        checkInTime: checkIn,
        checkOutTime: checkOut,
        status: status,
        confidenceScore: isAbsent ? 0.0 : 0.85 + (_rnd.nextDouble() * 0.14),
        cameraSource: 'Main Entrance Cam 1',
      );
    }).toList();
  }

  static List<ArchiveModel> getArchives() {
    return List.generate(100, (index) {
      return ArchiveModel(
        id: 'arch_$index',
        cameraId: 'cam_${(_rnd.nextInt(32) + 1)}',
        cameraName: 'Camera ${(_rnd.nextInt(32) + 1)}',
        timestamp: DateTime.now().subtract(Duration(hours: _rnd.nextInt(72), minutes: _rnd.nextInt(60))),
        durationSeconds: 10 + _rnd.nextInt(120),
        type: ArchiveType.values[_rnd.nextInt(ArchiveType.values.length)],
        description: 'Auto-recorded clip event',
      );
    });
  }

  static DashboardSummary getSummary(List<CameraModel> cams, List<AttendanceModel> atts) {
    return DashboardSummary(
      totalCameras: cams.length,
      activeCameras: cams.where((c) => c.status == CameraStatus.online).length,
      offlineCameras: cams.where((c) => c.status == CameraStatus.offline).length,
      facesDetectedToday: 423,
      attendanceMarkedToday: atts.where((a) => a.status != AttendanceStatus.absent).length,
    );
  }
}
