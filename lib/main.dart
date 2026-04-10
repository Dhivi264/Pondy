import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'app/app.dart';
import 'core/services/backend_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Start backend automatically
  await BackendService.start();

  runApp(
    const ProviderScope(
      child: SmartCctvApp(),
    ),
  );
}
