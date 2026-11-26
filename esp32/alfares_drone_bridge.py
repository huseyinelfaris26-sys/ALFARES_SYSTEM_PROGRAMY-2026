# DRONE BRIDGE - يربط زر Flutter مع درون DJI
import paho.mqtt.client as mqtt
print("ALFARES DRONE BRIDGE - جاهز")
def on_message(client, userdata, msg):
    cmd = msg.payload.decode()
    print(f"امر درون: {cmd}")
    if cmd == "DRONE_TAKEOFF":
        print(">>> DJI: اقلاع - ارتفاع 3 متر")
    elif cmd == "DRONE_SPRAY":
        print(">>> DJI: رش - 16 لتر/دقيقة")
    elif cmd == "DRONE_SCAN":
        print(">>> DJI: مسح NDVI")
    elif cmd == "DRONE_LAND":
        print(">>> DJI: هبوط آمن")
client = mqtt.Client()
client.on_message = on_message
client.connect("broker.hivemq.com", 1883)
client.subscribe("alfares/robot/command")
client.loop_forever()
