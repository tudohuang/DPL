#include <Arduino.h>
#include "driver/adc.h"
#include "adc_sampling.h"

#define ADC_ATTEN ADC_ATTEN_DB_11    // 衰減設定
#define ADC_WIDTH ADC_WIDTH_BIT_12   // ADC 解析度

void setupADC(adc1_channel_t channel) {
  adc1_config_width(ADC_WIDTH);
  adc1_config_channel_atten(channel, ADC_ATTEN);
}

int readADC(adc1_channel_t channel) {
  return adc1_get_raw(channel);  // 直接返回 ADC 數值
}
