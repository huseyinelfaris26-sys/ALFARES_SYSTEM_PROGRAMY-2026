// ALFARES_ROBOT_V1 - ESP32
#include <WiFi.h>
#include <PubSubClient.h>
const char* ssid = "اسم_الواي_فاي";
const char* password = "كلمة_السر";
const char* mqtt_server = "broker.hivemq.com";
WiFiClient espClient;
PubSubClient client(espClient);
#define PUMP 26
#define MOTOR_R 27
#define MOTOR_L 14
#define SOIL_SENSOR 32
void setup() {
  Serial.begin(115200);
  pinMode(PUMP, OUTPUT);
  pinMode(MOTOR_R, OUTPUT);
  pinMode(MOTOR_L, OUTPUT);
  digitalWrite(PUMP, LOW);
  digitalWrite(MOTOR_R, LOW);
  digitalWrite(MOTOR_L, LOW);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.println("WiFi Connected!");
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);
}
void callback(char* topic, byte* payload, unsigned int length) {
  String msg = "";
  for (unsigned int i = 0; i < length; i++) msg += (char)payload[i];
  Serial.println("أمر: " + msg);
  if (msg == "PUMP_ON") digitalWrite(PUMP, HIGH);
  if (msg == "PUMP_OFF") digitalWrite(PUMP, LOW);
  if (msg == "FORWARD") {
    digitalWrite(MOTOR_R, HIGH);
    digitalWrite(MOTOR_L, HIGH);
    delay(2000);
    digitalWrite(MOTOR_R, LOW);
    digitalWrite(MOTOR_L, LOW);
  }
  if (msg == "STOP") { digitalWrite(PUMP, LOW); digitalWrite(MOTOR_R, LOW); digitalWrite(MOTOR_L, LOW); }
}
void reconnect() {
  while (!client.connected()) {
    if (client.connect("ALFARES_ROBOT_001")) {
      client.subscribe("alfares/robot/command");
      Serial.println("MQTT Connected");
    } else delay(2000);
  }
}
void loop() {
  if (!client.connected()) reconnect();
  client.loop();
  int soil = analogRead(SOIL_SENSOR);
  int moisture = map(soil, 4095, 0, 0, 100);
  char buf[10];
  itoa(moisture, buf, 10);
  client.publish("alfares/robot/soil", buf);
  delay(10000);
}
