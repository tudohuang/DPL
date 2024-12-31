# Circuit Design

## Overview
The circuit design integrates a 24 GHz millimeter-wave radar module with a custom PCB, enabling precise and real-time motion measurement. The system is divided into three main parts:
1. **Analog Frontend**: Filters and amplifies radar signals.
2. **Microcontroller Unit (MCU)**: Converts analog signals to digital and transmits data.
3. **Power Supply**: Provides stable and regulated voltage for all components.

## Objectives
- Ensure low noise and high signal integrity.
- Optimize PCB layout for minimal interference.
- Enable compatibility with standard educational lab setups.

---

## System Architecture
The system architecture is divided into functional blocks:

### **1. Radar Module**
- **Component**: K-LC7 24 GHz Doppler Radar
- **Features**:
  - Transmits and receives radar signals.
  - Outputs raw analog signals proportional to motion.

### **2. Signal Conditioning**
- **Purpose**: Enhance radar output signals for ADC compatibility.
- **Components**:
  - **Operational Amplifier**: OPA4340 (Low noise, high precision), 4 OP included.
  - **Filters**:
    - **Bandpass Filter**: 4 Hz to 1 kHz to eliminate noise and unwanted frequencies.
    - **Low-pass Filter**: Attenuates high-frequency noise.
- **Implementation**:
  - Two-stage amplification with adjustable gain.

### **3. Microcontroller**
- **Component**: ESP32 Dev Module
- **Features**:
  - Built-in 12-bit ADC for analog-to-digital conversion.
  - Wi-Fi for wireless data transmission.
- **Firmware**:
  - Configures ADC for precise sampling.
  - Implements signal processing algorithms.

### **4. Power Supply**
- **Components**:
  - **Regulator**: AMS1117 (5V to 3.3V conversion).
  - **Decoupling Capacitors**: Reduces power supply noise.
- **Features**:
  - Ensures stable power for radar, MCU, and signal conditioning circuits.

---

## PCB Design
### **Software**
- Designed using **KiCad**:
  - Custom symbol and footprint libraries.
  - Layered PCB layout for signal integrity.

### **Layout**
- **Size**: 100 mm x 50 mm.
- **Layers**:
  - **Top Layer**: Analog and digital components.
  - **Bottom Layer**: Ground plane and power routing.
- **Highlights**:
  - Analog and digital sections are isolated to reduce interference.
  - Multiple vias for effective grounding.

---

## Schematic and PCB Files
- The complete schematic and PCB files are available in the `hardware/` folder:
  - `hardware/schematics/radar_module.sch`
  - `hardware/pcb/radar_module.kicad_pcb`

---

## Challenges and Solutions
### **Challenge**: High-frequency noise from radar output.
- **Solution**: Implemented multi-stage filtering and grounding techniques.

### **Challenge**: PCB space constraints.
- **Solution**: Used SMD components and optimized layout.

---

## Key Features
- Modular design allows easy upgrades.
- Low-cost components for educational accessibility.
- Open-source design to encourage replication and improvement.

