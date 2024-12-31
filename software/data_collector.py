import csv
import threading
import serial.tools.list_ports
from collections import deque
import time

# 設定參數
sampling_rate = 1000  # 1000 Hz
duration_seconds = 60  # 讀取 60 秒

# 初始化數據保存 (儲存時間和電壓數據)
data_queue = deque()  # 取消 maxlen 限制，改為依據時間來控制

# 自動檢測 ESP32 的 COM 埠
def detect_esp32_port():
    ports = list(serial.tools.list_ports.comports())
    for port in ports:
        if "USB-SERIAL" in port.description or "CP210" in port.description or "Arduino" in port.description:
            return port.device
    return None

# 資料讀取函數
def read_data(port, stop_event):
    global data_queue
    partial_line = ''
    
    if port is None:
        print("Port not found!")
        return
    
    ser = serial.Serial(port, 115200)
    ser.flush()
    start_time = time.time()

    block_time_prev = start_time
    count = 0
    try:
        while time.time() - start_time < duration_seconds and not stop_event.is_set():
            if ser.in_waiting:
                block_start = time.time()
                delta_block = block_start - block_time_prev
                #print(delta_block)
                block_time_prev = block_start
                # 讀取緩衝區內所有資料
                data = partial_line + ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                lines = data.split('\n')
                partial_line = lines[-1]
                
                for line in lines[:-1]:
                    try:
                        voltage = float(line)
                        timestamp = time.time() - start_time  # 記錄相對時間戳
                        data_queue.append((timestamp, voltage))
                    except ValueError:
                        continue
                    '''
                if delta_block > 0: 
                    print(len(lines)/delta_block)
                    count += 1
                    if count >10000:
                        break
                        '''

    except Exception as e:
        print(f"Error during reading: {e}")
    finally:
        # 完成讀取後關閉串口
        ser.close()

# 保存數據到 CSV 文件
def save_data_to_csv(filename):
    with open(filename, 'w', newline='') as file:
        writer = csv.writer(file)
        #writer.writerow(["Time (s)", "Voltage (V)"])  # 添加時間欄位
        for timestamp, voltage in data_queue:
            writer.writerow([timestamp, voltage])
    print(f"Data saved to {filename}")

# 主程式
def main():
    port = detect_esp32_port()
    if port is None:
        print("ESP32 not found!")
        return
    
    print(f"ESP32 Connected on {port}")
    stop_event = threading.Event()
    read_thread = threading.Thread(target=read_data, args=(port, stop_event), daemon=True)
    read_thread.start()
    
    # 等待資料讀取結束
    read_thread.join()  # 確保數據讀取執行緒完成
    
    # 要求使用者輸入檔名並保存數據
    filename = input("Enter the filename to save the data (e.g., output.csv): ")
    save_data_to_csv(filename)

if __name__ == "__main__":
    main()
