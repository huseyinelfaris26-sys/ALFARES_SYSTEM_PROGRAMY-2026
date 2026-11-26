import 'package:flutter/material.dart';

class RobotScreen extends StatelessWidget {

  const RobotScreen({super.key});

  @override
  Widget build(BuildContext context) {

    return Scaffold(

      appBar: AppBar(
        title: const Text(
          "الروبوت الزراعي",
        ),
      ),

      body: Column(
        mainAxisAlignment:
            MainAxisAlignment.center,
        children: [

          Center(
            child: Icon(
              Icons.precision_manufacturing,
              size: 120,
              color: Colors.green,
            ),
          ),

          const SizedBox(height: 20),

          ElevatedButton(
            onPressed: () {},
            child: const Text(
              "تشغيل ESP32",
            ),
          ),

          ElevatedButton(
            onPressed: () {},
            child: const Text(
              "تشغيل الدرون",
            ),
          )

        ],
      ),
    );
  }
}
