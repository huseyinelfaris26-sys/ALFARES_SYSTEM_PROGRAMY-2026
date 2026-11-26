import 'package:flutter/material.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  Widget buildCard(
    String title,
    IconData icon,
    Color color,
  ) {
    return Card(
      elevation: 5,
      child: ListTile(
        leading: Icon(icon,color: color,size: 35),
        title: Text(title),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {

    return Scaffold(
      appBar: AppBar(
        title: const Text(
          "ALFARES SYSTEM",
        ),
      ),

      body: ListView(
        padding: const EdgeInsets.all(12),
        children: [

          buildCard(
              "توصية المحاصيل",
              Icons.agriculture,
              Colors.green),

          buildCard(
              "كشف الأمراض",
              Icons.health_and_safety,
              Colors.red),

          buildCard(
              "الأقمار الصناعية",
              Icons.satellite_alt,
              Colors.blue),

          buildCard(
              "الروبوت الزراعي",
              Icons.precision_manufacturing,
              Colors.orange),

          buildCard(
              "الطقس الزراعي",
              Icons.cloud,
              Colors.indigo),

          buildCard(
              "التقارير PDF",
              Icons.picture_as_pdf,
              Colors.deepPurple),

          buildCard(
              "المساعد الزراعي الذكي",
              Icons.smart_toy,
              Colors.teal),

        ],
      ),
    );
  }
}
