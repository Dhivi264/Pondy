import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../data/services/api_service.dart';
import '../theme/app_theme.dart';

// ─── State ────────────────────────────────────────────────────────────────────

class _ChatMessage {
  final String role; // 'user' | 'assistant'
  final String content;
  final List<String> suggestions;
  final DateTime ts;
  _ChatMessage({
    required this.role,
    required this.content,
    this.suggestions = const [],
    DateTime? ts,
  }) : ts = ts ?? DateTime.now();
}

class _AssistantNotifier extends StateNotifier<List<_ChatMessage>> {
  _AssistantNotifier() : super([]);

  bool _loading = false;
  bool get loading => _loading;

  void _setLoading(bool v) {
    _loading = v;
    // trigger rebuild via state reassignment
    state = List.from(state);
  }

  Future<void> sendMessage(String text) async {
    if (text.trim().isEmpty) return;

    // Append user message
    state = [...state, _ChatMessage(role: 'user', content: text.trim())];

    _setLoading(true);

    try {
      // Ensure we are logged in as admin for system queries
      if (ApiService.instance.token == null) {
        try {
          await ApiService.instance.login('admin', 'admin123');
        } catch (_) {}
      }

      final history = state
          .where((m) => m.role != 'assistant' || m.content.isNotEmpty)
          .map((m) => {'role': m.role, 'content': m.content})
          .toList();

      final res = await ApiService.instance.post('/ai/ask', {
        'question': text.trim(),
        'conversation_history': history,
      });

      final answer = res['answer'] as String? ?? 'No response.';
      final suggestions = (res['suggestions'] as List?)?.cast<String>() ?? [];

      state = [
        ...state,
        _ChatMessage(
          role: 'assistant',
          content: answer,
          suggestions: suggestions,
        ),
      ];
    } catch (e) {
      debugPrint('[AiAssistant] Error: $e');
      state = [
        ...state,
        _ChatMessage(
          role: 'assistant',
          content:
              '⚠️ **Connection Error**\n\n'
              'I could not reach the Smart CCTV Intelligence at this moment.\n'
              'Please ensure the backend is active at `http://127.0.0.1:8000`.',
          suggestions: ['Retry connection', 'Check system status'],
        ),
      ];
    } finally {
      _setLoading(false);
    }
  }

  void clear() => state = [];
}

final _assistantProvider =
    StateNotifierProvider<_AssistantNotifier, List<_ChatMessage>>(
      (_) => _AssistantNotifier(),
    );

final _loadingProvider = Provider<bool>((ref) {
  ref.watch(_assistantProvider); // rebuild when messages change
  return ref.read(_assistantProvider.notifier).loading;
});

// ─── Floating Button ──────────────────────────────────────────────────────────

class AiAssistantFab extends ConsumerStatefulWidget {
  const AiAssistantFab({super.key});

  @override
  ConsumerState<AiAssistantFab> createState() => _AiAssistantFabState();
}

class _AiAssistantFabState extends ConsumerState<AiAssistantFab>
    with SingleTickerProviderStateMixin {
  late AnimationController _pulse;

  @override
  void initState() {
    super.initState();
    _pulse = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _pulse.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _pulse,
      builder: (_, child) =>
          Transform.scale(scale: 1.0 + _pulse.value * 0.04, child: child),
      child: FloatingActionButton(
        heroTag: 'ai_assistant_fab',
        onPressed: () => _openAssistant(context),
        backgroundColor: Colors.transparent,
        elevation: 0,
        child: Container(
          width: 56,
          height: 56,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: const LinearGradient(
              colors: [Color(0xFF0EA5E9), Color(0xFF8B5CF6)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            boxShadow: [
              BoxShadow(
                color: const Color(0xFF0EA5E9).withValues(alpha: 0.45),
                blurRadius: 18,
                spreadRadius: 2,
              ),
            ],
          ),
          child: const Icon(
            Icons.auto_awesome_rounded,
            color: Colors.white,
            size: 26,
          ),
        ),
      ),
    );
  }

  void _openAssistant(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => const _AssistantModal(),
    );
  }
}

// ─── Modal ────────────────────────────────────────────────────────────────────

class _AssistantModal extends ConsumerStatefulWidget {
  const _AssistantModal();

  @override
  ConsumerState<_AssistantModal> createState() => _AssistantModalState();
}

class _AssistantModalState extends ConsumerState<_AssistantModal> {
  final _controller = TextEditingController();
  final _scroll = ScrollController();

  static const _suggestions = [
    'System overview',
    'Show cameras',
    "Today's attendance",
    'AI pipeline status',
    'Offline cameras',
    'Employee enrollment',
    'Where has employee #1 been?',
    'Cameras for EMP001',
  ];

  @override
  void dispose() {
    _controller.dispose();
    _scroll.dispose();
    super.dispose();
  }

  void _send([String? override]) {
    final text = override ?? _controller.text;
    if (text.trim().isEmpty) return;
    _controller.clear();
    ref.read(_assistantProvider.notifier).sendMessage(text);
    Future.delayed(const Duration(milliseconds: 300), _scrollBottom);
  }

  void _scrollBottom() {
    if (_scroll.hasClients) {
      _scroll.animateTo(
        _scroll.position.maxScrollExtent,
        duration: const Duration(milliseconds: 350),
        curve: Curves.easeOut,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final messages = ref.watch(_assistantProvider);
    final loading = ref.watch(_loadingProvider);

    // Auto-scroll when new message arrives
    WidgetsBinding.instance.addPostFrameCallback((_) => _scrollBottom());

    return DraggableScrollableSheet(
      initialChildSize: 0.78,
      minChildSize: 0.45,
      maxChildSize: 0.95,
      builder: (_, scrollCtl) => Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.of(context).viewInsets.bottom,
        ),
        child: Container(
          decoration: const BoxDecoration(
            color: Color(0xFF0F1923),
            borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
          ),
          child: Column(
            children: [
              // ── Handle ──────────────────────────────────────────────────────
              _Handle(),

              // ── Header ──────────────────────────────────────────────────────
              _Header(
                onClear: () => ref.read(_assistantProvider.notifier).clear(),
              ),

              const Divider(height: 1, color: AppColors.border),

              // ── Messages ────────────────────────────────────────────────────
              Expanded(
                child: SingleChildScrollView(
                  controller: _scroll,
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 12,
                  ),
                  child: messages.isEmpty
                      ? _Welcome(onTap: _send)
                      : ListView.builder(
                          shrinkWrap: true,
                          physics: const NeverScrollableScrollPhysics(),
                          itemCount: messages.length + (loading ? 1 : 0),
                          itemBuilder: (_, i) {
                            if (loading && i == messages.length) {
                              return _TypingBubble();
                            }
                            final m = messages[i];
                            return _MessageBubble(
                              message: m,
                              onSuggestion: _send,
                            );
                          },
                        ),
                ),
              ),

              // ── Quick Chips (only on empty state) ───────────────────────────
              if (messages.isEmpty)
                _QuickChips(chips: _suggestions, onTap: _send),

              // ── Input ───────────────────────────────────────────────────────
              _InputBar(
                controller: _controller,
                loading: loading,
                onSend: _send,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ─── Sub-widgets ──────────────────────────────────────────────────────────────

class _Handle extends StatelessWidget {
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(top: 10, bottom: 4),
    child: Center(
      child: Container(
        width: 40,
        height: 4,
        decoration: BoxDecoration(
          color: AppColors.border,
          borderRadius: BorderRadius.circular(2),
        ),
      ),
    ),
  );
}

class _Header extends StatelessWidget {
  final VoidCallback onClear;
  const _Header({required this.onClear});

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
    child: Row(
      children: [
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0xFF0EA5E9), Color(0xFF8B5CF6)],
            ),
            borderRadius: BorderRadius.circular(10),
          ),
          child: const Icon(
            Icons.auto_awesome_rounded,
            color: Colors.white,
            size: 18,
          ),
        ),
        const SizedBox(width: 12),
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Smart CCTV Assistant',
              style: TextStyle(
                color: AppColors.textPrimary,
                fontSize: 15,
                fontWeight: FontWeight.w700,
              ),
            ),
            const Text(
              'AI-powered · live system data',
              style: TextStyle(color: AppColors.textMuted, fontSize: 11),
            ),
          ],
        ),
        const Spacer(),
        IconButton(
          icon: const Icon(
            Icons.delete_outline_rounded,
            color: AppColors.textMuted,
            size: 20,
          ),
          tooltip: 'Clear chat',
          onPressed: onClear,
        ),
      ],
    ),
  );
}

class _Welcome extends StatelessWidget {
  final void Function(String) onTap;
  const _Welcome({required this.onTap});

  static const _starters = [
    ('📊', 'System overview', 'Full status snapshot'),
    ('📷', 'Show cameras', 'Camera list & status'),
    ('📋', 'Today\'s attendance', 'Present / absent today'),
    ('🔍', 'Camera trail for EMP001', 'Which cameras a person passed'),
  ];

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.all(24),
    child: SingleChildScrollView(
      child: Column(
        children: [
          const SizedBox(height: 8),
          ShaderMask(
            shaderCallback: (b) => const LinearGradient(
              colors: [Color(0xFF0EA5E9), Color(0xFF8B5CF6)],
            ).createShader(b),
            child: const Text(
              'How can I help you?',
              style: TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.w800,
                color: Colors.white,
              ),
            ),
          ),
          const SizedBox(height: 6),
          const Text(
            'I have live access to cameras, attendance, employees,\n'
            'and the AI processing pipeline.',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: AppColors.textMuted,
              fontSize: 12,
              height: 1.5,
            ),
          ),
          const SizedBox(height: 28),
          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            mainAxisSpacing: 10,
            crossAxisSpacing: 10,
            childAspectRatio: 2.4,
            physics: const NeverScrollableScrollPhysics(),
            children: _starters
                .map(
                  (s) => _StarterCard(
                    emoji: s.$1,
                    title: s.$2,
                    sub: s.$3,
                    onTap: () => onTap(s.$2),
                  ),
                )
                .toList(),
          ),
        ],
      ),
    ),
  );
}

class _StarterCard extends StatelessWidget {
  final String emoji, title, sub;
  final VoidCallback onTap;
  const _StarterCard({
    required this.emoji,
    required this.title,
    required this.sub,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) => InkWell(
    onTap: onTap,
    borderRadius: BorderRadius.circular(12),
    child: Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.surfaceCard,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        children: [
          Text(emoji, style: const TextStyle(fontSize: 18)),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    color: AppColors.textPrimary,
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
                Text(
                  sub,
                  style: const TextStyle(
                    color: AppColors.textMuted,
                    fontSize: 10,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
        ],
      ),
    ),
  );
}

class _QuickChips extends StatelessWidget {
  final List<String> chips;
  final void Function(String) onTap;
  const _QuickChips({required this.chips, required this.onTap});

  @override
  Widget build(BuildContext context) => SizedBox(
    height: 38,
    child: ListView.separated(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.symmetric(horizontal: 16),
      itemCount: chips.length,
      separatorBuilder: (_, _) => const SizedBox(width: 8),
      itemBuilder: (_, i) => GestureDetector(
        onTap: () => onTap(chips[i]),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
          decoration: BoxDecoration(
            color: AppColors.surfaceHighlight,
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: AppColors.border),
          ),
          child: Text(
            chips[i],
            style: const TextStyle(
              color: AppColors.textSecondary,
              fontSize: 12,
            ),
          ),
        ),
      ),
    ),
  );
}

class _MessageBubble extends StatelessWidget {
  final _ChatMessage message;
  final void Function(String) onSuggestion;
  const _MessageBubble({required this.message, required this.onSuggestion});

  bool get _isUser => message.role == 'user';

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 14),
    child: Column(
      crossAxisAlignment: _isUser
          ? CrossAxisAlignment.end
          : CrossAxisAlignment.start,
      children: [
        // Avatar row
        if (!_isUser)
          Padding(
            padding: const EdgeInsets.only(bottom: 6),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(5),
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [Color(0xFF0EA5E9), Color(0xFF8B5CF6)],
                    ),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Icon(
                    Icons.auto_awesome_rounded,
                    color: Colors.white,
                    size: 12,
                  ),
                ),
                const SizedBox(width: 6),
                const Text(
                  'Assistant',
                  style: TextStyle(color: AppColors.textMuted, fontSize: 11),
                ),
              ],
            ),
          ),

        // Bubble
        Container(
          constraints: BoxConstraints(
            maxWidth: MediaQuery.of(context).size.width * 0.82,
          ),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
          decoration: BoxDecoration(
            gradient: _isUser
                ? const LinearGradient(
                    colors: [Color(0xFF0284C7), Color(0xFF7C3AED)],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  )
                : null,
            color: _isUser ? null : AppColors.surfaceCard,
            borderRadius: BorderRadius.only(
              topLeft: const Radius.circular(16),
              topRight: const Radius.circular(16),
              bottomLeft: Radius.circular(_isUser ? 16 : 4),
              bottomRight: Radius.circular(_isUser ? 4 : 16),
            ),
            border: _isUser ? null : Border.all(color: AppColors.border),
          ),
          child: _isUser
              ? Text(
                  message.content,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 13,
                    height: 1.5,
                  ),
                )
              : _MarkdownText(message.content),
        ),

        // Suggestions
        if (message.suggestions.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Wrap(
              spacing: 7,
              runSpacing: 6,
              children: message.suggestions
                  .map(
                    (s) => GestureDetector(
                      onTap: () => onSuggestion(s),
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 6,
                        ),
                        decoration: BoxDecoration(
                          color: const Color(0xFF0EA5E9).withValues(alpha: 0.1),
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(
                            color: const Color(
                              0xFF0EA5E9,
                            ).withValues(alpha: 0.35),
                          ),
                        ),
                        child: Text(
                          s,
                          style: const TextStyle(
                            color: Color(0xFF0EA5E9),
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                    ),
                  )
                  .toList(),
            ),
          ),

        // Timestamp
        Padding(
          padding: const EdgeInsets.only(top: 4),
          child: Text(
            _fmt(message.ts),
            style: const TextStyle(color: AppColors.textMuted, fontSize: 10),
          ),
        ),
      ],
    ),
  );

  String _fmt(DateTime t) =>
      '${t.hour.toString().padLeft(2, '0')}:'
      '${t.minute.toString().padLeft(2, '0')}';
}

/// Simple markdown-ish text renderer (bold, bullets, newlines).
class _MarkdownText extends StatelessWidget {
  final String text;
  const _MarkdownText(this.text);

  @override
  Widget build(BuildContext context) {
    final spans = <InlineSpan>[];
    final lines = text.split('\n');
    for (var i = 0; i < lines.length; i++) {
      if (i > 0) spans.add(const TextSpan(text: '\n'));
      _parseLine(lines[i], spans);
    }
    return RichText(
      text: TextSpan(
        style: const TextStyle(
          color: AppColors.textPrimary,
          fontSize: 13,
          height: 1.55,
        ),
        children: spans,
      ),
    );
  }

  void _parseLine(String line, List<InlineSpan> out) {
    // Split on **bold** markers
    final parts = line.split(RegExp(r'\*\*'));
    bool bold = false;
    for (final part in parts) {
      if (part.isEmpty) {
        bold = !bold;
        continue;
      }
      out.add(
        TextSpan(
          text: part,
          style: bold
              ? const TextStyle(
                  fontWeight: FontWeight.w700,
                  color: AppColors.textPrimary,
                )
              : null,
        ),
      );
      bold = !bold;
    }
  }
}

class _TypingBubble extends StatefulWidget {
  @override
  State<_TypingBubble> createState() => _TypingBubbleState();
}

class _TypingBubbleState extends State<_TypingBubble>
    with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 700),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 14),
    child: Row(
      children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          decoration: BoxDecoration(
            color: AppColors.surfaceCard,
            borderRadius: const BorderRadius.only(
              topLeft: Radius.circular(16),
              topRight: Radius.circular(16),
              bottomRight: Radius.circular(16),
              bottomLeft: Radius.circular(4),
            ),
            border: Border.all(color: AppColors.border),
          ),
          child: AnimatedBuilder(
            animation: _ctrl,
            builder: (_, _) => Row(
              mainAxisSize: MainAxisSize.min,
              children: List.generate(3, (i) {
                final delay = i / 3;
                final v = ((_ctrl.value + delay) % 1.0);
                return Container(
                  margin: const EdgeInsets.symmetric(horizontal: 2.5),
                  width: 7,
                  height: 7,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: Color.lerp(
                      AppColors.textMuted,
                      const Color(0xFF0EA5E9),
                      v,
                    ),
                  ),
                );
              }),
            ),
          ),
        ),
      ],
    ),
  );
}

class _InputBar extends StatelessWidget {
  final TextEditingController controller;
  final bool loading;
  final VoidCallback onSend;
  const _InputBar({
    required this.controller,
    required this.loading,
    required this.onSend,
  });

  @override
  Widget build(BuildContext context) => Container(
    padding: EdgeInsets.only(left: 16, right: 16, top: 10, bottom: 14),
    decoration: const BoxDecoration(
      color: Color(0xFF0F1923),
      border: Border(top: BorderSide(color: AppColors.border)),
    ),
    child: Row(
      children: [
        Expanded(
          child: TextField(
            controller: controller,
            enabled: !loading,
            onSubmitted: (_) => onSend(),
            maxLines: 3,
            minLines: 1,
            style: const TextStyle(color: AppColors.textPrimary, fontSize: 13),
            decoration: InputDecoration(
              hintText: 'Ask about cameras, attendance, AI pipeline…',
              hintStyle: const TextStyle(
                color: AppColors.textMuted,
                fontSize: 12,
              ),
              filled: true,
              fillColor: AppColors.surfaceCard,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(14),
                borderSide: const BorderSide(color: AppColors.border),
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(14),
                borderSide: const BorderSide(color: AppColors.border),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(14),
                borderSide: const BorderSide(
                  color: Color(0xFF0EA5E9),
                  width: 1.5,
                ),
              ),
              contentPadding: const EdgeInsets.symmetric(
                horizontal: 14,
                vertical: 10,
              ),
              isDense: true,
            ),
          ),
        ),
        const SizedBox(width: 10),
        GestureDetector(
          onTap: loading ? null : onSend,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: loading
                  ? null
                  : const LinearGradient(
                      colors: [Color(0xFF0EA5E9), Color(0xFF8B5CF6)],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
              color: loading ? AppColors.surfaceCard : null,
            ),
            child: loading
                ? const Padding(
                    padding: EdgeInsets.all(11),
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: AppColors.primary,
                    ),
                  )
                : const Icon(Icons.send_rounded, color: Colors.white, size: 20),
          ),
        ),
      ],
    ),
  );
}
