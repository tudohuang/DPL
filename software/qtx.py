import sys
import threading
import csv
import uuid
import numpy as np
from scipy.signal import butter, sosfilt, lfilter, firwin
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QStatusBar, QLabel, QMessageBox,
    QPushButton, QVBoxLayout, QWidget, QLineEdit, QFileDialog, QFrame, QHBoxLayout, QMenuBar
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from PySide6.QtCore import QTimer
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import serial.tools.list_ports
from collections import deque
import time

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
        self.voltage_data = deque(maxlen=500)  # 用於即時繪圖的 FIFO 緩存
        self.long_term_data = deque()  # 用於長期數據記錄
        
        # Initialize UI
        self.setup_ui()
        self.apply_styles()
        self.setWindowIcon(QIcon(r"logo.ico"))

    def setup_ui(self):
        # Main Window
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget) # Horizontal layout, divided into left control area and right chart area

        # Left control panel
        control_panel = QFrame()
        control_panel.setObjectName("controlPanel")
        control_panel_layout = QVBoxLayout(control_panel)
        control_panel_layout.setSpacing(15)
        main_layout.addWidget(control_panel, 2) # The left panel occupies 30%

        # Right chart area
        plots_frame = QFrame()
        plots_frame.setObjectName("plotsFrame")
        plots_layout = QVBoxLayout(plots_frame)
        main_layout.addWidget(plots_frame, 5) # The right chart area occupies 70%

        # Control area title
        control_title = QLabel("Control Panel")
        control_title.setObjectName("controlTitle")
        control_panel_layout.addWidget(control_title, alignment=Qt.AlignCenter)

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

        stop_recording_btn = QPushButton("Stop recording")
        stop_recording_btn.clicked.connect(self.stop_recording)
        control_panel_layout.addWidget(stop_recording_btn)

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

        analysis_label = QLabel("Analysis")
        analysis_label.setAlignment(Qt.AlignCenter)
        analysis_label.setObjectName("plotLabel")
        plots_layout.addWidget(analysis_label)
        self.analysis_canvas = self.create_plot("Analysis", "Frequency (Hz)", "Amplitude")
        plots_layout.addWidget(self.analysis_canvas)


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
        filtered_data = lfilter(self.fir_coeff, 1.0, np.array(self.voltage_data))
        self.voltage_canvas.ax.clear()
        self.voltage_canvas.ax.plot(filtered_data[100:], color='#55eb34', linewidth=2.0)
        self.voltage_canvas.ax.set_title("Voltage", fontsize=16, color='white')
        self.voltage_canvas.ax.set_xlabel("Time (s)", fontsize=12, color='white')
        self.voltage_canvas.ax.set_ylabel("Voltage (V)", fontsize=12, color='white')
        self.voltage_canvas.ax.set_ylim(-2, 2)
        self.voltage_canvas.ax.set_facecolor('#2c3e50')
        self.voltage_canvas.ax.grid(color='gray', linestyle='--', linewidth=0.5)
        self.voltage_canvas.draw()
    def update_spectrum_plot(self):
        """更新頻譜圖表。"""
        spectrum_data = np.abs(np.fft.fft(np.array(self.voltage_data)))
        self.spectrum_canvas.ax.clear()
        self.spectrum_canvas.ax.plot(spectrum_data[3:], color='#55eb34', linewidth=2.0)
        self.spectrum_canvas.ax.set_title("Spectrum", fontsize=16, color='white')
        self.spectrum_canvas.ax.set_xlabel("Frequency (Hz)", fontsize=12, color='white')
        self.spectrum_canvas.ax.set_ylabel("Amplitude", fontsize=12, color='white')
        self.spectrum_canvas.ax.set_ylim(0, 30)
        self.spectrum_canvas.ax.set_facecolor('#2c3e50')
        self.spectrum_canvas.ax.grid(color='gray', linestyle='--', linewidth=0.5)
        self.spectrum_canvas.draw()


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
                        self.voltage_data.append(voltage)  # 更新即時繪圖緩存

                        if self.recording:
                            self.long_term_data.append((timestamp, voltage))  # 若正在記錄，保存數據

                    except ValueError:
                        continue

            # 更新繪圖
            if len(self.voltage_data) >= 500:
                self.update_voltage_plot()
                self.update_spectrum_plot()

            time.sleep(0.1)  # 降低 CPU 負載

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
            self.analysis_canvas.ax.clear()
            self.analysis_canvas.ax.set_title("Frequency Spectrum")
            self.analysis_canvas.ax.set_xlabel("Frequency [Hz]")
            self.analysis_canvas.ax.set_ylabel("Amplitude")
            self.analysis_canvas.ax.grid(color='gray', linestyle='--', linewidth=0.5)
            self.analysis_canvas.ax.plot(freqs[1:int(5 / (sampling_rate / spectrum.size))],
                                        spectrum[1:int(5 / (sampling_rate / spectrum.size))], color='#55eb34')
            self.analysis_canvas.ax.plot(max_frequency, max_amplitude, 'r*', markersize=10)
            self.analysis_canvas.draw()

            # Update the status
            self.update_status(f"Max Frequency: {max_frequency:.2f} Hz, Sampling Rate: {sampling_rate:.2f} Hz")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to analyze CSV file: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(r"G:\.shortcut-targets-by-id\1hTHRprGG3w8dNgqo-yMJyqIEezOBEpgf\108課綱學習歷程\DPL\software\logo.ico"))

    window = OscilloscopeApp()
    window.show()
    sys.exit(app.exec())
