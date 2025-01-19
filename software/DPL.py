import sys
import threading
import csv
import uuid
import numpy as np
from scipy.signal import butter, sosfilt, lfilter, firwin, savgol_filter
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QStatusBar, QLabel, QMessageBox,
    QPushButton, QVBoxLayout, QWidget, QLineEdit, QFileDialog, QFrame, QHBoxLayout, QMenuBar,QTableWidget, QTableWidgetItem,QTabWidget,QSlider,QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from math import sqrt, pi
from PySide6.QtCore import QTimer
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import serial.tools.list_ports
from collections import deque
import time
import threading
from math import sqrt, pi

from scipy.signal import butter, filtfilt, sosfilt

def design_butterworth_filter(lowcut, highcut, fs, order=4):
    """
    Design a Butterworth bandpass filter.
    
    Parameters:
    - lowcut: Lower cutoff frequency (Hz).
    - highcut: Upper cutoff frequency (Hz).
    - fs: Sampling frequency (Hz).
    - order: Filter order (default: 4).
    
    Returns:
    - b, a: Filter coefficients.
    """
    nyquist = 0.5 * fs
    low = lowcut / nyquist
    high = highcut / nyquist
    sos = butter(order, [low, high], btype='band', output='sos')
    return sos






class OscilloscopeApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MCU Oscilloscope - PySide6 Version")
        self.resize(800, 600)

        # Parameters
        self.recording = False
        self.recording_duration = 60
        self.serial_port = None
        self.sampling_rate = 1000
        self.fir_coeff = firwin(100, [0.03, 0.8], pass_zero=False)
        self.voltage_data = deque(maxlen=5000)  # 用於即時繪圖的 FIFO 緩存
        self.time_data = deque(maxlen=5000)  # 用於即時繪圖的 FIFO 緩存
        self.data_all = deque(maxlen=500000)
        self.long_term_data = deque(maxlen=500000)  # 用於長期數據記錄
        self.stop_event = None
        self.sos = None
        self.vline_without_mass = None
        self.vline_with_mass = None
        self.sos_status = True
        
        # Initialize UI
        self.setup_ui()
        self.apply_styles()
        self.setWindowIcon(QIcon(r"G:\.shortcut-targets-by-id\1hTHRprGG3w8dNgqo-yMJyqIEezOBEpgf\108課綱學習歷程\DPL\software\logo.ico"))

    def setup_ui(self):
        # Main Window
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget) # Horizontal layout, divided into left control area and right chart area

        # Left control panel
        control_panel = QFrame()
        control_panel.setObjectName("controlPanel")
        control_panel_layout = QVBoxLayout(control_panel)  # 使用 VBoxLayout 排列元件
        control_panel_layout.setSpacing(15)  # 設定元件之間的間距
        main_layout.addWidget(control_panel, 2)  # 將控制面板加入主佈局





        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Example: Setting the initial status message
        self.status_bar.showMessage("Ready")
        
        
        # Right chart area
        plots_frame = QFrame()
        plots_frame.setObjectName("plotsFrame")
        plots_layout = QVBoxLayout(plots_frame)
        main_layout.addWidget(plots_frame, 5) # The right chart area occupies 70%

        # Control area title
        control_title = QLabel("Build and discover!", self)
        control_title.setObjectName("controlTitle")
        control_panel_layout.addWidget(control_title, alignment=Qt.AlignCenter)


        self.labelsl = QLabel("Current Value: 20", self)
        self.labelsl.setStyleSheet("""
            QLabel {
                font-weight: bold;            /* 字體加粗 */
                color: aqua;                  /* 字體顏色 */
                border: 2px solid #4CAF50;    /* 邊框顏色與粗細 */
                border-radius: 8px;           /* 邊框圓角 */
                padding: 3px;                 /* 內距 */
                text-align: center;           /* 文字置中 */
                background-color: #1E1E1E;    /* 背景顏色 */
            }
        """)
        self.labelsl.setFixedHeight(30)  # 設定固定高度
        self.labelsl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # 水平擴展，固定高度
        control_panel_layout.addWidget(self.labelsl)

        self.button = QPushButton("Filter OFF", self)
        self.button.setStyleSheet("background-color: lightgray; font-size: 18px;")
        control_panel_layout.addWidget(self.button)

        # 初始狀態
        self.is_on = False

        # 連接按鈕點擊事件
        self.button.clicked.connect(self.toggle)


        # 滑桿
        self.slider = QSlider(Qt.Horizontal, self)
        self.slider.setRange(20, 200)  # 設定範圍
        self.slider.setSingleStep(20)  # 設定步進值
        self.slider.setTickInterval(20)  # 設定刻度間隔
        self.slider.setTickPosition(QSlider.TicksBelow)  # 設定刻度位置
        self.slider.setValue(20)  # 設定初始值
        self.slider.setFixedHeight(20)  # 限制滑桿高度
        control_panel_layout.addWidget(self.slider)  # 將滑桿加入控制面板

        self.slider.valueChanged.connect(self.update_label)



        # Set the control area buttons and input box
        duration_layout = QHBoxLayout()
        duration_label = QLabel("Recording time (seconds):")
        duration_label.setObjectName("durationLabel")
        self.duration_input = QLineEdit("60")
        self.duration_input.setPlaceholderText("Enter seconds")
        duration_layout.addWidget(duration_label)
        duration_layout.addWidget(self.duration_input)
        control_panel_layout.addLayout(duration_layout)

        set_duration_btn = QPushButton("Set time")
        set_duration_btn.clicked.connect(self.set_duration)
        control_panel_layout.addWidget(set_duration_btn)

        check_connection_btn = QPushButton("Check connection")
        check_connection_btn.clicked.connect(self.check_connection)
        control_panel_layout.addWidget(check_connection_btn)

        start_recording_btn = QPushButton("Start recording")
        start_recording_btn.clicked.connect(self.start_recording)
        control_panel_layout.addWidget(start_recording_btn)

        analyze_csv_btn = QPushButton("Analyze CSV")
        analyze_csv_btn.clicked.connect(self.analyze_csv)
        control_panel_layout.addWidget(analyze_csv_btn)

        # Chart area
        voltage_label = QLabel("Voltage")
        voltage_label.setAlignment(Qt.AlignCenter)
        voltage_label.setObjectName("plotLabel")
        plots_layout.addWidget(voltage_label)
        self.voltage_canvas = self.create_plot("Voltage", "Time (s)", "Voltage (V)")
        plots_layout.addWidget(self.voltage_canvas)

        spectrum_label = QLabel("Spectrum")
        spectrum_label.setAlignment(Qt.AlignCenter)
        spectrum_label.setObjectName("plotLabel")
        plots_layout.addWidget(spectrum_label)
        self.spectrum_canvas = self.create_plot("Spectrum", "Frequency (Hz)", "Amplitude")
        plots_layout.addWidget(self.spectrum_canvas)
        plots_layout.setContentsMargins(10, 10, 10, 10)  # 設定外邊距（上、右、下、左）

        #analysis_label = QLabel("Analysis")
        #analysis_label.setAlignment(Qt.AlignCenter)
        #analysis_label.setObjectName("plotLabel")
        #plots_layout.addWidget(analysis_label)
        #self.analysis_canvas = self.create_plot("Analysis", "Frequency (Hz)", "Amplitude")
        #plots_layout.addWidget(self.analysis_canvas)


    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1d1f27;
                color: #ffffff;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            #controlPanel {
                background-color: #2a2e38;
                border-radius: 12px;
                padding: 20px;
                margin: 10px;
            }
            #controlTitle {
                font-size: 24px;
                font-weight: bold;
                color: #61dafb;
                margin-bottom: 10px;
            }
            QLabel {
                font-size: 14px;
                color: #c3c3c3;
            }
            #durationInput {
                background-color: #3a3f4b;
                color: #ffffff;
                border: 2px solid #61dafb;
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 14px;
            }
            QPushButton {
                background-color: #61dafb;
                color: #282c34;
                border: none;
                border-radius: 10px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #52bfe0;
            }
            QPushButton:pressed {
                background-color: #4eaecb;
            }
            #plotsFrame {
                background-color: #1e2029;
                border-radius: 12px;
                padding: 15px;
                margin: 10px;
            }
            QLabel#plotLabel {
                font-size: 18px;
                font-weight: bold;
                color: #61dafb;
                margin-bottom: 5px;
            }
                QStatusBar {
        background-color: #1d1f27;
        color: #61dafb;
        font-size: 14px;
        font-weight: bold;
    }
                        #controlTitle {
                            font-weight: bold;
                            color: #61dafb;

                        }

        """)




    def create_plot(self, title, xlabel, ylabel):
        fig = Figure(figsize=(8, 4), dpi=120, facecolor="#1d1f27")
        ax = fig.add_subplot(111)
        ax.set_xlabel(xlabel, fontsize=12, color='#ffffff')
        ax.set_ylabel(ylabel, fontsize=12, color='#ffffff')
        ax.tick_params(axis='x', colors='#c3c3c3')
        ax.tick_params(axis='y', colors='#c3c3c3')
        ax.grid(color='#444', linestyle='--', linewidth=0.5)
        ax.set_facecolor('#2a2e38')
        canvas = FigureCanvas(fig)
        canvas.ax = ax
        return canvas
    def update_voltage_plot(self):
        """更新電壓圖表。"""

        #filtered_data = lfilter(self.fir_coeff, 1.0, np.array(self.voltage_data))
        #filtered_data = savgol_filter(self.voltage_data, window_length=51, polyorder=3)
        filtered_data = self.voltage_data

        self.voltage_canvas.ax.clear()
        self.voltage_canvas.ax.plot( filtered_data, color='#55eb34', linewidth=2.0)
        #self.voltage_canvas.ax.set_xlabel("Time (s)", fontsize=12, color='white')
        self.voltage_canvas.ax.set_ylabel("Voltage (V)", fontsize=12, color='white')
        self.voltage_canvas.ax.set_ylim(-0.5, 2)
        self.voltage_canvas.ax.set_facecolor('#2c3e50')
        self.voltage_canvas.ax.grid(color='gray', linestyle='--', linewidth=0.5)
        self.voltage_canvas.draw()
    def update_spectrum_plot(self):
        """更新頻譜圖表。"""
        freq_points = int(self.sampling_rate * 20)
        if len(self.data_all) < freq_points: return 1
        freq_data = list(self.data_all)[-freq_points:]
        if self.is_on:
            freq_data = sosfilt(self.sos, freq_data)
        #freq_data = sosfilt(self.sos, freq_data)
        spectrum_data = np.abs(np.fft.fft(np.array(freq_data)))

        deltaf = self.sampling_rate/len(spectrum_data)
        data_points = int(5 // deltaf)

        spectrumX = np.arange(data_points)*deltaf

        XX = spectrumX[3:data_points]
        YY = spectrum_data[3:data_points]

        f,f_cal,fixed_value = self.update_label(self.slider.value())
        self.sos = design_butterworth_filter(max(round(f_cal)-1,1.5), round(f_cal)+1, self.sampling_rate, 10)
        maxi = np.argmax(YY)

        self.spectrum_canvas.ax.clear()
        self.spectrum_canvas.ax.plot(spectrumX[3:data_points], spectrum_data[3:data_points], color='#55eb34', linewidth=2.0)
        self.spectrum_canvas.ax.plot(XX[maxi], YY[maxi], 'r*')
        #self.spectrum_canvas.ax.set_xlabel("Frequency (Hz)", fontsize=12, color='white')
        self.spectrum_canvas.ax.set_ylabel("Amplitude", fontsize=12, color='white')
        self.spectrum_canvas.ax.set_xlim(0, 5.5)
        self.spectrum_canvas.ax.set_ylim(0, spectrum_data[3:data_points].max()*1.2)
        self.spectrum_canvas.ax.set_facecolor('#2c3e50')
        self.spectrum_canvas.ax.grid(color='gray', linestyle='--', linewidth=0.5)
        self.spectrum_canvas.ax.axvline(x=f, color='r', linestyle='--')#, label=f'w/o mass = {f:.2f} Hz')
        self.spectrum_canvas.ax.axvline(x=f_cal, color='y', linestyle='--')#, label=f'w/ mass = {f_cal:.2f} Hz')
        self.spectrum_canvas.draw()

        self.update_status(f"Max freq: {XX[maxi] :.2f} Hz")


    def read_and_plot_data(self, stop_event):
        """從 ESP32 獲取數據並即時繪圖。"""
        partial_line = ''
        port = self.detect_esp32_port()
        if port is None:
            self.update_status("Port not found!")
            return

        ser = serial.Serial(port, 115200)
        ser.flush()
        start_time = time.time()

        while not stop_event.is_set():
            if ser.in_waiting:
                # 獲取數據並分行處理
                data = partial_line + ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                lines = data.split('\n')
                partial_line = lines[-1]

                for line in lines[:-1]:
                    try:
                        voltage = float(line)
                        timestamp = time.time() - start_time
                        self.voltage_data.append(voltage-2.2)  # 更新即時繪圖緩存
                        self.data_all.append(voltage-2.2)
                        self.time_data.append(timestamp)

                        if self.recording:
                            self.long_term_data.append((timestamp, voltage))  # 若正在記錄，保存數據

                    except ValueError:
                        continue


    def show_about(self):
        self.status_bar.showMessage("This GUI app is a oscilloscope for MCU.")

    def set_duration(self):
        try:
            duration = int(self.duration_input.text())
            self.status_bar.showMessage(f"Recording time set to {duration} seconds.")
        except ValueError:
            self.status_bar.showMessage("Invalid duration input.")


    def update_status(self, new_status):
        self.status_bar.setStyleSheet("color: #61dafb;")
        self.status_bar.showMessage(new_status)

    def detect_esp32_port(self):
        ports = list(serial.tools.list_ports.comports())
        for port in ports:
            if any(keyword in port.description for keyword in ["USB-SERIAL", "CP210", "Arduino"]):
                return port.device
        return None

    def check_connection(self):
        port = self.detect_esp32_port()
        if port is None:
            self.update_status("ESP32 not found!")
            QMessageBox.critical(self, "Connection Error", "ESP32 not found. Please connect the device and try again.")
        else:
            self.update_status(f"ESP32 connected on {port}")
            self.stop_event = threading.Event()
            threading.Thread(target=self.read_and_plot_data, args=(self.stop_event,), daemon=True).start()

            for ii in range(5):
                time.sleep(1)
                self.update_status(f"Calibrating.....{ii + 1} s")
                
            

            samples = len(self.voltage_data)
            deltat = self.time_data[-1] - self.time_data[0]

            self.sampling_rate = int(samples/deltat)
            
            self.update_status(f'Sampling frequency: {self.sampling_rate} Hz')

            self.sos = design_butterworth_filter(2, 4, self.sampling_rate, 10)


            # QTimer Setup
            self.timer1 = QTimer(self)  # Create QTimer instance
            self.timer1.timeout.connect(self.update_voltage_plot)  # Connect timeout signal to the function
            self.timer1.start(10)  # Set interval to 100 ms

            self.timer2 = QTimer(self)  # Create QTimer instance
            self.timer2.timeout.connect(self.update_spectrum_plot)  # Connect timeout signal to the function
            self.timer2.start(200)  # Set interval to 100 ms

            self.update_status(f'Displaying ...')

    
    def toggle(self):
        self.is_on = not self.is_on
        self.sos_status = not self.sos_status

        # 更新按鈕文字與顏色
        if self.is_on:
            self.button.setText("Filter ON")
            self.button.setStyleSheet("background-color: aqua; font-size: 18px; color: white;")
        else:
            self.button.setText("Filter OFF")
            self.button.setStyleSheet("background-color: lightgray; font-size: 18px; color: black;")

    def start_recording(self):
        try:
            self.recording_duration = int(self.duration_input.text())
            self.long_term_data.clear()
            self.recording = True
            self.update_status(f"Recording started for {self.recording_duration} seconds.")
            QTimer.singleShot(self.recording_duration * 1000, self.stop_recording)
        except ValueError:
            QMessageBox.critical(self, "Invalid Input", "Please enter a valid integer for recording time.")

    def stop_recording(self):
        self.recording = False
        if self.stop_event:
            self.stop_event.set()
        self.update_status("Recording stopped.")
        self.save_data_to_csv()


    def save_data_to_csv(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Recording", "", "CSV Files (*.csv)")
        if file_name:
            with open(file_name, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(["Timestamp (s)", "Voltage (V)"])
                writer.writerows(self.long_term_data)
            self.update_status(f"Data saved to {file_name}.")

    def analyze_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open CSV", "", "CSV Files (*.csv)")
        if not file_path:
            return

        try:

            self.timer1.stop()
            self.timer2.stop()

            # Load data from CSV
            data = np.loadtxt(file_path, delimiter=',', skiprows=1)
            time_data = data[:, 0]
            signal_data = data[:, 1]
            sampling_rate = data.shape[0] / (time_data[-1] - time_data[0])
            print(f'Sampling rate: {sampling_rate:.2f} Hz')

            # High-pass filter
            cutoff_frequency = 0.1
            order = 8
            sos = butter(order, cutoff_frequency, btype='high', fs=sampling_rate, output='sos')
            filtered_signal = sosfilt(sos, signal_data)

            # Smooth the signal
            window_length = 100
            b = np.ones(window_length) / window_length
            smoothed_signal = lfilter(b, 1, np.abs(filtered_signal))

            # FFT analysis
            spectrum = np.abs(np.fft.fft(signal_data))
            freqs = np.fft.fftfreq(len(signal_data), d=1/sampling_rate)

            # Find max frequency
            max_index = np.argmax(spectrum[1:int(4.5 / (sampling_rate / spectrum.size))]) + 1
            max_frequency = max_index * sampling_rate / spectrum.size
            max_amplitude = spectrum[max_index]
            print(f'Max Frequency: {max_frequency:.2f} Hz')


            # Update the analysis plot
            self.spectrum_canvas.ax.clear()
            #self.spectrum_canvas.ax.set_xlabel("Frequency [Hz]")
            self.spectrum_canvas.ax.set_ylabel("Amplitude")
            self.spectrum_canvas.ax.grid(color='gray', linestyle='--', linewidth=0.5)
            self.spectrum_canvas.ax.plot(freqs[1:int(5 / (sampling_rate / spectrum.size))],
                                        spectrum[1:int(5 / (sampling_rate / spectrum.size))], color='#55eb34')
            self.spectrum_canvas.ax.plot(max_frequency, max_amplitude, 'r*', markersize=10)

            self.spectrum_canvas.draw()

            # Update the status
            self.update_status(f"Max Frequency: {max_frequency:.2f} Hz, Sampling Rate: {sampling_rate:.2f} Hz")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to analyze CSV file: {e}")

    def theoretical_frequency(self,m,m0,k):
        f = 1/(2*pi)*sqrt(k/m)
        f_cal = 1/(2*pi)*sqrt(k/(m+m0/3))
        return f,f_cal
        
    
    def update_label(self, value):
        """更新標籤的值並更新鉛直線"""
        fixed_value = round(value / 20) * 20
        self.slider.blockSignals(True)  # 阻止遞迴觸發
        self.slider.setValue(fixed_value)
        self.slider.blockSignals(False)  # 恢復訊號觸發
        #self.labelsl.setText(f"Mass：{fixed_value}")  # 更新標籤

        # 計算新頻率值
        f, f_cal = self.theoretical_frequency(fixed_value / 1000, 0.028, 26.07)
        self.labelsl.setText(f"Mass: {fixed_value} g, w/o mass: {f:.2f} Hz, w/ mass: {f_cal:.2f} Hz")

        return f,f_cal,fixed_value

class MainApp(QMainWindow):
    """主應用窗口"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Main Application")
        self.resize(600, 400)

        # 設置主樣式
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #1d1f27;
                color: #ffffff;
                font-family: 'Segoe UI', Arial, sans-serif;            }
            QLabel#titleLabel {
                font-size: 24px;
                font-weight: bold;
                color: #ffffff;
                padding: 20px;
            }
            QLabel#descriptionLabel {
                font-size: 16px;
                color: #555555;
                margin: 10px;
            }
            QPushButton {
                font-size: 16px;
                background-color: aqua;
                color: black;
                border: none;
                border-radius: 8px;
                padding: 10px;
                margin: 10px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QLabel#footerLabel {
                font-size: 12px;
                color: #888888;
                padding: 15px;
            }
            """
        )

        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 標題區域
        title_label = QLabel("Main Application")
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # 說明文字
        description_label = QLabel("Select a tool to open a new window.")
        description_label.setObjectName("descriptionLabel")
        description_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(description_label)


        osc_button = QPushButton("Open Oscilloscope")
        osc_button.clicked.connect(self.open_oscilloscope)
        main_layout.addWidget(osc_button)

        # 版權標籤
        footer_label = QLabel("© 2025 DPL. All rights reserved.")
        footer_label.setObjectName("footerLabel")
        footer_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(footer_label)



    def open_oscilloscope(self):
        """打開 Oscilloscope 窗口"""
        # Placeholder for OscilloscopeApp implementation
        self.osc_window = OscilloscopeApp()
        self.osc_window.show()




if __name__ == "__main__":
    
    app = QApplication(sys.argv)
    window = MainApp()

    window.show()
    sys.exit(app.exec())




