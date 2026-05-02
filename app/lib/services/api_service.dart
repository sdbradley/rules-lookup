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

class QueryResult {
  const QueryResult({required this.answer, required this.sources});
  final String answer;
  final List<Source> sources;
}

class ApiService {
  ApiService(this._auth);

  final AuthService _auth;

  Future<QueryResult> query(
    String question,
    GoverningBody? governingBody,
  ) async {
    final token = await _auth.getIdToken();

    final body = <String, dynamic>{'question': question};
    if (governingBody != null) body['governing_body'] = governingBody.apiValue;

    final response = await http
        .post(
          Uri.parse('$_baseUrl/query'),
          headers: {
            HttpHeaders.contentTypeHeader: 'application/json',
            if (token != null) HttpHeaders.authorizationHeader: 'Bearer $token',
          },
          body: jsonEncode(body),
        )
        .timeout(const Duration(seconds: 30));

    if (response.statusCode == 200) {
      final json = jsonDecode(response.body) as Map<String, dynamic>;
      final sources = (json['sources'] as List)
          .map((s) => Source.fromJson(s as Map<String, dynamic>))
          .toList();
      return QueryResult(answer: json['answer'] as String, sources: sources);
    } else if (response.statusCode == 429) {
      throw const RateLimitException();
    } else {
      throw ApiException(response.statusCode);
    }
  }
}
