import 'dart:html' as html; // ignore: avoid_web_libraries_in_flutter

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_theme.dart';
import '../../data/services/api_service.dart';
import '../../data/providers/app_providers.dart';
import '../cameras/local_camera_widget.dart';

class EmployeeFormScreen extends ConsumerStatefulWidget {
  const EmployeeFormScreen({super.key});
  @override
  ConsumerState<EmployeeFormScreen> createState() => _EmployeeFormScreenState();
}

class _EmployeeFormScreenState extends ConsumerState<EmployeeFormScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameCtrl = TextEditingController();
  final _idCtrl = TextEditingController();
  final _emailCtrl = TextEditingController();
  final _phoneCtrl = TextEditingController();
  String _dept = 'Security';
  String _role = 'Staff';
  bool _faceEnrolled = false;
  bool _saving = false;
  String? _error;
  String? _imageBase64;

  static const _depts = ['Security', 'IT', 'HR', 'Operations', 'Finance'];
  static const _roles = ['Staff', 'Manager', 'Analyst', 'Guard', 'Supervisor'];

  @override
  void dispose() {
    _nameCtrl.dispose();
    _idCtrl.dispose();
    _emailCtrl.dispose();
    _phoneCtrl.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      await ApiService.instance.createEmployee({
        'employee_id': _idCtrl.text.trim(),
        'name': _nameCtrl.text.trim(),
        if (_emailCtrl.text.trim().isNotEmpty) 'email': _emailCtrl.text.trim(),
        if (_phoneCtrl.text.trim().isNotEmpty) 'phone': _phoneCtrl.text.trim(),
        'department': _dept,
        'role': _role,
        'has_face_enrolled': _faceEnrolled,
        if (_imageBase64 != null) 'face_image_base64': _imageBase64,
        'is_active': true,
      });
      ref.invalidate(employeesProvider);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('${_nameCtrl.text} added successfully'),
            backgroundColor: AppColors.success,
          ),
        );
        context.go('/employees');
      }
    } catch (e) {
      setState(() => _error = 'Save failed: $e');
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.surface,
        leading: IconButton(
          icon: const Icon(
            Icons.arrow_back_rounded,
            color: AppColors.textPrimary,
          ),
          onPressed: () => context.go('/employees'),
        ),
        title: const Text(
          'Add New Employee',
          style: TextStyle(
            color: AppColors.textPrimary,
            fontWeight: FontWeight.w700,
          ),
        ),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Container(height: 1, color: AppColors.border),
        ),
      ),
      body: Center(
        child: Container(
          width: 680,
          margin: const EdgeInsets.symmetric(vertical: 28),
          child: Form(
            key: _formKey,
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(32),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _sectionLabel('Personal Information'),
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      Expanded(
                        child: _field(
                          'Full Name',
                          _nameCtrl,
                          hint: 'John Doe',
                          icon: Icons.person_rounded,
                          validator: (v) =>
                              v == null || v.isEmpty ? 'Required' : null,
                        ),
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: _field(
                          'Employee ID',
                          _idCtrl,
                          hint: 'EMP0001',
                          icon: Icons.badge_rounded,
                          validator: (v) =>
                              v == null || v.isEmpty ? 'Required' : null,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      Expanded(
                        child: _field(
                          'Email',
                          _emailCtrl,
                          hint: 'john@company.com',
                          icon: Icons.email_rounded,
                          keyboard: TextInputType.emailAddress,
                        ),
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: _field(
                          'Phone',
                          _phoneCtrl,
                          hint: '+1 555 0000',
                          icon: Icons.phone_rounded,
                          keyboard: TextInputType.phone,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      Expanded(
                        child: _dropdown(
                          'Department',
                          _dept,
                          _depts,
                          (v) => setState(() => _dept = v!),
                        ),
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: _dropdown(
                          'Role',
                          _role,
                          _roles,
                          (v) => setState(() => _role = v!),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 28),
                  _sectionLabel('Face Recognition'),
                  const SizedBox(height: 16),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(24),
                    decoration: BoxDecoration(
                      color: AppColors.surfaceCard,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: _faceEnrolled
                            ? AppColors.success.withValues(alpha: 0.4)
                            : AppColors.border,
                      ),
                    ),
                    child: Column(
                      children: [
                        Icon(
                          _faceEnrolled
                              ? Icons.face_rounded
                              : Icons.face_retouching_off_rounded,
                          size: 48,
                          color: _faceEnrolled
                              ? AppColors.success
                              : AppColors.textMuted,
                        ),
                        const SizedBox(height: 10),
                        Text(
                          _faceEnrolled
                              ? 'Face marked as enrolled'
                              : 'No face enrolled',
                          style: TextStyle(
                            color: _faceEnrolled
                                ? AppColors.success
                                : AppColors.textSecondary,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(height: 4),
                        const Text(
                          'Capture via webcam or mark as enrolled manually.',
                          style: TextStyle(
                            color: AppColors.textMuted,
                            fontSize: 12,
                          ),
                        ),
                        const SizedBox(height: 14),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            OutlinedButton.icon(
                              onPressed: () => setState(
                                () => _faceEnrolled = !_faceEnrolled,
                              ),
                              style: OutlinedButton.styleFrom(
                                foregroundColor: _faceEnrolled
                                    ? AppColors.success
                                    : AppColors.primary,
                                side: BorderSide(
                                  color: _faceEnrolled
                                      ? AppColors.success
                                      : AppColors.primary,
                                ),
                              ),
                              icon: Icon(
                                _faceEnrolled
                                    ? Icons.check_rounded
                                    : Icons.camera_alt_rounded,
                                size: 16,
                              ),
                              label: Text(
                                _faceEnrolled ? 'Unmark' : 'Mark as Enrolled',
                              ),
                            ),
                            const SizedBox(width: 12),
                            OutlinedButton.icon(
                              onPressed: () {
                                final html.FileUploadInputElement uploadInput = html.FileUploadInputElement();
                                uploadInput.accept = 'image/*';
                                uploadInput.click();
                                uploadInput.onChange.listen((e) {
                                  if (uploadInput.files != null && uploadInput.files!.isNotEmpty) {
                                    final file = uploadInput.files![0];
                                    final reader = html.FileReader();
                                    reader.readAsDataUrl(file);
                                    reader.onLoadEnd.listen((_) {
                                      setState(() {
                                        _faceEnrolled = true;
                                        _imageBase64 = reader.result as String?;
                                      });
                                      if (mounted) {
                                        ScaffoldMessenger.of(context).showSnackBar(
                                          const SnackBar(
                                            content: Text('Photo uploaded and face enrolled.'),
                                            backgroundColor: AppColors.success,
                                          ),
                                        );
                                      }
                                    });
                                  }
                                });
                              },
                              style: OutlinedButton.styleFrom(
                                foregroundColor: AppColors.primary,
                                side: const BorderSide(color: AppColors.primary),
                              ),
                              icon: const Icon(Icons.upload_file_rounded, size: 16),
                              label: const Text('Upload Photo'),
                            ),
                            const SizedBox(width: 12),
                            ElevatedButton.icon(
                              onPressed: () async {
                                final result = await showDialog<html.Blob>(
                                  context: context,
                                  builder: (context) => const Dialog(
                                    backgroundColor: Colors.black,
                                    child: SizedBox(
                                      width: 800,
                                      height: 600,
                                      child: LocalCameraWidget(showCapture: true),
                                    ),
                                  ),
                                );
                                if (result != null) {
                                  setState(() => _faceEnrolled = true);
                                  if (!context.mounted) return;
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    const SnackBar(
                                      content: Text(
                                        'Face captured and enrolled.',
                                      ),
                                      backgroundColor: AppColors.success,
                                    ),
                                  );
                                }
                              },
                              icon: const Icon(
                                Icons.videocam_rounded,
                                size: 16,
                              ),
                              label: const Text('Capture Live'),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  if (_error != null) ...[
                    const SizedBox(height: 16),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: AppColors.errorBg,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(
                          color: AppColors.error.withValues(alpha: 0.3),
                        ),
                      ),
                      child: Row(
                        children: [
                          const Icon(
                            Icons.error_outline,
                            color: AppColors.error,
                            size: 16,
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              _error!,
                              style: const TextStyle(
                                color: AppColors.error,
                                fontSize: 13,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                  const SizedBox(height: 32),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      OutlinedButton(
                        onPressed: () => context.go('/employees'),
                        child: const Text('Cancel'),
                      ),
                      const SizedBox(width: 12),
                      SizedBox(
                        height: 44,
                        child: ElevatedButton.icon(
                          onPressed: _saving ? null : _save,
                          icon: _saving
                              ? const SizedBox(
                                  width: 14,
                                  height: 14,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                    color: Colors.white,
                                  ),
                                )
                              : const Icon(Icons.save_rounded, size: 16),
                          label: const Text(
                            'Save Employee',
                            style: TextStyle(fontWeight: FontWeight.w700),
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _sectionLabel(String text) => Row(
    children: [
      Text(
        text,
        style: const TextStyle(
          color: AppColors.textPrimary,
          fontSize: 15,
          fontWeight: FontWeight.w700,
        ),
      ),
      const SizedBox(width: 12),
      Expanded(child: Container(height: 1, color: AppColors.border)),
    ],
  );

  Widget _field(
    String label,
    TextEditingController ctrl, {
    String? hint,
    IconData? icon,
    TextInputType keyboard = TextInputType.text,
    String? Function(String?)? validator,
  }) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        label,
        style: const TextStyle(
          color: AppColors.textSecondary,
          fontSize: 12,
          fontWeight: FontWeight.w600,
        ),
      ),
      const SizedBox(height: 6),
      TextFormField(
        controller: ctrl,
        keyboardType: keyboard,
        style: const TextStyle(color: AppColors.textPrimary, fontSize: 14),
        decoration: InputDecoration(
          hintText: hint,
          prefixIcon: icon != null
              ? Icon(icon, size: 17, color: AppColors.textMuted)
              : null,
        ),
        validator: validator,
      ),
    ],
  );

  Widget _dropdown(
    String label,
    String value,
    List<String> items,
    ValueChanged<String?> onChanged,
  ) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        label,
        style: const TextStyle(
          color: AppColors.textSecondary,
          fontSize: 12,
          fontWeight: FontWeight.w600,
        ),
      ),
      const SizedBox(height: 6),
      DropdownButtonFormField<String>(
        initialValue: value,
        dropdownColor: AppColors.surfaceCard,
        style: const TextStyle(color: AppColors.textPrimary, fontSize: 14),
        decoration: const InputDecoration(),
        items: items
            .map((d) => DropdownMenuItem(value: d, child: Text(d)))
            .toList(),
        onChanged: onChanged,
      ),
    ],
  );
}
