#include <Arduino.h>
#include "esp32_config.h"

void setupSerial(unsigned long baudRate) {
  Serial.begin(baudRate);  // 設定串列波特率
  Serial.println("Serial initialized");
}
