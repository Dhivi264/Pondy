import 'dart:async';
// ignore: avoid_web_libraries_in_flutter
import 'dart:html' as html;
import 'dart:ui_web' as ui;

import 'package:flutter/material.dart';

/// A web-only widget that shows the device webcam feed using
/// the browser's getUserMedia API — no `camera` package needed.
/// When [showCapture] is true, shows a capture button that returns
/// an [html.Blob] (the captured JPEG) via [Navigator.pop].
class LocalCameraWidget extends StatefulWidget {
  final bool showCapture;
  const LocalCameraWidget({super.key, this.showCapture = false});

  @override
  State<LocalCameraWidget> createState() => _LocalCameraWidgetState();
}

class _LocalCameraWidgetState extends State<LocalCameraWidget> {
  html.VideoElement? _video;
  html.MediaStream? _stream;
  String _error = '';
  bool _ready = false;
  late final String _viewId;

  @override
  void initState() {
    super.initState();
    _viewId = 'webcam-${DateTime.now().millisecondsSinceEpoch}';
    _startCamera();
  }

  Future<void> _startCamera() async {
    try {
      _stream = await html.window.navigator.mediaDevices!.getUserMedia({
        'video': true,
        'audio': false,
      });

      _video = html.VideoElement()
        ..autoplay = true
        ..muted = true
        ..style.width = '100%'
        ..style.height = '100%'
        ..style.objectFit = 'cover'
        ..srcObject = _stream;

      // ignore: undefined_prefixed_name
      ui.platformViewRegistry.registerViewFactory(
        _viewId,
        (int id) => _video!,
      );

      if (mounted) setState(() => _ready = true);
    } catch (e) {
      if (mounted) setState(() => _error = 'Camera error: $e');
    }
  }

  Future<void> _capture() async {
    if (_video == null) return;
    final canvas = html.CanvasElement(
      width: _video!.videoWidth,
      height: _video!.videoHeight,
    );
    canvas.context2D.drawImage(_video!, 0, 0);
    final blob = await canvas.toBlob('image/jpeg', 0.92);
    if (!mounted) return;
    Navigator.pop(context, blob);
  }

  @override
  void dispose() {
    _stream?.getTracks().forEach((t) => t.stop());
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_error.isNotEmpty) {
      return Container(
        color: Colors.black87,
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.videocam_off, color: Colors.white54, size: 48),
              const SizedBox(height: 12),
              const Text(
                'CAMERA FEED UNAVAILABLE',
                style: TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 1.5,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                _error,
                style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.5),
                  fontSize: 11,
                ),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      );
    }

    if (!_ready) {
      return const Center(child: CircularProgressIndicator());
    }

    return Stack(
      children: [
        SizedBox.expand(
          child: HtmlElementView(viewType: _viewId),
        ),
        if (widget.showCapture) ...[
          Align(
            alignment: Alignment.bottomCenter,
            child: Padding(
              padding: const EdgeInsets.only(bottom: 24),
              child: FloatingActionButton(
                backgroundColor: Colors.white,
                onPressed: _capture,
                child: const Icon(Icons.camera_alt, color: Colors.black),
              ),
            ),
          ),
          Positioned(
            top: 10,
            right: 10,
            child: IconButton(
              icon: const Icon(Icons.close, color: Colors.white),
              onPressed: () => Navigator.pop(context, null),
            ),
          ),
        ],
      ],
    );
  }
}
