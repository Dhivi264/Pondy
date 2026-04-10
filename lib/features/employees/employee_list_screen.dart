import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_theme.dart';
import '../../core/responsive/responsive_layout.dart';

class EmployeeListScreen extends StatefulWidget {
  const EmployeeListScreen({super.key});

  @override
  State<EmployeeListScreen> createState() => _EmployeeListScreenState();
}

class _EmployeeListScreenState extends State<EmployeeListScreen> {
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    // Simulate loading state
    Future.delayed(const Duration(seconds: 1), () {
      if (mounted) setState(() => _isLoading = false);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Employee Management',
                  style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
                ),
                ElevatedButton.icon(
                  onPressed: () => context.go('/employees/add'),
                  icon: const Icon(Icons.person_add),
                  label: const Text('Add Employee'),
                ),
              ],
            ),
            const SizedBox(height: 24),
            Row(
              children: [
                Expanded(
                  child: TextField(
                    decoration: const InputDecoration(
                      hintText: 'Search by ID or Name...',
                      prefixIcon: Icon(Icons.search),
                    ),
                  ),
                ),
                const SizedBox(width: 16),
                OutlinedButton.icon(
                  onPressed: () {},
                  icon: const Icon(Icons.filter_list),
                  label: const Text('Filter'),
                ),
              ],
            ),
            const SizedBox(height: 24),
            Expanded(
              child: _isLoading
                  ? const Center(child: CircularProgressIndicator())
                  : _buildList(context),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildList(BuildContext context) {
    final isDesktop = ResponsiveLayout.isDesktop(context);
    
    // Using minimal mock data (3 items max) for layout preview
    final items = [
      {'id': 'EMP-001', 'name': 'John Doe', 'role': 'Security Officer'},
      {'id': 'EMP-002', 'name': 'Jane Smith', 'role': 'Administrator'},
      {'id': 'EMP-003', 'name': 'Mike Ross', 'role': 'Technician'},
    ];

    if (items.isEmpty) {
      return const Center(child: Text('No employees found.', style: TextStyle(color: AppTheme.textMuted)));
    }

    if (isDesktop) {
      return Card(
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 16.0, vertical: 8.0),
              child: Row(
                children: [
                  Expanded(flex: 2, child: Text('ID', style: TextStyle(fontWeight: FontWeight.bold, color: AppTheme.textMuted))),
                  Expanded(flex: 3, child: Text('Name', style: TextStyle(fontWeight: FontWeight.bold, color: AppTheme.textMuted))),
                  Expanded(flex: 3, child: Text('Role', style: TextStyle(fontWeight: FontWeight.bold, color: AppTheme.textMuted))),
                  Expanded(flex: 2, child: Text('Status', style: TextStyle(fontWeight: FontWeight.bold, color: AppTheme.textMuted))),
                  SizedBox(width: 48), // Actions column
                ],
              ),
            ),
            const Divider(),
            ...items.map((e) => _buildDesktopRow(context, e)),
          ],
        ),
      );
    }
    
    return ListView.builder(
      itemCount: items.length,
      itemBuilder: (context, index) {
        return Card(
          margin: const EdgeInsets.only(bottom: 12),
          child: ListTile(
            leading: const CircleAvatar(child: Icon(Icons.person)),
            title: Text(items[index]['name']!),
            subtitle: Text('${items[index]['id']}  •  ${items[index]['role']}'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => context.go('/employees/${items[index]['id']}'),
          ),
        );
      },
    );
  }

  Widget _buildDesktopRow(BuildContext context, Map<String, String> item) {
    return InkWell(
      onTap: () => context.go('/employees/${item['id']}'),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
        child: Row(
          children: [
            Expanded(flex: 2, child: Text(item['id']!)),
            Expanded(flex: 3, child: Row(
              children: [
                const CircleAvatar(radius: 12, child: Icon(Icons.person, size: 16)),
                const SizedBox(width: 12),
                Text(item['name']!),
              ],
            )),
            Expanded(flex: 3, child: Text(item['role']!)),
            Expanded(
              flex: 2,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: AppTheme.success.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: const Text('Cleared', style: TextStyle(color: AppTheme.success, fontSize: 12)),
              ),
            ),
            IconButton(
              icon: const Icon(Icons.more_vert, size: 20),
              onPressed: () {},
              color: AppTheme.textMuted,
            ),
          ],
        ),
      ),
    );
  }
}
