import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import threading
import serial.tools.list_ports
import scipy.signal as signal
from collections import deque
import time
import csv
import uuid
from scipy.signal import butter, sosfilt, lfilter



# FIR filter coefficients
fir_coeff = signal.firwin(100, [0.03, 0.8], pass_zero=False)

# Parameters
sampling_rate = 1000  # Sampling rate (1000 Hz)
display_seconds = 0.5  # Duration to display in seconds
data_points = int(sampling_rate * display_seconds)  # Number of data points for display
voltage_data = deque(maxlen=data_points)  # Used for real-time plotting
long_term_data = deque()  # Used for recording data
recording = False  # Recording flag
recording_duration = 60  # Default recording duration (in seconds)

# Detect ESP32 COM port
def detect_esp32_port():
    ports = list(serial.tools.list_ports.comports())
    for port in ports:
        if any(keyword in port.description for keyword in ["USB-SERIAL", "CP210", "Arduino"]):
            return port.device
    return None

# Update status on the GUI
def update_status(new_status):
    status_var.set(new_status)

# Show information about the program
def show_about():
    messagebox.showinfo("About", "This GUI app is a commercial-style oscilloscope for MCU.")

# Start recording function
def start_recording():
    global recording, long_term_data, recording_duration
    long_term_data.clear()
    recording = True
    update_status(f"Recording started for {recording_duration} seconds.")
    
    # Set a timer to stop recording after the specified duration
    threading.Timer(recording_duration, stop_recording).start()

# Stop recording function
def stop_recording():
    global recording
    recording = False
    update_status("Recording stopped.")
    save_data_to_csv()

# Set the duration of recording (if user changes it)
def set_duration():
    global recording_duration
    try:
        recording_duration = int(duration_entry.get())
        update_status(f"Recording time set to {recording_duration} seconds.")
    except ValueError:
        messagebox.showerror("Invalid Input", "Please enter a valid integer for recording time.")

# Save data to CSV after recording
def save_data_to_csv():
    filename = uuid.uuid4().hex + '.csv'  # Generate a unique filename
    with open(filename, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Timestamp (s)", "Voltage (V)"])  # Optional header
        for timestamp, voltage in long_term_data:
            writer.writerow([timestamp, voltage])
    print(f"Data saved to {filename}")

# Read data from the serial port (combined for real-time plotting and recording)
def read_and_plot_data(stop_event):
    global voltage_data, long_term_data, recording
    partial_line = ''
    port = detect_esp32_port()
    if port is None:
        print("Port not found!")
        return

    ser = serial.Serial(port, 115200)
    ser.flush()
    start_time = time.time()

    while not stop_event.is_set():
        if ser.in_waiting:
            data = partial_line + ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
            lines = data.split('\n')
            partial_line = lines[-1]

            for line in lines[:-1]:
                try:
                    voltage = float(line)
                    timestamp = time.time() - start_time
                    voltage_data.append(voltage)  # Update for real-time plotting

                    if recording:
                        long_term_data.append((timestamp, voltage))  # Record data when recording is active

                except ValueError:
                    continue

        # Update the plot only when there's enough data
        if len(voltage_data) >= 500:
            filtered_data = signal.lfilter(fir_coeff, 1.0, np.array(voltage_data))
            ax_voltage.clear()
            ax_voltage.plot(filtered_data[100:], color='#55eb34', linewidth=2.0) #3498db
            ax_voltage.set_title("Voltage", fontsize=16, color='white')
            ax_voltage.set_xlabel("Time (s)", fontsize=12, color='white')
            ax_voltage.set_ylabel("Voltage (V)", fontsize=12, color='white')
            ax_voltage.set_ylim(-2, 2)
            ax_voltage.set_facecolor('#2c3e50')
            ax_voltage.grid(color='gray', linestyle='--', linewidth=0.5)
            canvas_voltage.draw()

            spectrum_data = np.abs(np.fft.fft(filtered_data[-100:]))
            ax_spectrum.clear()
            ax_spectrum.plot(spectrum_data[3:], color='#55eb34', linewidth=2.0)
            ax_spectrum.set_title("Spectrum", fontsize=16, color='white')
            ax_spectrum.set_xlabel("Frequency (Hz)", fontsize=12, color='white')
            ax_spectrum.set_ylabel("Amplitude", fontsize=12, color='white')
            ax_spectrum.set_ylim(0, 30)
            ax_spectrum.set_facecolor('#2c3e50')
            ax_spectrum.grid(color='gray', linestyle='--', linewidth=0.5)
            canvas_spectrum.draw()

        time.sleep(0.1)  # Prevent excessive CPU usage


# Check connection to ESP32
def check_connection():
    port = detect_esp32_port()
    if port is None:
        update_status("Error: ESP32 not found!")
        messagebox.showerror("Connection Error", "ESP32 not found. Please connect the device and try again.")
    else:
        update_status(f"ESP32 Connected on {port}")
        stop_event = threading.Event()
        threading.Thread(target=read_and_plot_data, args=(stop_event,), daemon=True).start()
        
        
        
        
def analyze_csv():
    file_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
    if not file_path:
        return

    try:
        data = np.loadtxt(file_path, delimiter=',', skiprows=1)
        time_data = data[:, 0]
        signal_data = data[:, 1]
        sampling_rate = data.shape[0] / (time_data[-1] - time_data[0])
        print(f'Sampling rate: {sampling_rate:.2f} Hz')

        cutoff_frequency = 0.1
        order = 8
        sos = butter(order, cutoff_frequency, btype='high', fs=sampling_rate, output='sos')
        filtered_signal = sosfilt(sos, signal_data)

        window_length = 100
        b = np.ones(window_length) / window_length
        a = 1
        smoothed_signal = lfilter(b, a, np.abs(filtered_signal))

        spectrum = np.abs(np.fft.fft(signal_data))
        max_index = np.argmax(spectrum[1:int(4.5 / (sampling_rate / spectrum.size))]) + 1
        max_frequency = max_index * sampling_rate / spectrum.size
        max_amplitude = spectrum[max_index]
        print(f'Max Frequency: {max_frequency:.2f} Hz')

        ax_analysis.clear()
        ax_analysis.set_title("Frequency Spectrum", fontsize=16, color='white')
        ax_analysis.set_xlabel("Frequency [Hz]", fontsize=12, color='white')
        ax_analysis.set_ylabel("Amplitude", fontsize=12, color='white')
        ax_analysis.grid(color='gray', linestyle='--', linewidth=0.5)
        ax_analysis.set_facecolor('#2c3e50')

        freqs = np.arange(1, spectrum.size) * sampling_rate / spectrum.size
        ax_analysis.plot(freqs[1:int(5 / (sampling_rate / spectrum.size))], spectrum[1:int(5 / (sampling_rate / spectrum.size))], color='#55eb34') #3498db
        ax_analysis.plot(max_frequency, max_amplitude, 'r*', markersize=10)
        canvas_analysis.draw()

        update_status(f"Max Frequency: {max_frequency:.2f} Hz, Sampling Rate: {sampling_rate:.2f} Hz")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to analyze CSV file: {e}")      
        
        
        
        
        
        
        
    

# Initialize tkinter window
root = tk.Tk()
root.title("MCU Oscilloscope")
root.geometry("1200x800")  # Adjusted for better layout
root.configure(bg='#2c3e50')

# Menu bar
menu_bar = tk.Menu(root, bg='#34495e', fg='white')
menu_bar.add_command(label="About", command=show_about)
menu_bar.add_command(label="Exit", command=root.quit)
root.config(menu=menu_bar)

# Frames for better layout
frame_controls = ttk.Frame(root, padding=(20, 5), style="TFrame")
frame_controls.pack(side=tk.TOP, fill=tk.BOTH)
frame_plots = ttk.Frame(root, padding=(20, 5))
frame_plots.pack(side=tk.BOTTOM, expand=True, fill=tk.BOTH)

# Control Panel Elements
tk.Label(frame_controls, text="Control Panel", font=("Times New Roman", 18), 
         foreground="white", background="#6c9692").pack(pady=20, side=tk.LEFT)

status_var = tk.StringVar()
status_var.set("Ready")
status_label = ttk.Label(frame_controls, textvariable=status_var, anchor=tk.W, 
                         font=("Times New Roman", 14), style="TLabel")
status_label.pack(fill=tk.X, pady=5, side=tk.LEFT)

# Duration input and button panel
duration_frame = ttk.Frame(frame_controls, padding=(10, 5))
duration_frame.pack(pady=20, fill=tk.X, side=tk.LEFT)

tk.Label(duration_frame, text="Set Duration (Seconds):", font=("Times New Roman", 12), 
         foreground="white", background="#6c9692").pack(side=tk.LEFT, padx=5)
duration_entry = ttk.Entry(duration_frame, width=10)
duration_entry.insert(0, "60")
duration_entry.pack(side=tk.LEFT, padx=5)

btn_set_duration = ttk.Button(duration_frame, text="Set Duration", command=set_duration)
btn_set_duration.pack(side=tk.LEFT, padx=5)

# Buttons with improved style
style = ttk.Style()
style.configure("TButton", relief="flat", background="#1abc9c", foreground="green", padding=10)

btn_check = ttk.Button(frame_controls, text="Check Connection", 
                       command=lambda: threading.Thread(target=check_connection).start(), style="TButton")
btn_check.pack(pady=10, side=tk.LEFT)

btn_start = ttk.Button(frame_controls, text="Start Recording", command=start_recording, style="TButton")
btn_start.pack(pady=10, side=tk.LEFT)

btn_stop = ttk.Button(frame_controls, text="Stop Recording", command=stop_recording, style="TButton")
btn_stop.pack(pady=10, side=tk.LEFT)

btn_analyze = ttk.Button(frame_controls, text="Analyze CSV", command=analyze_csv)
btn_analyze.pack(pady=10, side=tk.LEFT)

# Create plots horizontally aligned
frame_voltage = ttk.Frame(frame_plots)
frame_voltage.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
frame_spectrum = ttk.Frame(frame_plots)
frame_spectrum.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
frame_analysis = ttk.Frame(frame_plots)
frame_analysis.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

# Create voltage plot
fig_voltage = Figure(figsize=(6, 3), dpi=100)
ax_voltage = fig_voltage.add_subplot(111)
ax_voltage.set_title("Voltage", fontsize=16, color='white')
ax_voltage.set_xlabel("Time (s)", fontsize=12, color='white')
ax_voltage.set_ylabel("Voltage (V)", fontsize=12, color='white')
ax_voltage.set_xlim(0, display_seconds)
ax_voltage.set_ylim(-5, 5)
ax_voltage.set_facecolor('#2c3e50')
ax_voltage.grid(color='gray', linestyle='--', linewidth=0.5)
canvas_voltage = FigureCanvasTkAgg(fig_voltage, master=frame_voltage)
canvas_voltage.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

# Create spectrum plot
fig_spectrum = Figure(figsize=(6, 3), dpi=100)
ax_spectrum = fig_spectrum.add_subplot(111)
ax_spectrum.set_title("Spectrum", fontsize=16, color='white')
ax_spectrum.set_xlabel("Frequency (Hz)", fontsize=12, color='white')
ax_spectrum.set_ylabel("Amplitude", fontsize=12, color='white')
ax_spectrum.set_xlim(0, sampling_rate // 2)
ax_spectrum.set_ylim(0, 25)
ax_spectrum.set_facecolor('#2c3e50')
ax_spectrum.grid(color='gray', linestyle='--', linewidth=0.5)
canvas_spectrum = FigureCanvasTkAgg(fig_spectrum, master=frame_spectrum)
canvas_spectrum.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

# Create analysis plot
fig_analysis = Figure(figsize=(6, 3), dpi=100)
ax_analysis = fig_analysis.add_subplot(111)
ax_analysis.set_facecolor('#2c3e50')
ax_analysis.grid(color='gray', linestyle='--', linewidth=0.5)
canvas_analysis = FigureCanvasTkAgg(fig_analysis, master=frame_analysis)
canvas_analysis.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

# Start main loop
root.mainloop()


