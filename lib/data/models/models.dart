
enum CameraStatus { online, offline }

class CameraModel {
  final String id;
  final String name;
  final int channel;
  final CameraStatus status;
  final int fps;
  final bool isAiActive;
  final String location;
  final bool isRecording;
  final String? streamUrl;

  CameraModel({
    required this.id,
    required this.name,
    required this.channel,
    required this.status,
    required this.fps,
    required this.isAiActive,
    required this.location,
    required this.isRecording,
    this.streamUrl,
  });
}

class EmployeeModel {
  final String id;
  final String empId;
  final String name;
  final String department;
  final String designation;
  final String phone;
  final String email;
  final bool hasRegisteredFace;
  final DateTime dateAdded;
  final String? lastSeenCameraId;

  EmployeeModel({
    required this.id,
    required this.empId,
    required this.name,
    required this.department,
    required this.designation,
    required this.phone,
    required this.email,
    required this.hasRegisteredFace,
    required this.dateAdded,
    this.lastSeenCameraId,
  });
}

enum AttendanceStatus { present, absent, late }

class AttendanceModel {
  final String id;
  final String employeeId;
  final String employeeName;
  final DateTime date;
  final DateTime? checkInTime;
  final DateTime? checkOutTime;
  final AttendanceStatus status;
  final double confidenceScore;
  final String cameraSource; // e.g. "Main Entrance Cam 1"

  AttendanceModel({
    required this.id,
    required this.employeeId,
    required this.employeeName,
    required this.date,
    this.checkInTime,
    this.checkOutTime,
    required this.status,
    required this.confidenceScore,
    required this.cameraSource,
  });
}

enum ArchiveType { all, faceDetection, attendance, alert }

class ArchiveModel {
  final String id;
  final String cameraId;
  final String cameraName;
  final DateTime timestamp;
  final int durationSeconds;
  final ArchiveType type;
  final String? description;
  final String? filePath;

  ArchiveModel({
    required this.id,
    required this.cameraId,
    required this.cameraName,
    required this.timestamp,
    required this.durationSeconds,
    required this.type,
    this.description,
    this.filePath,
  });
}

class DashboardSummary {
  final int totalCameras;
  final int activeCameras;
  final int offlineCameras;
  final int facesDetectedToday;
  final int attendanceMarkedToday;

  DashboardSummary({
    required this.totalCameras,
    required this.activeCameras,
    required this.offlineCameras,
    required this.facesDetectedToday,
    required this.attendanceMarkedToday,
  });
}
