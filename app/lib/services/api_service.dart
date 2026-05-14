import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import '../models/conversation.dart';
import '../models/governing_body.dart';
import '../models/message.dart';
import 'auth_service.dart';

const _baseUrl =
    'https://rules-lookup-api-396650179371.us-central1.run.app';

class RateLimitException implements Exception {
  const RateLimitException();
}

class ApiException implements Exception {
  const ApiException(this.statusCode, [this.message]);
  final int statusCode;
  final String? message;
}

sealed class StreamEvent {}

class TextEvent extends StreamEvent {
  TextEvent(this.text);
  final String text;
}

class DoneEvent extends StreamEvent {
  DoneEvent(this.sources, this.conversationId, this.logId);
  final List<Source> sources;
  final String conversationId;
  final String? logId;
}

class ApiService {
  ApiService(this._auth);

  final AuthService _auth;

  Future<Map<String, String>> _headers() async {
    final token = await _auth.getIdToken();
    return {
      HttpHeaders.contentTypeHeader: 'application/json',
      if (token != null) HttpHeaders.authorizationHeader: 'Bearer $token',
    };
  }

  Stream<StreamEvent> queryStream(
    String question,
    GoverningBody? governingBody, {
    String? conversationId,
    List<Map<String, String>>? messages,
  }) async* {
    final body = <String, dynamic>{'question': question};
    if (governingBody != null) body['governing_body'] = governingBody.apiValue;
    if (conversationId != null) body['conversation_id'] = conversationId;
    if (messages != null && messages.isNotEmpty) body['messages'] = messages;

    final request =
        http.Request('POST', Uri.parse('$_baseUrl/query/stream'));
    request.headers.addAll(await _headers());
    request.body = jsonEncode(body);

    final streamedResponse = await http.Client()
        .send(request)
        .timeout(const Duration(seconds: 15));

    if (streamedResponse.statusCode == 429) throw const RateLimitException();
    if (streamedResponse.statusCode != 200) {
      throw ApiException(streamedResponse.statusCode);
    }

    String buffer = '';
    await for (final chunk
        in streamedResponse.stream.transform(utf8.decoder)) {
      buffer += chunk;
      final lines = buffer.split('\n');
      buffer = lines.last;
      for (final line in lines.take(lines.length - 1)) {
        if (!line.startsWith('data: ')) continue;
        final data = jsonDecode(line.substring(6)) as Map<String, dynamic>;
        if (data['type'] == 'text') {
          yield TextEvent(data['text'] as String);
        } else if (data['type'] == 'done') {
          final sources = (data['sources'] as List)
              .map((s) => Source.fromJson(s as Map<String, dynamic>))
              .toList();
          final convId = data['conversation_id'] as String? ?? '';
          final logId = data['log_id'] as String?;
          yield DoneEvent(sources, convId, logId);
        }
      }
    }
  }

  Future<List<Conversation>> getConversations() async {
    final response = await http.get(
      Uri.parse('$_baseUrl/conversations'),
      headers: await _headers(),
    );
    if (response.statusCode != 200) {
      throw ApiException(response.statusCode);
    }
    final list = jsonDecode(response.body) as List;
    return list
        .map((c) => Conversation.fromJson(c as Map<String, dynamic>))
        .toList();
  }

  Future<void> submitFeedback(String logId, String rating) async {
    await http.post(
      Uri.parse('$_baseUrl/feedback'),
      headers: await _headers(),
      body: jsonEncode({'log_id': logId, 'rating': rating}),
    );
  }

  Future<Conversation> getConversationDetail(String conversationId) async {
    final response = await http.get(
      Uri.parse('$_baseUrl/conversations/$conversationId'),
      headers: await _headers(),
    );
    if (response.statusCode != 200) {
      throw ApiException(response.statusCode);
    }
    return Conversation.fromJson(
        jsonDecode(response.body) as Map<String, dynamic>);
  }
}
