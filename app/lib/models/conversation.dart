import 'message.dart';

class Conversation {
  const Conversation({
    required this.id,
    required this.preview,
    required this.createdAt,
    this.governingBody,
    this.messages = const [],
  });

  final String id;
  final String preview;
  final DateTime createdAt;
  final String? governingBody;
  final List<ConversationMessage> messages;

  factory Conversation.fromJson(Map<String, dynamic> json) => Conversation(
        id: json['id'] as String,
        preview: json['preview'] as String,
        createdAt: DateTime.parse(json['created_at'] as String),
        governingBody: json['governing_body'] as String?,
        messages: json['messages'] != null
            ? (json['messages'] as List)
                .map((m) => ConversationMessage.fromJson(m as Map<String, dynamic>))
                .toList()
            : const [],
      );
}

class ConversationMessage {
  const ConversationMessage({
    required this.id,
    required this.role,
    required this.content,
    required this.createdAt,
    this.sources = const [],
  });

  final String id;
  final String role;
  final String content;
  final DateTime createdAt;
  final List<Source> sources;

  factory ConversationMessage.fromJson(Map<String, dynamic> json) =>
      ConversationMessage(
        id: json['id'] as String,
        role: json['role'] as String,
        content: json['content'] as String,
        createdAt: DateTime.parse(json['created_at'] as String),
        sources: json['sources'] != null
            ? (json['sources'] as List)
                .map((s) => Source.fromJson(s as Map<String, dynamic>))
                .toList()
            : const [],
      );
}
