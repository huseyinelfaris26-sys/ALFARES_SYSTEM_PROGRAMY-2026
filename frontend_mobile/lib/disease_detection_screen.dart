import 'dart:io';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

class DiseaseDetectionScreen extends StatefulWidget {
  const DiseaseDetectionScreen({super.key});

  @override
  State<DiseaseDetectionScreen> createState() =>
      _DiseaseDetectionScreenState();
}

class _DiseaseDetectionScreenState
    extends State<DiseaseDetectionScreen> {

  File? image;

  Future pickImage() async {

    final picked =
        await ImagePicker().pickImage(
      source: ImageSource.gallery,
    );

    if (picked == null) return;

    setState(() {
      image = File(
        picked.path,
      );
    });
  }

  @override
  Widget build(BuildContext context) {

    return Scaffold(
      appBar: AppBar(
        title: const Text(
          "كشف الأمراض",
        ),
      ),
      body: Center(
        child: Column(
          children: [

            const SizedBox(height: 20),

            ElevatedButton(
              onPressed: pickImage,
              child: const Text(
                "اختيار صورة",
              ),
            ),

            const SizedBox(height: 20),

            image == null
                ? const Text(
                    "لا توجد صورة",
                  )
                : Image.file(
                    image!,
                    height: 250,
                  ),

            const SizedBox(height: 20),

            const Text(
              "سيتم إرسال الصورة إلى نموذج الذكاء الاصطناعي",
            )

          ],
        ),
      ),
    );
  }
}
