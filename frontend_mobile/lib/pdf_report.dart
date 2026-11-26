import 'package:flutter/material.dart';

class PdfReport extends StatelessWidget {

  const PdfReport({super.key});

  @override
  Widget build(BuildContext context) {

    return Scaffold(
      appBar: AppBar(
        title: const Text(
          "تقرير PDF",
        ),
      ),

      body: Center(
        child: ElevatedButton(

          onPressed: () {

          },

          child: const Text(
            "إنشاء تقرير PDF",
          ),
        ),
      ),
    );
  }
}
