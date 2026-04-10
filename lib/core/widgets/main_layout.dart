import 'package:flutter/material.dart';
import 'side_navigation.dart';
import 'responsive_layout.dart';

class MainLayout extends StatelessWidget {
  final Widget child;

  const MainLayout({super.key, required this.child});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Row(
        children: [
          if (ResponsiveLayout.isDesktop(context)) const SideNavigation(),
          Expanded(
            child: Column(
              children: [
                if (!ResponsiveLayout.isDesktop(context))
                  AppBar(
                    title: const Text('Smart CCTV'),
                    leading: Builder(
                      builder: (context) => IconButton(
                        icon: const Icon(Icons.menu),
                        onPressed: () => Scaffold.of(context).openDrawer(),
                      ),
                    ),
                  ),
                Expanded(child: child),
              ],
            ),
          ),
        ],
      ),
      drawer: ResponsiveLayout.isDesktop(context) ? null : const SideNavigation(),
    );
  }
}
