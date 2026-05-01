enum MessageRole { user, assistant }

class Source {
  const Source({
    required this.governingBody,
    required this.sourceDoc,
    this.ruleNumber,
    this.sectionTitle,
    this.pageNumber,
  });

  final String governingBody;
  final String sourceDoc;
  final String? ruleNumber;
  final String? sectionTitle;
  final int? pageNumber;

  factory Source.fromJson(Map<String, dynamic> json) => Source(
        governingBody: json['governing_body'] as String,
        sourceDoc: json['source_doc'] as String,
        ruleNumber: json['rule_number'] as String?,
        sectionTitle: json['section_title'] as String?,
        pageNumber: json['page_number'] as int?,
      );

  String get citation {
    final parts = [governingBody];
    if (ruleNumber != null) parts.add('Rule $ruleNumber');
    if (sectionTitle != null) parts.add(sectionTitle!);
    return parts.join(' — ');
  }
}

class Message {
  const Message({
    required this.role,
    required this.text,
    this.sources = const [],
    this.isLoading = false,
  });

  final MessageRole role;
  final String text;
  final List<Source> sources;
  final bool isLoading;

  Message copyWith({String? text, List<Source>? sources, bool? isLoading}) =>
      Message(
        role: role,
        text: text ?? this.text,
        sources: sources ?? this.sources,
        isLoading: isLoading ?? this.isLoading,
      );
}
