import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:provider/provider.dart';

import '../models/message.dart';
import '../services/api_service.dart';

class MessageBubble extends StatelessWidget {
  const MessageBubble({super.key, required this.message});

  final Message message;

  @override
  Widget build(BuildContext context) {
    final isUser = message.role == MessageRole.user;
    final colorScheme = Theme.of(context).colorScheme;

    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: ConstrainedBox(
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.82,
        ),
        child: Column(
          crossAxisAlignment:
              isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
          children: [
            Container(
              margin: const EdgeInsets.symmetric(vertical: 4, horizontal: 12),
              padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 14),
              decoration: BoxDecoration(
                color: isUser
                    ? colorScheme.primary
                    : colorScheme.primaryContainer,
                borderRadius: BorderRadius.circular(16),
              ),
              child: message.isLoading
                  ? const SizedBox(
                      height: 16,
                      width: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : isUser
                      ? Text(
                          message.text,
                          style: TextStyle(color: colorScheme.onPrimary),
                        )
                      : MarkdownBody(
                          data: message.text,
                          styleSheet: MarkdownStyleSheet(
                            p: TextStyle(color: colorScheme.onSurface),
                            strong: TextStyle(
                              color: colorScheme.onSurface,
                              fontWeight: FontWeight.bold,
                            ),
                            em: TextStyle(
                              color: colorScheme.onSurface,
                              fontStyle: FontStyle.italic,
                            ),
                            h1: TextStyle(
                              color: colorScheme.onSurface,
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                            ),
                            h2: TextStyle(
                              color: colorScheme.onSurface,
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                            ),
                            code: TextStyle(
                              color: colorScheme.onSurface,
                              backgroundColor:
                                  colorScheme.surfaceContainerHighest,
                              fontFamily: 'monospace',
                            ),
                            blockquote: TextStyle(color: colorScheme.onSurface),
                            blockquoteDecoration: BoxDecoration(
                              color: colorScheme.surfaceContainerHighest,
                              borderRadius: BorderRadius.circular(4),
                              border: Border(
                                left: BorderSide(
                                  color: colorScheme.primary,
                                  width: 4,
                                ),
                              ),
                            ),
                          ),
                        ),
            ),
            if (message.sources.isNotEmpty)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                child: Wrap(
                  spacing: 6,
                  runSpacing: 4,
                  children: message.sources
                      .map((s) => _SourceChip(source: s))
                      .toList(),
                ),
              ),
            if (!isUser && !message.isLoading && message.logId != null)
              _FeedbackButtons(logId: message.logId!),
          ],
        ),
      ),
    );
  }
}

class _FeedbackButtons extends StatefulWidget {
  const _FeedbackButtons({required this.logId});

  final String logId;

  @override
  State<_FeedbackButtons> createState() => _FeedbackButtonsState();
}

class _FeedbackButtonsState extends State<_FeedbackButtons> {
  String? _rating;

  void _submit(String rating) {
    final next = _rating == rating ? null : rating;
    setState(() => _rating = next);
    if (next != null) {
      context.read<ApiService>().submitFeedback(widget.logId, next);
    }
  }

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.only(left: 12, top: 2, bottom: 4),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          IconButton(
            iconSize: 18,
            visualDensity: VisualDensity.compact,
            icon: Icon(
              _rating == 'up' ? Icons.thumb_up : Icons.thumb_up_outlined,
              color: _rating == 'up' ? colorScheme.primary : colorScheme.outline,
            ),
            onPressed: () => _submit('up'),
            tooltip: 'Helpful',
          ),
          IconButton(
            iconSize: 18,
            visualDensity: VisualDensity.compact,
            icon: Icon(
              _rating == 'down' ? Icons.thumb_down : Icons.thumb_down_outlined,
              color: _rating == 'down' ? colorScheme.error : colorScheme.outline,
            ),
            onPressed: () => _submit('down'),
            tooltip: 'Not helpful',
          ),
        ],
      ),
    );
  }
}

class _SourceChip extends StatelessWidget {
  const _SourceChip({required this.source});

  final Source source;

  @override
  Widget build(BuildContext context) {
    return Chip(
      label: Text(source.citation,
          style: Theme.of(context).textTheme.labelSmall),
      padding: EdgeInsets.zero,
      materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
    );
  }
}
