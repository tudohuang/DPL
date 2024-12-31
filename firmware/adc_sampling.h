#ifndef ADC_SAMPLING_H
#define ADC_SAMPLING_H

#include "driver/adc.h"

// 初始化 ADC
void setupADC(adc1_channel_t channel);

// 讀取 ADC 數據
int readADC(adc1_channel_t channel);

#endif
