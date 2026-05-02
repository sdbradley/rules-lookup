import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

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
  DoneEvent(this.sources);
  final List<Source> sources;
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
    GoverningBody? governingBody,
  ) async* {
    final body = <String, dynamic>{'question': question};
    if (governingBody != null) body['governing_body'] = governingBody.apiValue;

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
          yield DoneEvent(sources);
        }
      }
    }
  }
}
