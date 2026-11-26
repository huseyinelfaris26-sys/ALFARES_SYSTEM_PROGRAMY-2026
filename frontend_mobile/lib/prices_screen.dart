import 'package:flutter/material.dart';

class PricesScreen extends StatelessWidget {

  const PricesScreen({super.key});

  @override
  Widget build(BuildContext context) {

    return Scaffold(

      appBar: AppBar(
        title: const Text(
          "الأسعار الزراعية",
        ),
      ),

      body: ListView(

        children: const [

          ListTile(
            title: Text("الدولار"),
            trailing: Text("15000"),
          ),

          ListTile(
            title: Text("القمح"),
            trailing: Text("450"),
          ),

          ListTile(
            title: Text("الشعير"),
            trailing: Text("390"),
          ),

        ],
      ),
    );
  }
}
