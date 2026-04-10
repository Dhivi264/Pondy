import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:path/path.dart' as p;

class BackendService {
  static Process? _process;

  static Future<String?> start() async {
    if (kIsWeb) {
      debugPrint('[Backend] Cannot start backend process automatically from a web browser.');
      return 'Cannot start backend from web browser. Please run `python run.py` manually in your terminal.';
    }

    if (_process != null) return null;

    try {
      final rootDir = Directory.current.path;
      final backendDir = p.join(rootDir, 'backend');
      
      final pythonCmd = 'python';
      final scriptPath = p.join(backendDir, 'run.py');
      debugPrint('[Backend] Starting server: $pythonCmd $scriptPath');

      _process = await Process.start(
        pythonCmd,
        [scriptPath],
        workingDirectory: backendDir,
      );

      _process!.stdout.listen((data) {
        debugPrint('[Backend] ${String.fromCharCodes(data).trim()}');
      });

      _process!.stderr.listen((data) {
        debugPrint('[Backend-ERR] ${String.fromCharCodes(data).trim()}');
      });

      debugPrint('[Backend] Process started with PID: ${_process!.pid}');
      return null;
    } catch (e) {
      debugPrint('[Backend] ERROR: Failed to launch backend: $e');
      return 'Failed to launch backend: $e';
    }
  }

  static void stop() {
    _process?.kill();
    _process = null;
  }
}
