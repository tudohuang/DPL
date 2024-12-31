#include <Arduino.h>
#include "adc_sampling.h"
#include "esp32_config.h"

// 常量設定
#define BUFFER_SIZE 1024               // 緩衝區大小
#define ADC1_I_CHANNEL ADC1_CHANNEL_5  // GPIO 34

// 緩衝區
int16_t i_buffer[BUFFER_SIZE];         // 原始數據緩衝區
float voltage_buffer[BUFFER_SIZE];    // 電壓緩衝區

void setup() {
  setupSerial(115200);          // 初始化串列埠
  setupADC(ADC1_I_CHANNEL);     // 初始化 ADC
  Serial.println("ADC initialized");
}

void loop() {
  static int index = 0;

  // 讀取 ADC 數據
  int raw = readADC(ADC1_I_CHANNEL);

  // 存入緩衝區並轉換為電壓值
  i_buffer[index] = raw;
  voltage_buffer[index] = (raw / 4095.0) * 3.3;

  // 輸出電壓值
  Serial.println(voltage_buffer[index], 4);  // 保留 4 位小數

  // 更新緩衝區索引
  index++;
  if (index >= BUFFER_SIZE) {
    index = 0;  // 緩衝區滿時重置索引
  }
}
