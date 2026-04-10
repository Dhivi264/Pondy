import 'package:flutter_riverpod/flutter_riverpod.dart';

// Authentication State
final authProvider = StateProvider<bool>((ref) => false);

// Placeholder Provider for Employee State
final employeesProvider = FutureProvider((ref) async {
  // To be connected to EmployeeRepository implementation
  return [];
});

// Placeholder Provider for Camera State
final camerasProvider = StateProvider<List<dynamic>>((ref) => []);

// Application Settings State
final darkModeProvider = StateProvider<bool>((ref) => true);
