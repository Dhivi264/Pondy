import 'package:flutter/material.dart';
import '../../core/theme/app_theme.dart';
import '../../core/responsive/responsive_layout.dart';
import '../../data/services/api_service.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:intl/intl.dart';

class FootageScreen extends StatefulWidget {
  const FootageScreen({super.key});

  @override
  State<FootageScreen> createState() => _FootageScreenState();
}

class _FootageScreenState extends State<FootageScreen> {
  List<dynamic> _recordings = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _fetchFootage();
  }

  Future<void> _fetchFootage() async {
    try {
      setState(() {
        _isLoading = true;
        _error = null;
      });
      final data = await ApiService.instance.getRecordingsList();
      setState(() {
        _recordings = data;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  void _playVideo(String url) async {
    final uri = Uri.parse('${ApiService.instance.token == null ? kBackendBase : kBackendBase}$url');
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri);
    } else {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Could not play video.')),
        );
      }
    }
  }

  String _formatBytes(int bytes) {
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    if (bytes < 1024 * 1024 * 1024) return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
    return '${(bytes / (1024 * 1024 * 1024)).toStringAsFixed(2)} GB';
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Scaffold(
      backgroundColor: Colors.transparent,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'CCTV Footage',
                        style: TextStyle(
                          fontSize: 28,
                          fontWeight: FontWeight.w800,
                          color: isDark ? AppColors.textPrimary : LightColors.textPrimary,
                          letterSpacing: -0.5,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Backend recording files',
                        style: TextStyle(
                          fontSize: 14,
                          color: isDark ? AppColors.textSecondary : LightColors.textSecondary,
                        ),
                      ),
                    ],
                  ),
                  IconButton(
                    icon: Icon(Icons.refresh, color: isDark ? AppColors.primary : LightColors.primary),
                    onPressed: _fetchFootage,
                  ),
                ],
              ),
              const SizedBox(height: 24),
              Expanded(
                child: _isLoading
                    ? const Center(child: CircularProgressIndicator())
                    : _error != null
                        ? Center(child: Text('Error: $_error', style: const TextStyle(color: AppColors.error)))
                        : _recordings.isEmpty
                            ? Center(
                                child: Column(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    Icon(Icons.video_collection_outlined, size: 64, color: isDark ? AppColors.textMuted : LightColors.textMuted),
                                    const SizedBox(height: 16),
                                    Text('No recordings found', style: TextStyle(color: isDark ? AppColors.textSecondary : LightColors.textSecondary)),
                                  ],
                                ),
                              )
                            : ResponsiveLayout.isMobile(context)
                                ? _buildList(isDark)
                                : _buildGrid(isDark),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildList(bool isDark) {
    return ListView.builder(
      itemCount: _recordings.length,
      itemBuilder: (context, index) {
        final rec = _recordings[index];
        return _buildFootageCard(rec, isDark);
      },
    );
  }

  Widget _buildGrid(bool isDark) {
    return GridView.builder(
      physics: const BouncingScrollPhysics(),
      gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
        maxCrossAxisExtent: 350,
        mainAxisSpacing: 16,
        crossAxisSpacing: 16,
        childAspectRatio: 1.5,
      ),
      itemCount: _recordings.length,
      itemBuilder: (context, index) {
        final rec = _recordings[index];
        return _buildFootageCard(rec, isDark);
      },
    );
  }

  Widget _buildFootageCard(dynamic rec, bool isDark) {
    final filename = rec['filename'] as String;
    final size = rec['size_bytes'] as int;
    final createdAtMs = rec['created_at'] as double;
    final date = DateTime.fromMillisecondsSinceEpoch((createdAtMs * 1000).toInt());

    return Card(
      color: isDark ? AppColors.surface : LightColors.surface,
      elevation: isDark ? 4 : 2,
      shadowColor: Colors.black26,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () => _playVideo(rec['url']),
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: (isDark ? AppColors.primary : LightColors.primary).withOpacity(0.1),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Icon(Icons.movie_creation_rounded, color: isDark ? AppColors.primary : LightColors.primary),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          filename,
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.w600,
                            color: isDark ? AppColors.textPrimary : LightColors.textPrimary,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        const SizedBox(height: 4),
                        Text(
                          _formatBytes(size),
                          style: TextStyle(
                            fontSize: 12,
                            color: isDark ? AppColors.teal : LightColors.teal,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const Spacer(),
              Divider(color: isDark ? AppColors.border : LightColors.border),
              const SizedBox(height: 8),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      Icon(Icons.calendar_today_rounded, size: 14, color: isDark ? AppColors.textMuted : LightColors.textMuted),
                      const SizedBox(width: 4),
                      Text(
                        DateFormat('MMM d, y, h:mm a').format(date),
                        style: TextStyle(
                          fontSize: 12,
                          color: isDark ? AppColors.textSecondary : LightColors.textSecondary,
                        ),
                      ),
                    ],
                  ),
                  Icon(Icons.play_circle_fill_rounded, color: isDark ? AppColors.primary : LightColors.primary),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
