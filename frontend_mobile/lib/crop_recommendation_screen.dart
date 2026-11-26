import 'package:flutter/material.dart';

class CropRecommendationScreen extends StatefulWidget {
  const CropRecommendationScreen({super.key});

  @override
  State<CropRecommendationScreen> createState() =>
      _CropRecommendationScreenState();
}

class _CropRecommendationScreenState
    extends State<CropRecommendationScreen> {

  final nController = TextEditingController();
  final pController = TextEditingController();
  final kController = TextEditingController();

  String result = "";

  void predictCrop() {

    int n = int.tryParse(nController.text) ?? 0;

    if (n > 80) {
      result = "القمح";
    } else {
      result = "الشعير";
    }

    setState(() {});
  }

  @override
  Widget build(BuildContext context) {

    return Scaffold(
      appBar: AppBar(
        title: const Text("توصية المحصول"),
      ),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [

            TextField(
              controller: nController,
              decoration: const InputDecoration(
                labelText: "N",
              ),
            ),

            TextField(
              controller: pController,
              decoration: const InputDecoration(
                labelText: "P",
              ),
            ),

            TextField(
              controller: kController,
              decoration: const InputDecoration(
                labelText: "K",
              ),
            ),

            const SizedBox(height: 20),

            ElevatedButton(
              onPressed: predictCrop,
              child: const Text(
                "تحليل",
              ),
            ),

            const SizedBox(height: 20),

            Text(
              result,
              style: const TextStyle(
                fontSize: 28,
                fontWeight: FontWeight.bold,
              ),
            )

          ],
        ),
      ),
    );
  }
}
