/*
 * ==============================================================================
 * Central Pier Arcade — IoT Ticket Dispenser Monitoring Node
 * Firmware: esp32_ticket_sensor.ino
 * Target Hardware: ESP32 DevKit v1 / NodeMCU-32S
 * Sensors: 6x FC-51 Infrared Proximity / Obstacle Sensors (Active-Low)
 * Architecture: 1 ESP32 node monitors a 6-machine island
 * ==============================================================================
 * Description:
 *   Continuously monitors ticket hopper levels across 6 arcade machines.
 *   Implements a 5-second non-blocking debounce filter using millis() to prevent
 *   false alarms caused by mechanical vibration or ticket motion during play.
 *   Dispatches HTTP POST alerts with JSON payloads to the FastAPI backend.
 * ==============================================================================
 */

#include <WiFi.h>
#include <HTTPClient.h>

// ==========================================
// 1. Wi-Fi & Backend Configuration
// ==========================================
const char* WIFI_SSID     = "CentralPier-Ops-WiFi";
const char* WIFI_PASSWORD = "ArcadeSecureKey2024";

// Backend FastAPI Server Endpoint
// Replace with your server's LAN IP (e.g., http://192.168.1.100:8000/api/iot/sensor-alert)
const char* SERVER_URL    = "http://192.168.1.100:8000/api/iot/sensor-alert";
const char* IOT_API_KEY   = "arcade-iot-dev-key";
const char* NODE_ID       = "esp32-island-01";

// ==========================================
// 2. Hardware Pinout & Timing Constants
// ==========================================
#define NUM_CHANNELS 6
const unsigned long DEBOUNCE_DELAY_MS   = 5000;   // 5.0 seconds continuous state required
const unsigned long WIFI_RETRY_INTERVAL = 10000;  // 10 seconds Wi-Fi reconnect timer
const unsigned long HEARTBEAT_INTERVAL  = 300000; // 5 minutes periodic heartbeat per channel

// FC-51 Active-Low Logic:
// - TICKET STACK PRESENT: Sensor output = LOW  (0V), onboard D0 LED is ON
// - TICKET STACK DEPLETED: Sensor output = HIGH (3.3V), onboard D0 LED is OFF
#define TICKET_DETECTED LOW
#define TICKET_DEPLETED HIGH

struct MachineSensor {
  int pin;
  int machineId;
  const char* machineName;
  int candidateState;
  unsigned long candidateStartTime;
  bool isLowStockDebounced;
  bool lastReportedLowStock;
  unsigned long lastSentTimestamp;
};

// Machine mapping for Island 01 (Database machines 1 through 6)
MachineSensor sensors[NUM_CHANNELS] = {
  { 13, 1, "Spindependence 1",  TICKET_DETECTED, 0, false, false, 0 },
  { 12, 2, "Spindependence 2",  TICKET_DETECTED, 0, false, false, 0 },
  { 14, 3, "Spindependence 3",  TICKET_DETECTED, 0, false, false, 0 },
  { 27, 4, "Spindependence 5",  TICKET_DETECTED, 0, false, false, 0 },
  { 26, 5, "Spindependence 4",  TICKET_DETECTED, 0, false, false, 0 },
  { 25, 6, "Plinko 1",          TICKET_DETECTED, 0, false, false, 0 }
};

unsigned long lastWiFiCheckTime = 0;

// ==========================================
// 3. Helper Functions
// ==========================================
void connectToWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;

  Serial.print(F("[WiFi] Connecting to: "));
  Serial.println(WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long startAttempt = millis();
  while (WiFi.status() != WL_CONNECTED && (millis() - startAttempt < 8000)) {
    delay(250);
    Serial.print(F("."));
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println(F("\n[WiFi] Connected successfully."));
    Serial.print(F("[WiFi] Node IP: "));
    Serial.println(WiFi.localIP());
  } else {
    Serial.println(F("\n[WiFi] Connection failed. Will retry non-blockingly."));
  }
}

bool sendSensorAlert(int machineId, bool lowStock, const char* machineName) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println(F("[HTTP] Skipped alert: Wi-Fi offline."));
    return false;
  }

  HTTPClient http;
  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-Key", IOT_API_KEY);

  // Build JSON payload: {"machine_id": 1, "low_stock": true, "sensor_node": "esp32-island-01"}
  String payload = "{";
  payload += "\"machine_id\":" + String(machineId) + ",";
  payload += "\"low_stock\":" + String(lowStock ? "true" : "false") + ",";
  payload += "\"sensor_node\":\"" + String(NODE_ID) + "\"";
  payload += "}";

  Serial.print(F("[HTTP] POST -> "));
  Serial.print(machineName);
  Serial.print(F(" | LowStock: "));
  Serial.print(lowStock ? "YES" : "NO");
  Serial.print(F(" | Payload: "));
  Serial.println(payload);

  int httpCode = http.POST(payload);

  if (httpCode > 0) {
    Serial.printf("[HTTP] Response code: %d\n", httpCode);
    if (httpCode == HTTP_CODE_OK || httpCode == 201) {
      String response = http.getString();
      Serial.printf("[HTTP] Server reply: %s\n", response.c_str());
      http.end();
      return true;
    }
  } else {
    Serial.printf("[HTTP] POST failed, error: %s\n", http.errorToString(httpCode).c_str());
  }

  http.end();
  return false;
}

// ==========================================
// 4. Setup & Main Loop
// ==========================================
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println(F("\n======================================================="));
  Serial.println(F(" Central Pier Arcade — Ticket Sensor Firmware Starting "));
  Serial.println(F("======================================================="));

  // Initialize GPIO pins with internal pull-ups
  for (int i = 0; i < NUM_CHANNELS; i++) {
    pinMode(sensors[i].pin, INPUT_PULLUP);
    int initialReading = digitalRead(sensors[i].pin);
    sensors[i].candidateState = initialReading;
    sensors[i].candidateStartTime = millis();
    sensors[i].isLowStockDebounced = (initialReading == TICKET_DEPLETED);
    sensors[i].lastReportedLowStock = sensors[i].isLowStockDebounced;
    sensors[i].lastSentTimestamp = 0;

    Serial.printf("[INIT] Channel %d | Machine %d (%s) on GPIO %d -> State: %s\n",
      i,
      sensors[i].machineId,
      sensors[i].machineName,
      sensors[i].pin,
      sensors[i].isLowStockDebounced ? "LOW STOCK" : "OK"
    );
  }

  connectToWiFi();
}

void loop() {
  unsigned long now = millis();

  // Non-blocking Wi-Fi watchdog
  if (WiFi.status() != WL_CONNECTED) {
    if (now - lastWiFiCheckTime >= WIFI_RETRY_INTERVAL) {
      lastWiFiCheckTime = now;
      connectToWiFi();
    }
  }

  // Iterate across all 6 machine channels
  for (int i = 0; i < NUM_CHANNELS; i++) {
    int rawReading = digitalRead(sensors[i].pin);

    // 1. Debounce state tracker
    if (rawReading != sensors[i].candidateState) {
      // Detected state transition candidate, reset timer
      sensors[i].candidateState = rawReading;
      sensors[i].candidateStartTime = now;
    } else {
      // Raw reading matches candidate; check if held steady for >= 5000ms
      if ((now - sensors[i].candidateStartTime) >= DEBOUNCE_DELAY_MS) {
        bool targetLowStock = (sensors[i].candidateState == TICKET_DEPLETED);

        // State transition confirmed after debounce filter
        if (targetLowStock != sensors[i].isLowStockDebounced) {
          sensors[i].isLowStockDebounced = targetLowStock;

          Serial.printf(
            "[ALERT] Confirmed transition for %s (GPIO %d): %s\n",
            sensors[i].machineName,
            sensors[i].pin,
            targetLowStock ? "LOW STOCK THRESHOLD REACHED" : "RESTOCKED / NORMAL"
          );

          // Dispatch immediate HTTP alert on state transition
          bool ok = sendSensorAlert(sensors[i].machineId, sensors[i].isLowStockDebounced, sensors[i].machineName);
          if (ok) {
            sensors[i].lastReportedLowStock = sensors[i].isLowStockDebounced;
            sensors[i].lastSentTimestamp = now;
          }
        }
      }
    }

    // 2. Periodic heartbeat dispatch (re-sync with server every 5 min if in Low Stock)
    if (sensors[i].isLowStockDebounced && (now - sensors[i].lastSentTimestamp >= HEARTBEAT_INTERVAL)) {
      Serial.printf("[HEARTBEAT] Re-sending low-stock status for %s\n", sensors[i].machineName);
      bool ok = sendSensorAlert(sensors[i].machineId, true, sensors[i].machineName);
      if (ok) {
        sensors[i].lastSentTimestamp = now;
      }
    }
  }

  // Brief yield for RTOS task scheduling
  delay(20);
}
