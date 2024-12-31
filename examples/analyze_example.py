import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import butter, sosfilt, lfilter
import argparse


def main(args):
    # 讀取數據
    data = np.loadtxt(args.input_file, delimiter=',')
    offset = int(data.size * 0.05)
    signal = data[offset:-offset, 1]
    time = data[offset:-offset, 0]

    # 計算取樣率
    sampling_rate = data.shape[0] / (data[-1, 0] - data[0, 0])
    print('Sampling rate:', sampling_rate)

    # 設置分析範圍
    demo_length = signal.size // 5  # 10 sec

    # 設計高通濾波器
    sos = butter(
        8,
        0.1,
        btype='high',
        fs=sampling_rate,
        output='sos'
    )
    # 使用濾波器處理信號
    filtered_signal = sosfilt(sos, signal)
    t1 = 0
    t2 = demo_length + 10000
    signal2 = np.abs(filtered_signal[t1:t2])

    # 運行平均濾波器
    b = np.ones(100) / 100  # 分子係數
    a = 1  # 分母係數
    signal3 = lfilter(b, a, signal2)

    # 頻譜分析
    signal4 = np.abs(np.fft.fft(signal))
    checkhz_len = int(5 / (sampling_rate / signal4.size))  # 檢查最高 5 Hz 頻率
    max_indx = (np.argmax(signal4[1:checkhz_len]) + 1)
    max_hz = max_indx * sampling_rate / signal4.size
    max_spec = signal4[max_indx]
    print("Maximum Frequency:", max_hz)

    # 繪製頻譜
    plt.ylabel('Amplitude', fontsize=15)
    plt.xlabel('Frequency [Hz]', fontsize=15)
    plt.title('Frequency Spectrum', fontsize=20)
    plt.plot(sampling_rate / signal4.size * np.arange(1, checkhz_len), signal4[1:checkhz_len])
    plt.plot(max_hz, max_spec, 'r*')
    plt.show()

# 設置 argparse
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze and process signal data.")
    parser.add_argument(
        "--input_file",
        type=str,
        required=True,
        help="Path to the input CSV file containing signal data."
    )

    args = parser.parse_args()
    main(args)
