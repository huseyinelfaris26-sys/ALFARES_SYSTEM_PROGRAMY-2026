import 'package:flutter/material.dart';
import 'login_screen.dart';

void main() {
  runApp(const AlfaresApp());
}

class AlfaresApp extends StatelessWidget {
  const AlfaresApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: "ALFARES SMART AGRICULTURE",
      theme: ThemeData(
        primarySwatch: Colors.green,
      ),
      home: const LoginScreen(),
    );
  }
}
