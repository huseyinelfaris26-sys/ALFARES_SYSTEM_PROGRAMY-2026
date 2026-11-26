![ALFARES Logo](assets/logo.png)

# 🌾 ALFARES_SYSTEM.PROGRAMY - 2026
### المشروع الزراعي الذكي رقم 1 بالعالم

![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)
![Flutter](https://img.shields.io/badge/Flutter-3.27-blue.svg)
![Python](https://img.shields.io/badge/Python-3.12-yellow.svg)
![ESP32](https://img.shields.io/badge/ESP32-IoT-red.svg)
![Drone](https://img.shields.io/badge/Drone-DJI_T50_T100-orange.svg)

> روبوت + درون + أقمار صناعية + طقس + صرف + بحث
> زر واحد يشغل الروبوت الحقيقي من جوالك

---
# ALFARES_SYSTEM.PROGRAMY - المشروع رقم 1 بالعالم - 2026
## أضخم مشروع زراعي ذكي - جاهز شغال

### كيف تشغل بدون الأجهزة والمعدات 
1. Flutter: افتح flutter_app في Android Studio -> Run
2. Python: pip install -r python_backend/requirements.txt -> streamlit run python_backend/app.py
3. ESP32: ارفع esp32/alfares_robot.ino لما تشتري القطع

### لما تشتري القطع بعدين
- الدرون: DJI Agras T100 (100L) او T50 (40L)
- الحساسات: SenseCAP S2105 + Ecowitt WH51
- العقل: ESP32-S3 + Raspberry Pi 5
- اللابتوب: Windows 11 - 16GB RAM

### Topics MQTT - لا تغيرها
- alfares/robot/command : PUMP_ON, PUMP_OFF, FORWARD, STOP, DRONE_TAKEOFF, DRONE_SPRAY
- alfares/robot/soil : رطوبة التربة
- alfares/robot/drone : حالة الدرون

© ALFARES_SYSTEM.PROGRAMY 2026
