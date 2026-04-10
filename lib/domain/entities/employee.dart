class Employee {
  final String id;
  final String name;
  final String department;
  final String role;
  final bool hasFaceEnrolled;
  final bool isActive;

  const Employee({
    required this.id,
    required this.name,
    required this.department,
    required this.role,
    this.hasFaceEnrolled = false,
    this.isActive = true,
  });

  // Example factory for future backend JSON parsing
  factory Employee.fromJson(Map<String, dynamic> json) {
    return Employee(
      id: json['id'] as String,
      name: json['name'] as String,
      department: json['department'] as String,
      role: json['role'] as String,
      hasFaceEnrolled: json['has_face_enrolled'] as bool? ?? false,
      isActive: json['is_active'] as bool? ?? true,
    );
  }
}
