import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../core/widgets/app_shell.dart';
import '../../features/auth/login_screen.dart';
import '../../features/dashboard/dashboard_screen.dart';
import '../../features/cameras/camera_detail_screen.dart';
import '../../features/cameras/cameras_screen.dart';
import '../../features/employees/employees_screen.dart';
import '../../features/employees/employee_detail_screen.dart';
import '../../features/employees/employee_form_screen.dart';
import '../../features/footage/footage_screen.dart';
import '../../features/attendance/attendance_screen.dart';
import '../../features/settings/settings_screen.dart';
import '../../features/profile/profile_screen.dart';
import '../../features/settings/system_repair_screen.dart';

final _rootNav  = GlobalKey<NavigatorState>();
final _shellNav = GlobalKey<NavigatorState>();

final appRouter = GoRouter(
  navigatorKey: _rootNav,
  initialLocation: '/login',
  routes: [
    GoRoute(path: '/', redirect: (_, _) => '/login'),
    GoRoute(path: '/login', builder: (_, _) => const LoginScreen()),
    ShellRoute(
      navigatorKey: _shellNav,
      builder: (_, _, child) => AppShell(child: child),
      routes: [
        GoRoute(path: '/dashboard',   builder: (_, _) => const DashboardScreen()),
        GoRoute(path: '/cameras',     builder: (_, _) => const CamerasScreen(),
          routes: [
            GoRoute(path: ':id', builder: (_, s)  => CameraDetailScreen(
                cameraId: s.pathParameters['id'] ?? '')),
          ],
        ),
        GoRoute(path: '/employees',   builder: (_, _) => const EmployeesScreen(),
          routes: [
            GoRoute(path: 'add',      builder: (_, _) => const EmployeeFormScreen()),
            GoRoute(path: ':id',      builder: (_, s)  => EmployeeDetailScreen(
                employeeId: s.pathParameters['id'] ?? '')),
          ],
        ),
        GoRoute(path: '/footage',     builder: (_, _) => const FootageScreen()),
        GoRoute(path: '/attendance',  builder: (_, _) => const AttendanceScreen()),
        GoRoute(path: '/settings',    builder: (_, _) => const SettingsScreen()),
        GoRoute(path: '/profile',     builder: (_, _) => const ProfileScreen()),
        GoRoute(path: '/repair',      builder: (_, _) => const SystemRepairScreen()),
      ],
    ),
  ],
);
