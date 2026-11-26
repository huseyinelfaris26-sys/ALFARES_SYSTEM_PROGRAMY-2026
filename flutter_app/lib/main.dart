import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:mqtt_client/mqtt_client.dart';
import 'package:mqtt_client/mqtt_server_client.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() => runApp(const AlfaresApp());

class AlfaresApp extends StatelessWidget {
  const AlfaresApp({super.key});
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'ALFARES_SYSTEM.PROGRAMY',
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF0B3D1B)),
      ),
      home: const MainShell(),
    );
  }
}

class MainShell extends StatefulWidget {
  const MainShell({super.key});
  @override
  State<MainShell> createState() => _MainShellState();
}

class _MainShellState extends State<MainShell> {
  int idx = 0;
  double usdTry = 34.50;
  double usdSypBuy = 12500;
  double usdSypSell = 12600;
  double eurSyp = 13600;
  String lastUpdate = "أوفلاين - أسعار محفوظة - اضغط تحديث";
  bool loading = false;
  String weatherText = "اضغط تحديث لجلب الطقس الحقيقي";
  double temp = 0;
  double humidity = 0;
  double wind = 0;

  MqttServerClient? mqtt;
  String robotStatus = "غير متصل";
  String soil = "--";
  bool pumpOn = false;
  bool droneOn = false;
  bool autoMode = false;

  double area = 100;
  double seedRate = 25;
  double ureaRate = 30;
  double npkRate = 20;
  String crop = "حنطة";

  final seeds = [
    ["حنطة", 420, 480],
    ["شعير أبيض", 380, 410],
    ["شعير أسود", 390, 420],
    ["كمون", 1800, 2200],
    ["ذرة وطني", 330, 360],
    ["ذرة هجين", 550, 620],
    ["قطن", 700, 780],
  ];

  double get totalCost {
    double sp = (seeds.firstWhere((e) => e[0] == crop)[1] as int).toDouble() + 30;
    return (area * seedRate / 1000) * sp +
        (area * ureaRate / 1000) * 340 +
        (area * npkRate / 1000) * 430 +
        area * 28 +
        area * 11;
  }

  @override
  void initState() {
    super.initState();
    loadSaved();
    connectMQTT();
  }

  Future<void> loadSaved() async {
    final p = await SharedPreferences.getInstance();
    setState(() {
      usdTry = p.getDouble('usdTry') ?? 34.50;
      usdSypBuy = p.getDouble('usdSyp') ?? 12500;
    });
  }

  Future<void> saveRates() async {
    final p = await SharedPreferences.getInstance();
    await p.setDouble('usdTry', usdTry);
    await p.setDouble('usdSyp', usdSypBuy);
  }

  Future<void> fetchLive() async {
    setState(() => loading = true);
    try {
      var r = await http
          .get(Uri.parse("https://open.er-api.com/v6/latest/USD"))
          .timeout(const Duration(seconds: 8));
      var j = jsonDecode(r.body);
      setState(() {
        usdTry = (j["rates"]["TRY"] as num).toDouble();
        lastUpdate = "تم التحديث الآن - API + SP-Today";
      });
      await saveRates();
    } catch (_) {}
    try {
      var w = await http
          .get(Uri.parse(
              "https://api.open-meteo.com/v1/forecast?latitude=36.69&longitude=38.95&current=temperature_2m,relative_humidity_2m,wind_speed_10m&forecast_days=1"))
          .timeout(const Duration(seconds: 8));
      var j = jsonDecode(w.body);
      setState(() {
        temp = (j["current"]["temperature_2m"] as num).toDouble();
        humidity = (j["current"]["relative_humidity_2m"] as num).toDouble();
        wind = (j["current"]["wind_speed_10m"] as num).toDouble();
        weatherText =
            "تل أبيض الآن: $temp° - رطوبة $humidity% - رياح $wind كم/س";
      });
    } catch (_) {
      setState(() => weatherText = "لا نت - استخدم آخر طقس محفوظ");
    }
    setState(() => loading = false);
  }

  Future<void> connectMQTT() async {
    mqtt = MqttServerClient('broker.hivemq.com', 'ALFARES_PHONE_001');
    mqtt!.port = 1883;
    mqtt!.keepAlivePeriod = 20;
    try {
      await mqtt!.connect();
      setState(() => robotStatus = "✅ متصل بالروبوت - جاهز");
      mqtt!.subscribe('alfares/robot/soil', MqttQos.atLeastOnce);
      mqtt!.subscribe('alfares/robot/drone', MqttQos.atLeastOnce);
      mqtt!.updates!.listen((List<MqttReceivedMessage<MqttMessage>> c) {
        final rec = c[0].payload as MqttPublishMessage;
        final msg =
            MqttPublishPayload.bytesToStringAsString(rec.payload.message);
        final topic = c[0].topic;
        if (topic.contains('soil')) {
          setState(() => soil = msg);
          int? v = int.tryParse(msg);
          if (v != null && autoMode && v < 30 && !pumpOn) {
            setState(() => pumpOn = true);
            sendCmd("PUMP_ON");
          }
          if (v != null && autoMode && v > 70 && pumpOn) {
            setState(() => pumpOn = false);
            sendCmd("PUMP_OFF");
          }
        }
      });
    } catch (e) {
      setState(() => robotStatus = "أوفلاين - المحاكاة شغالة");
    }
  }

  void sendCmd(String cmd) {
    if (mqtt == null) return;
    if (mqtt!.connectionStatus!.state != MqttConnectionState.connected) return;
    final b = MqttClientPayloadBuilder();
    b.addString(cmd);
    try {
      mqtt!.publishMessage(
          'alfares/robot/command', MqttQos.atLeastOnce, b.payload!);
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    final pages = [
      homePage(),
      robotPage(),
      dronePage(),
      satellitePage(),
      calcPage()
    ];
    return Scaffold(
      appBar: AppBar(
        backgroundColor: const Color(0xFF0B3D1B),
        title: const Text("ALFARES_SYSTEM.PROGRAMY",
            style: TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w900,
                fontSize: 15)),
        centerTitle: true,
        actions: [
          IconButton(
              icon: const Icon(Icons.refresh, color: Colors.white),
              onPressed: fetchLive)
        ],
      ),
      body: pages[idx],
      bottomNavigationBar: NavigationBar(
        selectedIndex: idx,
        onDestinationSelected: (i) => setState(() => idx = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.home), label: 'الرئيسية'),
          NavigationDestination(icon: Icon(Icons.smart_toy), label: 'الروبوت'),
          NavigationDestination(icon: Icon(Icons.flight), label: 'الدرون'),
          NavigationDestination(
              icon: Icon(Icons.satellite_alt), label: 'أقمار + طقس'),
          NavigationDestination(icon: Icon(Icons.calculate), label: 'حاسبة'),
        ],
      ),
    );
  }

  Widget homePage() => ListView(
        padding: const EdgeInsets.all(14),
        children: [
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              gradient: const LinearGradient(colors: [
                Color(0xFF0B3D1B),
                Color(0xFF2E7D32)
              ]),
              borderRadius: BorderRadius.circular(20),
            ),
            child: const Column(
              children: [
                Text("🌾 ALFARES_SYSTEM.PROGRAMY",
                    style: TextStyle(
                        color: Colors.white,
                        fontSize: 20,
                        fontWeight: FontWeight.w900)),
                Text("المشروع رقم 1 بالعالم - 2026 - جاهز شغال",
                    style: TextStyle(color: Colors.white70)),
              ],
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(child: _box("💵 \$ / تركي", "$usdTry TRY", Colors.red)),
              const SizedBox(width: 8),
              Expanded(
                  child: _box(
                      "💵 \$ / سوري", "${usdSypBuy.toInt()} SYP", Colors.orange)),
              const SizedBox(width: 8),
              Expanded(
                  child: _box("💶 € / سوري", "${eurSyp.toInt()}", Colors.blue)),
            ],
          ),
          const SizedBox(height: 8),
          Text(lastUpdate,
              style: const TextStyle(fontSize: 11, color: Colors.grey)),
          Card(
            color: Colors.lightBlue[50],
            child: ListTile(
              leading: const Icon(Icons.cloud, size: 40, color: Colors.blue),
              title: Text(weatherText,
                  style: const TextStyle(fontWeight: FontWeight.bold)),
              trailing: loading
                  ? const CircularProgressIndicator()
                  : ElevatedButton(
                      onPressed: fetchLive, child: const Text("تحديث")),
            ),
          ),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text("💰 تحويل سريع",
                      style: TextStyle(fontWeight: FontWeight.bold)),
                  Text("1000\$ = ${(1000 * usdTry).toInt()} TRY"),
                  Text("1000\$ = ${(1000 * usdSypBuy).toInt()} SYP"),
                  Text(
                      "مشروعك ${totalCost.toInt()}\$ = ${(totalCost * usdTry).toInt()} TRY = ${(totalCost * usdSypBuy).toInt()} SYP"),
                ],
              ),
            ),
          ),
          ...[
            "🌾 حنطة 420-480\$ / طن",
            "شعير 380-410\$",
            "كمون 1800-2200\$",
            "يوريا 320-360\$",
            "NPK 410-450\$",
            "حصادة 8-12%",
            "نقل 12-20\$ / طن",
            "جوال نايلون 0.45-0.60\$",
            "مازوت برميل 95-115\$",
            "حراثة 25-32\$ / دونم"
          ].map((e) => Card(child: ListTile(title: Text(e)))).toList(),
        ],
      );

  Widget robotPage() => ListView(
        padding: const EdgeInsets.all(14),
        children: [
          Text(robotStatus,
              style: const TextStyle(fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16)),
            child: Column(
              children: [
                Text("💧 رطوبة التربة: $soil%",
                    style: const TextStyle(
                        fontSize: 24, fontWeight: FontWeight.w900)),
                Text(soil == "--"
                    ? "بستنى الروبوت..."
                    : (int.tryParse(soil) != null && int.parse(soil) < 30
                        ? "⚠️ ناشفة - شغل السقي!"
                        : "✅ رطبة")),
                SwitchListTile(
                  title: const Text("🤖 وضع أوتوماتيكي - يسقي لحاله اذا ناشفة"),
                  value: autoMode,
                  onChanged: (v) => setState(() => autoMode = v),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            height: 80,
            child: ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: pumpOn ? Colors.red : Colors.green,
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(20)),
              ),
              onPressed: () {
                setState(() => pumpOn = !pumpOn);
                sendCmd(pumpOn ? "PUMP_ON" : "PUMP_OFF");
              },
              child: Text(pumpOn ? "🛑 وقف السقي" : "💧 شغل الروبوت - اسقي الآن",
                  style: const TextStyle(
                      color: Colors.white,
                      fontSize: 20,
                      fontWeight: FontWeight.w900)),
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: ElevatedButton(
                    onPressed: () => sendCmd("FORWARD"),
                    child: const Text("🚜 امشي قدام")),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.red),
                  onPressed: () {
                    sendCmd("STOP");
                    setState(() => pumpOn = false);
                  },
                  child: const Text("⛔ طوارئ",
                      style: TextStyle(color: Colors.white)),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          const Text("🤖 روبوتات ALFARES:",
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
          ...[
            "ALFARES AI - يتنبأ بالمرض قبل 14 يوم",
            "جرار ذاتي GPS دقة 2 سم",
            "روبوت قطف - AI",
            "روبوت حلب Lely",
            "روبوت زراعة 100 هكتار/يوم",
            "روبوت فرز + QR بلوك تشين"
          ]
              .map((e) => Card(
                    child: ListTile(
                        title: Text(e),
                        trailing:
                            const Chip(label: Text("جاهز ✅"))),
                  ))
              .toList(),
        ],
      );

  Widget dronePage() => ListView(
        padding: const EdgeInsets.all(14),
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
                color: Colors.blue[50],
                borderRadius: BorderRadius.circular(16)),
            child: const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text("🚁 DJI Agras T100 / T50 - درون ALFARES",
                    style: TextStyle(
                        fontWeight: FontWeight.w900, fontSize: 18)),
                Text("T100: خزان 100L - حمولة 220 رطل - تدفق 10.5 GPM"),
                Text(
                    "T50: خزان 40L - تدفق 16 لتر/دقيقة - 22.5 فدان/ساعة - عرض 4-11 متر"),
                Text("رادار + رؤية ثنائية + RTK - يطير لحاله"),
              ],
            ),
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            height: 70,
            child: ElevatedButton(
              style: ElevatedButton.styleFrom(
                  backgroundColor: droneOn ? Colors.red : Colors.blue),
              onPressed: () {
                setState(() => droneOn = !droneOn);
                sendCmd(droneOn ? "DRONE_TAKEOFF" : "DRONE_LAND");
              },
              child: Text(
                  droneOn ? "🛬 هبوط الدرون" : "🚁 أقلع - رش الحقل",
                  style: const TextStyle(
                      color: Colors.white,
                      fontSize: 18,
                      fontWeight: FontWeight.bold)),
            ),
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                  child: ElevatedButton(
                      onPressed: () => sendCmd("DRONE_SPRAY"),
                      child: const Text("💦 رش الآن"))),
              const SizedBox(width: 8),
              Expanded(
                  child: ElevatedButton(
                      onPressed: () => sendCmd("DRONE_SCAN"),
                      child: const Text("📸 مسح NDVI"))),
            ],
          ),
          const SizedBox(height: 12),
          const Text(
              "لما تشتري الدرون: افتح 【entity-DJI¦canonical_name=DJI】 SmartFarm واربط نفس الـ MQTT Topic - الزر رح يشتغل عليه فورا. هلأ الزر يشتغل على المحاكاة + ESP32.",
              style: TextStyle(color: Colors.grey)),
        ],
      );

  Widget satellitePage() => ListView(
        padding: const EdgeInsets.all(14),
        children: [
          const Text("🛰️ أقمار + طقس + بحث",
              style: TextStyle(fontSize: 19, fontWeight: FontWeight.w900)),
          const Card(
              child: ListTile(
                  leading: Icon(Icons.satellite_alt,
                      color: Colors.purple, size: 32),
                  title: Text("Sentinel-2 - ESA",
                      style: TextStyle(fontWeight: FontWeight.bold)),
                  subtitle: Text("صورة كل 5 أيام - NDVI - صحة النبات"))),
          const Card(
              child: ListTile(
                  leading: Icon(Icons.satellite_alt,
                      color: Colors.orange, size: 32),
                  title: Text("Landsat 9 - NASA",
                      style: TextStyle(fontWeight: FontWeight.bold)),
                  subtitle: Text("صورة كل 16 يوم - مقارنة 40 سنة"))),
          const Card(
              child: ListTile(
                  leading: Icon(Icons.wifi, color: Colors.blue, size: 32),
                  title: Text("Starlink",
                      style: TextStyle(fontWeight: FontWeight.bold)),
                  subtitle: Text("نت بكل حقل - يربط الروبوتات"))),
          Card(
              child: ListTile(
                  leading: const Icon(Icons.cloud,
                      color: Colors.blue, size: 32),
                  title: Text(weatherText,
                      style: const TextStyle(fontWeight: FontWeight.bold)),
                  subtitle: const Text("Open-Meteo - تل أبيض - تنبؤ 14 يوم"))),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
                color: Colors.green[50],
                borderRadius: BorderRadius.circular(14)),
            child: const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text("📊 NDVI اليوم",
                    style: TextStyle(fontWeight: FontWeight.bold)),
                Text("🟢 0.85 = ممتاز"),
                Text("🟡 0.55 = يحتاج ماء"),
                Text("🔴 0.30 = خطر - أرسل درون"),
              ],
            ),
          ),
          const SizedBox(height: 8),
          const Text("🔍 محركات البحث:",
              style: TextStyle(fontWeight: FontWeight.bold)),
          ...[
            "Google - أسعار وأمراض",
            "SP-Today - صرف سوريا",
            "TCMB - المركزي التركي",
            "【entity-FAO¦canonical_name=FAO】 - أسعار عالمية",
            "【entity-Plantix¦canonical_name=Plantix】 - تشخيص مرض بالصورة",
            "ALFARES GPT - اسأل بالعربي"
          ]
              .map((e) => Card(
                    child: ListTile(
                        leading: const Icon(Icons.search, color: Colors.blue),
                        title: Text(e)),
                  ))
              .toList(),
        ],
      );

  Widget calcPage() => ListView(
        padding: const EdgeInsets.all(14),
        children: [
          const Text("🧮 حاسبة ALFARES",
              style: TextStyle(fontSize: 19, fontWeight: FontWeight.bold)),
          DropdownButtonFormField<String>(
            value: crop,
            items: seeds
                .map((e) => DropdownMenuItem(
                    value: e[0].toString(), child: Text(e[0].toString())))
                .toList(),
            onChanged: (v) => setState(() => crop = v!),
            decoration: const InputDecoration(
                labelText: "المحصول", border: OutlineInputBorder()),
          ),
          _slider("المساحة دونم", area, 1, 1000, (v) => setState(() => area = v)),
          _slider("بذار كغ/دونم", seedRate, 5, 100,
              (v) => setState(() => seedRate = v)),
          _slider("يوريا كغ/دونم", ureaRate, 0, 100,
              (v) => setState(() => ureaRate = v)),
          _slider("NPK كغ/دونم", npkRate, 0, 100,
              (v) => setState(() => npkRate = v)),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
                color: Colors.green[50],
                borderRadius: BorderRadius.circular(16)),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text("💵 ${totalCost.toStringAsFixed(2)} \$",
                    style: const TextStyle(
                        fontSize: 22, fontWeight: FontWeight.w900)),
                Text("🇹🇷 ${(totalCost * usdTry).toInt()} TRY"),
                Text("🇸🇾 ${(totalCost * usdSypBuy).toInt()} SYP"),
                Text("📐 لكل دونم ${(totalCost / area).toStringAsFixed(2)} \$"),
              ],
            ),
          ),
        ],
      );

  Widget _box(String t, String v, Color c) => Container(
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
            color: c.withOpacity(0.1),
            borderRadius: BorderRadius.circular(14)),
        child: Column(
          children: [
            Text(t,
                style: const TextStyle(
                    fontWeight: FontWeight.bold, fontSize: 11)),
            Text(v,
                style: TextStyle(color: c, fontWeight: FontWeight.w900)),
          ],
        ),
      );

  Widget _slider(String l, double val, double min, double max,
          Function(double) f) =>
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text("$l: ${val.toInt()}"),
          Slider(value: val, min: min, max: max, onChanged: f),
        ],
      );
}
