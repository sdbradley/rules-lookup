import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'screens/auth/login_screen.dart';
import 'screens/chat/chat_screen.dart';
import 'services/auth_service.dart';

class RulesLookupApp extends StatelessWidget {
  const RulesLookupApp({super.key});

  @override
  Widget build(BuildContext context) {
    return Provider(
      create: (_) => AuthService(),
      child: MaterialApp(
        title: 'Rules Lookup',
        theme: ThemeData(
          colorSchemeSeed: Colors.deepOrange,
          useMaterial3: true,
        ),
        home: const _AuthGate(),
      ),
    );
  }
}

class _AuthGate extends StatelessWidget {
  const _AuthGate();

  @override
  Widget build(BuildContext context) {
    return StreamBuilder<User?>(
      stream: context.read<AuthService>().userStream,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Scaffold(
            body: Center(child: CircularProgressIndicator()),
          );
        }
        return snapshot.hasData ? const ChatScreen() : const LoginScreen();
      },
    );
  }
}
