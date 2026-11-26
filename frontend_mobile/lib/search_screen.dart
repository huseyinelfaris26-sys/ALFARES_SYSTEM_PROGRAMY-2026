import 'package:flutter/material.dart';

class SearchScreen extends StatefulWidget {

  const SearchScreen({super.key});

  @override
  State<SearchScreen> createState() =>
      _SearchScreenState();
}

class _SearchScreenState
    extends State<SearchScreen> {

  final controller =
      TextEditingController();

  String result = "";

  @override
  Widget build(BuildContext context) {

    return Scaffold(

      appBar: AppBar(
        title: const Text(
          "البحث الزراعي",
        ),
      ),

      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(

          children: [

            TextField(
              controller: controller,
              decoration: const InputDecoration(
                hintText: "ابحث...",
              ),
            ),

            const SizedBox(height: 20),

            ElevatedButton(
              onPressed: () {
                setState(() {
                  result =
                      controller.text;
                });
              },
              child: const Text(
                "بحث",
              ),
            ),

            const SizedBox(height: 20),

            Text(result),

          ],

        ),
      ),
    );
  }
}
