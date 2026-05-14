import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../models/conversation.dart';
import '../../models/message.dart';
import '../../services/api_service.dart';
import '../../widgets/message_bubble.dart';

class ConversationDetailScreen extends StatefulWidget {
  const ConversationDetailScreen({super.key, required this.conversation});

  final Conversation conversation;

  @override
  State<ConversationDetailScreen> createState() =>
      _ConversationDetailScreenState();
}

class _ConversationDetailScreenState extends State<ConversationDetailScreen> {
  late Future<Conversation> _future;

  @override
  void initState() {
    super.initState();
    _future = context
        .read<ApiService>()
        .getConversationDetail(widget.conversation.id);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(
          widget.conversation.preview,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
      ),
      body: FutureBuilder<Conversation>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return const Center(
                child: Text('Could not load conversation.'));
          }
          final conv = snapshot.data!;
          if (conv.messages.isEmpty) {
            return const Center(child: Text('No messages.'));
          }
          return ListView.builder(
            padding: const EdgeInsets.symmetric(vertical: 12),
            itemCount: conv.messages.length,
            itemBuilder: (_, i) {
              final msg = conv.messages[i];
              final isAssistant = msg.role == 'assistant';
              final question = isAssistant && i > 0
                  ? conv.messages[i - 1].content
                  : null;
              return MessageBubble(
                message: Message(
                  role: isAssistant ? MessageRole.assistant : MessageRole.user,
                  text: msg.content,
                  sources: msg.sources,
                ),
                question: question,
              );
            },
          );
        },
      ),
    );
  }
}
