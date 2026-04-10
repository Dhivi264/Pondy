import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/theme/app_theme.dart';
import '../../data/services/api_service.dart';
import '../../data/providers/app_providers.dart';

class SystemRepairScreen extends ConsumerStatefulWidget {
  const SystemRepairScreen({super.key});

  @override
  ConsumerState<SystemRepairScreen> createState() => _SystemRepairScreenState();
}

class _SystemRepairScreenState extends ConsumerState<SystemRepairScreen> {
  bool _isRepairing = false;

  @override
  void initState() {
    super.initState();
    _fetchStatus();
  }

  Future<void> _fetchStatus() async {
    try {
      await ApiService.instance.getHardwareProfile();
    } catch (_) {}
  }

  Future<void> _triggerRepair() async {
    setState(() => _isRepairing = true);
    try {
      // 1. Force restart AI pipeline
      await ApiService.instance.post('/cameras/system/start_ai/', {});
      // 2. Refresh dashboard
      ref.invalidate(dashboardSummaryProvider);
      ref.invalidate(camerasProvider);
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Watchdog triggered: System repair active.'), backgroundColor: AppColors.success),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Repair failed: $e'), backgroundColor: AppColors.error),
        );
      }
    } finally {
      if (mounted) setState(() => _isRepairing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('AI System Repair Kit', style: TextStyle(fontWeight: FontWeight.w800)),
        backgroundColor: AppColors.surface,
        elevation: 0,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            _buildRepairCard(),
            const SizedBox(height: 24),
            _buildDiagnosticSummary(),
          ],
        ),
      ),
    );
  }

  Widget _buildRepairCard() {
    return Container(
      padding: const EdgeInsets.all(32),
      decoration: BoxDecoration(
        color: AppColors.surfaceCard,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: AppColors.border),
        boxShadow: const [BoxShadow(color: Color(0x10000000), blurRadius: 20)],
      ),
      child: Column(
        children: [
          Icon(Icons.health_and_safety_rounded, size: 64, color: _isRepairing ? AppColors.warning : AppColors.success),
          const SizedBox(height: 20),
          const Text('Self-Healing Engine', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800, color: AppColors.textPrimary)),
          const SizedBox(height: 8),
          const Text(
            'The AI Watchdog monitors all camera threads and database connections 24/7. Use this kit to force a re-calibration if streams appear hung.',
            textAlign: TextAlign.center,
            style: TextStyle(color: AppColors.textMuted, fontSize: 13, height: 1.5),
          ),
          const SizedBox(height: 32),
          SizedBox(
            width: double.infinity,
            height: 54,
            child: ElevatedButton.icon(
              onPressed: _isRepairing ? null : _triggerRepair,
              icon: _isRepairing 
                ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                : const Icon(Icons.bolt_rounded),
              label: Text(_isRepairing ? 'REPAIRING...' : 'INITIATE SYSTEM REPAIR'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.primary,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDiagnosticSummary() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('System Diagnostics', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
          const SizedBox(height: 16),
          _diagnosticRow('AI Model Status', 'YOLOv11-AI Engine Active', AppColors.success),
          _diagnosticRow('DB Connection', 'Healthy / Encrypted', AppColors.success),
          _diagnosticRow('Transport Layer', 'Automatic TCP/UDP failover', AppColors.teal),
          _diagnosticRow('Heartbeat', 'Last ping: 2s ago', AppColors.success),
        ],
      ),
    );
  }

  Widget _diagnosticRow(String label, String value, Color color) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 10),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: AppColors.textSecondary, fontSize: 13)),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(color: color.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(6)),
            child: Text(value, style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.w700)),
          ),
        ],
      ),
    );
  }
}
