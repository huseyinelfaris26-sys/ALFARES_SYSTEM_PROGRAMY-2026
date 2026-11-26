import 'package:flutter/material.dart';

class SatelliteScreen extends StatelessWidget {

  const SatelliteScreen({super.key});

  @override
  Widget build(BuildContext context) {

    return Scaffold(

      appBar: AppBar(
        title: const Text(
          "الأقمار الصناعية",
        ),
      ),

      body: Stack(
        fit: StackFit.expand,
        children: [

          Image.asset(
            "assets/images/satellite_bg.jpg",
            fit: BoxFit.cover,
          ),

          Container(
            color: Colors.black45,
          ),

          const Center(
            child: Text(
              "NDVI Sentinel-2",
              style: TextStyle(
                color: Colors.white,
                fontSize: 30,
              ),
            ),
          ),

        ],
      ),
    );
  }
}
