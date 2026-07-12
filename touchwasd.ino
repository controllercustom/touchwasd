/*
 * MIT License
 *
 * Copyright (c) 2026 controllercustom@myyahoo.com
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

#include <WiFiManager.h>
#include <ArduinoOTA.h>
#include <ESPmDNS.h>
#include <WebServer.h>
#include <ESP32USBHID.h>
#include <WebSocketsServer.h>
#include <Preferences.h>
#include <string.h>
#ifdef ARDUINO_M5STACK_ATOMS3
#include <M5GFX.h>
#endif

#define VERSION "0.1"

// Uncomment next line and change the password to enable OTA authentication:
// #define OTA_PASS "your-password-here"

ESP32USBHID HID;
#ifdef ARDUINO_M5STACK_ATOMS3
M5GFX display;
#endif
WebServer server(80);
WebSocketsServer webSocket(81);

enum Mode { MODE_WASD, MODE_ARROWS };
Mode currentMode = MODE_WASD;

char hostname[33];
WiFiManagerParameter customHostnameParam("hostname", "Device hostname", "touchwasd", 32);

#ifdef ARDUINO_M5STACK_ATOMS3
#define RESET_BUTTON_PIN 41
#else
#define RESET_BUTTON_PIN 0
#endif
unsigned long resetPressStart = 0;
bool resetButtonWasLow = false;
unsigned long lastWSActivity = 0;
int wsClientCount = 0;

// Per-HID-usage reference count so multiple clients (or slide-typing that
// re-sends a key before release) don't prematurely release a key another
// client is still holding. Mirrors the design in AGENTS.md / test_core.KeyState.
uint8_t keyRefCount[256] = {0};

void pressKeyOrArrow(char c) {
  uint8_t kc = 0;
  if (currentMode == MODE_ARROWS) {
    switch (c) {
      case 'w': kc = KEY_UP; break;
      case 's': kc = KEY_DOWN; break;
      case 'a': kc = KEY_LEFT; break;
      case 'd': kc = KEY_RIGHT; break;
    }
  } else {
    kc = ESP32USBHID::charToHID(c);
  }
  if (kc == 0) return;
  if (keyRefCount[kc] == 0) {
    HID.pressKey(kc);
  }
  if (keyRefCount[kc] < 255) keyRefCount[kc]++;
}

void releaseKeyOrArrow(char c) {
  uint8_t kc = 0;
  if (currentMode == MODE_ARROWS) {
    switch (c) {
      case 'w': kc = KEY_UP; break;
      case 's': kc = KEY_DOWN; break;
      case 'a': kc = KEY_LEFT; break;
      case 'd': kc = KEY_RIGHT; break;
    }
  } else {
    kc = ESP32USBHID::charToHID(c);
  }
  if (kc == 0) return;
  if (keyRefCount[kc] > 0) keyRefCount[kc]--;
  if (keyRefCount[kc] == 0) {
    HID.releaseKey(kc);
  }
}

void resetState() {
  memset(keyRefCount, 0, sizeof(keyRefCount));
  HID.releaseAllKeys();
}

void webSocketEvent(uint8_t num, WStype_t type, uint8_t * payload, size_t length) {
  if (type == WStype_TEXT) {
    lastWSActivity = millis();
    const char* msg = (const char*)payload;

    if (strcmp(msg, "#MODE:wasd") == 0) {
      currentMode = MODE_WASD;
      resetState();
      { Preferences p; p.begin("touchwasd", false); p.putUChar("mode", 0); p.end(); }
      webSocket.broadcastTXT("#MODE:wasd");
      updateDisplay();
    } else if (strcmp(msg, "#MODE:arrows") == 0) {
      currentMode = MODE_ARROWS;
      resetState();
      { Preferences p; p.begin("touchwasd", false); p.putUChar("mode", 1); p.end(); }
      webSocket.broadcastTXT("#MODE:arrows");
      updateDisplay();
    } else if (length == 1 && msg[0] == '~') {
      resetState();
    } else if (length == 1) {
      pressKeyOrArrow(msg[0]);
    } else if (length > 1 && msg[0] == '~') {
      releaseKeyOrArrow(msg[1]);
    }

  } else if (type == WStype_CONNECTED) {
    Serial.printf("[WS] Client %u connected\n", num);
    wsClientCount++;
    updateDisplay();
    resetState();
    lastWSActivity = millis();
    webSocket.sendTXT(num, currentMode == MODE_WASD ? "#MODE:wasd" : "#MODE:arrows");
  } else if (type == WStype_DISCONNECTED) {
    Serial.printf("[WS] Client %u disconnected\n", num);
    if (wsClientCount > 0) wsClientCount--;
    updateDisplay();
    resetState();
  }
}

#include "webpage.h"

void handleRoot() {
  server.send(200, "text/html", index_html);
}

#ifdef ARDUINO_M5STACK_ATOMS3
static void bootMsg(const char* s1, const char* s2, const char* s3) {
  display.fillScreen(TFT_BLACK);
  display.setCursor(0, 0);
  display.setTextSize(2);
  display.setTextColor(TFT_CYAN, TFT_BLACK);
  display.printf("touchWASD v%s", VERSION);
  display.setTextColor(TFT_WHITE, TFT_BLACK);
  int y = 18;
  if (s1) { display.setCursor(0, y); display.println(s1); y += 18; }
  if (s2) { display.setCursor(0, y); display.println(s2); y += 18; }
  if (s3) { display.setCursor(0, y); display.println(s3); }
}

static void updateDisplay() {
  display.fillScreen(TFT_BLACK);
  display.setCursor(0, 0);
  display.setTextSize(2);
  display.setTextColor(TFT_CYAN, TFT_BLACK);
  display.printf("touchWASD v%s\n", VERSION);
  display.setTextColor(TFT_WHITE, TFT_BLACK);
  if (WiFi.status() == WL_CONNECTED) {
    display.println(WiFi.localIP());
    char buf[32];
    snprintf(buf, sizeof(buf), "%s.local", hostname);
    display.println(buf);
  } else {
    display.println("No WiFi");
  }
  display.printf("Mode: %s", currentMode == MODE_WASD ? "WASD" : "Arrows");
  display.printf("\nClients: %d", wsClientCount);
}
#else
static void bootMsg(const char*, const char*, const char*) {}
static void updateDisplay() {}
#endif

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\n[INIT] Starting touchWASD...");

#ifdef ARDUINO_M5STACK_ATOMS3
  display.begin();
#endif
  bootMsg("Starting...", nullptr, nullptr);

  HID.begin();

  {
    Preferences p;
    p.begin("touchwasd", false);
    currentMode = p.getUChar("mode", 0) == 0 ? MODE_WASD : MODE_ARROWS;
    p.end();
  }

  pinMode(RESET_BUTTON_PIN, INPUT_PULLUP);

  bootMsg("WiFi connecting...", nullptr, nullptr);
  WiFiManager wm;
  wm.setHostname("touchwasd");
  wm.addParameter(&customHostnameParam);
  wm.setConfigPortalTimeout(180);
  wm.setConnectTimeout(20);
  if (!wm.autoConnect("touchWASD-Config")) {
    Serial.println("[WARN] WiFi timeout! Proceeding anyway.");
  }
  if (WiFi.status() == WL_CONNECTED) {
    const char* h = customHostnameParam.getValue();
    if (h && strlen(h) > 0) {
      snprintf(hostname, sizeof(hostname), "%s", h);
    } else {
      snprintf(hostname, sizeof(hostname), "touchwasd");
    }

    char ipStr[16];
    snprintf(ipStr, sizeof(ipStr), "%d.%d.%d.%d",
             WiFi.localIP()[0], WiFi.localIP()[1],
             WiFi.localIP()[2], WiFi.localIP()[3]);

    char mdnsHostname[32];
    snprintf(mdnsHostname, sizeof(mdnsHostname), "%s.local", hostname);
    bootMsg(ipStr, mdnsHostname, nullptr);
    Serial.printf("[WiFi] Connected! IP=%s, hostname=%s\n", ipStr, hostname);
    ArduinoOTA.setHostname(hostname);
#ifdef OTA_PASS
    ArduinoOTA.setPassword(OTA_PASS);
    Serial.println("[OTA] Password enabled");
#endif
    ArduinoOTA.onStart([]() { Serial.println("[OTA] Start"); });
    ArduinoOTA.onEnd([]() { Serial.println("[OTA] End"); });
    ArduinoOTA.onProgress([](unsigned int p, unsigned int t) {
      Serial.printf("[OTA] Progress: %u%%\r", p * 100 / t);
    });
    ArduinoOTA.onError([](ota_error_t e) {
      Serial.printf("[OTA] Error: %u\n", e);
    });

    if (MDNS.begin(hostname)) {
      Serial.printf("[mDNS] Responder started at %s\n", mdnsHostname);
      MDNS.addService("http", "tcp", 80);
      MDNS.addService("ws", "tcp", 81);
    }

    ArduinoOTA.begin();
    Serial.println("[OTA] Ready");
  } else {
    snprintf(hostname, sizeof(hostname), "touchwasd");
    bootMsg("WiFi failed!", nullptr, nullptr);
  }

  bootMsg("Starting server...", nullptr, nullptr);
  server.on("/", handleRoot);
  server.on("/favicon.ico", [](){server.send(204, "text/plain", "");});
  server.on("/update", HTTP_GET, []() {
#ifdef OTA_PASS
    if (!server.authenticate("admin", OTA_PASS)) return server.requestAuthentication(BASIC_AUTH, "touchWASD OTA");
#endif
    server.sendHeader("Connection", "close");
    server.send(200, "text/html",
      "<form method='POST' action='/update' enctype='multipart/form-data'>"
      "<input type='file' name='firmware'><br><br>"
      "<input type='submit' value='Update Firmware'>"
      "</form>");
  });
  server.on("/update", HTTP_POST, []() {
#ifdef OTA_PASS
    if (!server.authenticate("admin", OTA_PASS)) { server.send(401, "text/plain", "Unauthorized"); return; }
#endif
    server.sendHeader("Connection", "close");
    server.send(200, "text/plain", Update.hasError() ? "FAIL" : "OK");
    if (!Update.hasError()) delay(1000);
  }, []() {
    HTTPUpload &upload = server.upload();
    static bool uploadAborted = false;
    if (upload.status == UPLOAD_FILE_START) {
      uploadAborted = false;
#ifdef OTA_PASS
      if (!server.authenticate("admin", OTA_PASS)) { uploadAborted = true; return; }
#endif
      Serial.printf("[OTA Web] Start: %s (%u bytes)\n", upload.filename.c_str(), upload.totalSize);
      if (!Update.begin(upload.totalSize, U_FLASH)) {
        Update.printError(Serial);
        uploadAborted = true;
      }
    } else if (upload.status == UPLOAD_FILE_WRITE) {
      if (!uploadAborted && Update.write(upload.buf, upload.currentSize) != upload.currentSize) {
        Update.printError(Serial);
      }
    } else if (upload.status == UPLOAD_FILE_ABORTED) {
      uploadAborted = false;
      Serial.println("[OTA Web] Upload aborted by client");
    } else if (upload.status == UPLOAD_FILE_END) {
      if (!uploadAborted) {
        if (Update.end(true)) {
          Serial.printf("[OTA Web] Success: %u bytes\n", upload.totalSize);
          // Marked the new partition; reboot so it actually runs.
          ESP.restart();
        } else {
          Update.printError(Serial);
        }
      }
    }
  });
  server.begin();
  Serial.println("[HTTP] WebServer started on port 80");

  webSocket.onEvent(webSocketEvent);
  webSocket.begin();
  Serial.println("[WS] WebSocketServer started on port 81");

  updateDisplay();
}

static void handleWdt(unsigned long now) {
  if (lastWSActivity && now - lastWSActivity > 5000 &&
      (HID.getModifierState() || HID.getPressedCount())) {
    Serial.println("[WDT] No WS activity for 5s — resetting state");
    resetState();
    lastWSActivity = now;
  }
}

static void handleResetButton(unsigned long now) {
  bool resetPressed = digitalRead(RESET_BUTTON_PIN) == LOW;
  if (resetPressed && !resetButtonWasLow) {
    resetPressStart = now;
    resetButtonWasLow = true;
  } else if (resetPressed && resetButtonWasLow) {
    if (now - resetPressStart >= 5000) {
      Serial.println("[WiFi] Button held 5s — erasing credentials and rebooting");
#ifdef ARDUINO_M5STACK_ATOMS3
      bootMsg("Resetting", "WiFi...", nullptr);
#endif
      delay(100);
      WiFiManager wm;
      wm.resetSettings();
      delay(500);
      ESP.restart();
    }
  } else {
    resetButtonWasLow = false;
  }
}

void loop() {
  ArduinoOTA.handle();
  server.handleClient();
  webSocket.loop();
  unsigned long now = millis();
  handleWdt(now);
  handleResetButton(now);
}