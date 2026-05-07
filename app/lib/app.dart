import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'screens/auth/login_screen.dart';
import 'screens/chat/chat_screen.dart';
import 'services/api_service.dart';
import 'services/auth_service.dart';
import 'services/subscription_service.dart';

class RulesLookupApp extends StatelessWidget {
  const RulesLookupApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        Provider(create: (_) => AuthService()),
        ProxyProvider<AuthService, ApiService>(
          update: (_, auth, __) => ApiService(auth),
        ),
      ],
      child: MaterialApp(
        title: 'RulesAI',
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(
            seedColor: const Color(0xFF2D7FE6),
          ),
          useMaterial3: true,
        ),
        darkTheme: ThemeData(
          colorScheme: ColorScheme.fromSeed(
            seedColor: const Color(0xFF2D7FE6),
            brightness: Brightness.dark,
          ).copyWith(surface: const Color(0xFF011A38)),
          useMaterial3: true,
        ),
        themeMode: ThemeMode.system,
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
        if (snapshot.hasData) {
          SubscriptionService.initialize(snapshot.data!.uid);
          return const ChatScreen();
        }
        return const LoginScreen();
      },
    );
  }
}
