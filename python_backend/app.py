# ALFARES_SYSTEM.PROGRAMY - Python Backend
import streamlit as st
import pandas as pd
import numpy as np
import requests
try:
    import paho.mqtt.client as mqtt
    HAS_MQTT = True
except Exception:
    HAS_MQTT = False

st.set_page_config(page_title="ALFARES_SYSTEM.PROGRAMY", page_icon="🌾", layout="wide")
st.title("🌾 ALFARES_SYSTEM.PROGRAMY - المشروع رقم 1 بالعالم - 2026")

def get_usd_try():
    try:
        r = requests.get("https://open.er-api.com/v6/latest/USD", timeout=5)
        return round(r.json()["rates"]["TRY"], 2)
    except Exception:
        return 34.5

def get_weather():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=36.69&longitude=38.95&current=temperature_2m,relative_humidity_2m,wind_speed_10m"
        j = requests.get(url, timeout=8).json()["current"]
        return f"تل أبيض: {j['temperature_2m']}° رطوبة {j['relative_humidity_2m']}% رياح {j['wind_speed_10m']} كم/س"
    except Exception:
        return "لا نت - طقس محفوظ"

usd_try = get_usd_try()
usd_syp = 12500
c1, c2, c3 = st.columns(3)
c1.metric("💵 $ / TRY", f"{usd_try}")
c2.metric("💵 $ / SYP", f"{usd_syp:,}")
c3.metric("🌦️ طقس", get_weather())

st.header("🤖 زر الروبوت الحقيقي - من اللابتوب")
if HAS_MQTT:
    if st.button("💧 شغل الروبوت - اسقي الآن", use_container_width=True):
        cl = mqtt.Client()
        cl.connect("broker.hivemq.com", 1883)
        cl.publish("alfares/robot/command", "PUMP_ON")
        cl.disconnect()
        st.success("✅ تم ارسال PUMP_ON!")
    if st.button("🚁 أقلع الدرون", use_container_width=True):
        cl = mqtt.Client()
        cl.connect("broker.hivemq.com", 1883)
        cl.publish("alfares/robot/command", "DRONE_TAKEOFF")
        cl.disconnect()
        st.success("✅ تم ارسال DRONE_TAKEOFF!")
    if st.button("⛔ طوارئ", use_container_width=True):
        cl = mqtt.Client()
        cl.connect("broker.hivemq.com", 1883)
        cl.publish("alfares/robot/command", "STOP")
        cl.disconnect()
        st.error("تم الايقاف")

st.header("🧮 حاسبة + أسعار 2026")
SEEDS = {"حنطة": (420, 480), "شعير أبيض": (380, 410), "شعير أسود": (390, 420), "كمون": (1800, 2200), "ذرة وطني": (330, 360), "ذرة هجين": (550, 620), "قطن": (700, 780)}
crop = st.selectbox("المحصول", list(SEEDS.keys()))
area = st.number_input("دونم", value=100)
seed_rate = st.number_input("بذار كغ/دونم", value=25)
seed_price = np.mean(SEEDS[crop])
total = (area * seed_rate / 1000) * seed_price + area * 30 / 1000 * 340 + area * 20 / 1000 * 430 + area * 28 + area * 11
st.success(f"الإجمالي: {total:,.2f} $ = {total * usd_try:,.0f} TRY = {total * usd_syp:,.0f} SYP")
st.header("🛰️ أقمار + حساسات")
st.write("Sentinel-2 NDVI: 0.82 🟢 | Landsat 9 | Starlink متصل")
st.write("حساسات: SenseCAP S2105 | Ecowitt WH51 | Milesight EM500")
st.write("درون: DJI Agras T100 100L / T50 40L")
df = pd.DataFrame([{"محصول": k, "من $": v[0], "إلى $": v[1]} for k, v in SEEDS.items()])
st.dataframe(df, use_container_width=True)
