import 'dart:convert';
import 'package:http/http.dart' as http;
import 'api_service.dart';

class CropService {

  static Future<Map<String,dynamic>>
  recommend(Map<String,dynamic> data)
  async {

    final response =
        await http.post(

      Uri.parse(
        "${ApiService.baseUrl}/crop/recommend",
      ),

      headers: {
        "Content-Type":
        "application/json"
      },

      body: jsonEncode(data),
    );

    return jsonDecode(
      response.body,
    );
  }
}
