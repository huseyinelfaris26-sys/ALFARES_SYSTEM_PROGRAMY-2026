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
