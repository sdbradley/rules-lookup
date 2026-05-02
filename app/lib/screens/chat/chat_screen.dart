import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../models/governing_body.dart';
import '../../models/message.dart';
import '../../services/api_service.dart';
import '../../services/auth_service.dart';
import '../../widgets/governing_body_selector.dart';
import '../../widgets/message_bubble.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final _inputController = TextEditingController();
  final _scrollController = ScrollController();
  final List<Message> _messages = [];
  GoverningBody? _selectedBody;
  bool _isSending = false;

  @override
  void dispose() {
    _inputController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _sendMessage() async {
    final text = _inputController.text.trim();
    if (text.isEmpty || _isSending) return;

    _inputController.clear();
    setState(() {
      _isSending = true;
      _messages.add(Message(role: MessageRole.user, text: text));
      _messages.add(
          Message(role: MessageRole.assistant, text: '', isLoading: true));
    });
    _scrollToBottom();

    try {
      final result = await context
          .read<ApiService>()
          .query(text, _selectedBody);

      setState(() {
        _messages[_messages.length - 1] = Message(
          role: MessageRole.assistant,
          text: result.answer,
          sources: result.sources,
        );
      });
    } on RateLimitException {
      setState(() {
        _messages[_messages.length - 1] = const Message(
          role: MessageRole.assistant,
          text:
              "You've reached your monthly limit of 20 free queries. Upgrade coming soon!",
        );
      });
    } on ApiException catch (e) {
      setState(() {
        _messages[_messages.length - 1] = Message(
          role: MessageRole.assistant,
          text: 'Something went wrong (error ${e.statusCode}). Please try again.',
        );
      });
    } catch (e) {
      setState(() {
        _messages[_messages.length - 1] = const Message(
          role: MessageRole.assistant,
          text: 'Could not reach the server. Check your connection and try again.',
        );
      });
    } finally {
      if (mounted) setState(() => _isSending = false);
      _scrollToBottom();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: GoverningBodySelector(
          selected: _selectedBody,
          onChanged: (body) => setState(() => _selectedBody = body),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () => context.read<AuthService>().signOut(),
            tooltip: 'Sign out',
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: _messages.isEmpty
                ? _EmptyState(selectedBody: _selectedBody)
                : ListView.builder(
                    controller: _scrollController,
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    itemCount: _messages.length,
                    itemBuilder: (_, i) =>
                        MessageBubble(message: _messages[i]),
                  ),
          ),
          _InputBar(
            controller: _inputController,
            isSending: _isSending,
            onSend: _sendMessage,
          ),
        ],
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({this.selectedBody});

  final GoverningBody? selectedBody;

  @override
  Widget build(BuildContext context) {
    final bodyName = selectedBody?.displayName ?? 'all rulebooks';
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.sports_baseball_outlined,
                size: 64, color: Colors.grey),
            const SizedBox(height: 16),
            Text(
              'Ask a question about $bodyName',
              style: Theme.of(context)
                  .textTheme
                  .bodyLarge
                  ?.copyWith(color: Colors.grey),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}

class _InputBar extends StatelessWidget {
  const _InputBar({
    required this.controller,
    required this.isSending,
    required this.onSend,
  });

  final TextEditingController controller;
  final bool isSending;
  final VoidCallback onSend;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.fromLTRB(
          12, 8, 12, MediaQuery.of(context).padding.bottom + 8),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        border:
            Border(top: BorderSide(color: Theme.of(context).dividerColor)),
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: controller,
              minLines: 1,
              maxLines: 4,
              textInputAction: TextInputAction.send,
              onSubmitted: (_) => onSend(),
              decoration: const InputDecoration(
                hintText: 'Ask a rules question...',
                border: OutlineInputBorder(),
                contentPadding:
                    EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              ),
            ),
          ),
          const SizedBox(width: 8),
          IconButton.filled(
            onPressed: isSending ? null : onSend,
            icon: isSending
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2))
                : const Icon(Icons.send),
          ),
        ],
      ),
    );
  }
}
