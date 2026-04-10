import 'dart:html' as html; // ignore: avoid_web_libraries_in_flutter

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_theme.dart';
import '../../features/cameras/local_camera_widget.dart';

class AddEmployeeScreen extends StatefulWidget {
  const AddEmployeeScreen({super.key});

  @override
  State<AddEmployeeScreen> createState() => _AddEmployeeScreenState();
}

class _AddEmployeeScreenState extends State<AddEmployeeScreen> {
  html.Blob? _capturedImage;

  Future<void> _captureFromWebcam() async {
    final html.Blob? result = await showDialog<html.Blob>(
      context: context,
      builder: (context) => const Dialog(
        backgroundColor: Colors.black,
        insetPadding: EdgeInsets.all(20),
        child: ClipRRect(
          borderRadius: BorderRadius.all(Radius.circular(16)),
          child: SizedBox(
            width: 800,
            height: 600,
            child: LocalCameraWidget(showCapture: true),
          ),
        ),
      ),
    );

    if (result != null) {
      setState(() => _capturedImage = result);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/employees'),
        ),
        title: const Text('Add New Employee'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24.0),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              flex: 2,
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(24.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Employee Details', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                      const SizedBox(height: 24),
                      Row(
                        children: [
                          Expanded(child: const _TextField(label: 'First Name')),
                          const SizedBox(width: 16),
                          Expanded(child: const _TextField(label: 'Last Name')),
                        ],
                      ),
                      const SizedBox(height: 16),
                      const _TextField(label: 'Employee ID (Auto-generated or Manual)'),
                      const SizedBox(height: 16),
                      Row(
                        children: [
                          Expanded(child: const _TextField(label: 'Department')),
                          const SizedBox(width: 16),
                          Expanded(child: const _TextField(label: 'Designation')),
                        ],
                      ),
                      const SizedBox(height: 16),
                      Row(
                        children: [
                          Expanded(child: const _TextField(label: 'Email')),
                          const SizedBox(width: 16),
                          Expanded(child: const _TextField(label: 'Phone Number')),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(width: 24),
            Expanded(
              flex: 1,
              child: Column(
                children: [
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(24.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          const Text('Face Registration', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                          const SizedBox(height: 16),
                          Container(
                            height: 200,
                            decoration: BoxDecoration(
                              color: AppColors.surfaceHighlight,
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(color: AppColors.border, style: BorderStyle.solid),
                            ),
                            child: _capturedImage != null
                              ? ClipRRect(
                                  borderRadius: BorderRadius.circular(8),
                                  child: Image.network(
                                    html.Url.createObjectUrl(_capturedImage!),
                                    fit: BoxFit.cover,
                                  ),
                                )
                              : const Column(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    Icon(Icons.add_a_photo, size: 48, color: AppColors.textMuted),
                                    SizedBox(height: 8),
                                    Text('Upload or capture face image', style: TextStyle(color: AppColors.textMuted)),
                                  ],
                                ),
                          ),
                          const SizedBox(height: 16),
                          OutlinedButton.icon(
                            onPressed: () {},
                            icon: const Icon(Icons.upload),
                            label: const Text('Upload Image'),
                          ),
                          const SizedBox(height: 8),
                          ElevatedButton.icon(
                            onPressed: _captureFromWebcam,
                            icon: const Icon(Icons.camera_alt),
                            label: const Text('Capture from Webcam'),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 24),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: () {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('Mock Employee Saved Successfully!')),
                        );
                        context.go('/employees');
                      },
                      style: ElevatedButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 20)),
                      child: const Text('SAVE EMPLOYEE', style: TextStyle(fontWeight: FontWeight.bold)),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _TextField extends StatelessWidget {
  final String label;

  const _TextField({required this.label});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
        const SizedBox(height: 8),
        const TextField(),
      ],
    );
  }
}
