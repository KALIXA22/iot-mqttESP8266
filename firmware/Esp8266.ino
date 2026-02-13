#include <ESP8266WiFi.h>
#include <PubSubClient.h> 
#include <SPI.h>
#include <MFRC522.h>     
#include <ArduinoJson.h> 
#include <map> // Multi-card support

// --- Configuration ---
const char* ssid = "EdNet";
const char* password = "Huawei@123";
const char* mqtt_server = "157.173.101.159";
const char* team_id = "kaliza07";

String topic_status = "rfid/kaliza07/card/status";
String topic_topup  = "rfid/kaliza07/card/topup";
String topic_balance = "rfid/kaliza07/card/balance";

// --- Global State ---
std::map<String, int> card_ledger; 

#define SS_PIN 5  
#define RST_PIN 4 
MFRC522 mfrc522(SS_PIN, RST_PIN); 

WiFiClient espClient;
PubSubClient client(espClient);

void callback(char* topic, byte* payload, unsigned int length) {
  Serial.println("[DEBUG] MQTT message received");
  Serial.print("Topic: "); Serial.println(topic);

  StaticJsonDocument<200> doc;
  DeserializationError err = deserializeJson(doc, payload, length);
  if (err) {
    Serial.print("[ERROR] JSON parse failed: "); Serial.println(err.c_str());
    return;
  }

  String uid = doc["uid"].as<String>();
  int topup_amount = doc["amount"];

  Serial.printf("[DEBUG] Top-up command for UID: %s, Amount: %d\n", uid.c_str(), topup_amount);

  card_ledger[uid] += topup_amount;
  Serial.printf("[DEBUG] New balance for %s: %d\n", uid.c_str(), card_ledger[uid]);

  // Notify backend/dashboard
  StaticJsonDocument<200> response;
  response["uid"] = uid;
  response["new_balance"] = card_ledger[uid]; 
    
  char buffer[256];
  serializeJson(response, buffer);
  client.publish(topic_balance.c_str(), buffer);
  Serial.println("[DEBUG] Published new balance to MQTT");
}

void setup() {
  Serial.begin(115200);
  Serial.println("[INFO] Starting ESP8266...");
  
  SPI.begin();
  mfrc522.PCD_Init();
  Serial.println("[INFO] RFID reader initialized");

  WiFi.begin(ssid, password);
  Serial.print("[INFO] Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) { 
    delay(500); 
    Serial.print(".");
  }
  Serial.println("\n[INFO] WiFi connected!");
  Serial.print("[INFO] IP address: "); Serial.println(WiFi.localIP());

  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);
}

void reconnect() {
  while (!client.connected()) {
    Serial.println("[INFO] Attempting MQTT connection...");
    if (client.connect(team_id)) {
      Serial.println("[INFO] MQTT connected!");
      client.subscribe(topic_topup.c_str());
      Serial.println("[INFO] Subscribed to topic: " + topic_topup);
    } else {
      Serial.print("[WARN] MQTT connect failed, rc=");
      Serial.print(client.state());
      Serial.println(" retrying in 5s");
      delay(5000);
    }
  }
}

void loop() {
  if (!client.connected()) reconnect();
  client.loop(); 

  if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()) {
    String uid = "";
    for (byte i = 0; i < mfrc522.uid.size; i++) {
      uid += String(mfrc522.uid.uidByte[i] < 0x10 ? "0" : "");
      uid += String(mfrc522.uid.uidByte[i], HEX);
    }
    uid.toUpperCase();

    Serial.printf("[INFO] Card detected: %s\n", uid.c_str());

    int my_balance = card_ledger[uid]; 
    Serial.printf("[INFO] Current balance for this card: %d\n", my_balance);

    StaticJsonDocument<200> doc;
    doc["uid"] = uid;
    doc["balance"] = my_balance;
    
    char buffer[256];
    serializeJson(doc, buffer);
    client.publish(topic_status.c_str(), buffer);
    Serial.println("[DEBUG] Published card balance to MQTT");

    mfrc522.PICC_HaltA(); 
    mfrc522.PCD_StopCrypto1();
    Serial.println("[DEBUG] Card halted and reader ready for next");
  }
}
