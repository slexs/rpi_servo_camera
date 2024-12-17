# Raspberry Pi Servo Camera Control

A web-based interface for controlling a servo-mounted camera on Raspberry Pi. This project allows you to control camera movements through a web browser using keyboard arrows or on-screen controls.

## Features

- Web-based camera control interface
- Real-time servo movement control using arrow keys
- AJAX-based controls (no page refresh needed)
- Compatible with Raspberry Pi Camera Module
- Servo motor control for pan/tilt movements
- Mobile-friendly interface

## Hardware Requirements

- Raspberry Pi (tested on Pi 4)
- Raspberry Pi Camera Module
- Servo motors (for pan/tilt mechanism)
- Servo mount/hardware assembly

## Software Requirements

- Python 3.x
- Flask
- RPi.GPIO
- picamera

## Installation

1. Clone the repository:
```bash
git clone https://github.com/slexs/rpi_servo_camera.git
cd rpi_servo_camera
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate
```

3. Install required packages:
```bash
pip install flask RPi.GPIO picamera
```

## Usage

1. Start the server:
```bash
python camera_control.py
```

2. Access the control interface:
- Open a web browser
- Navigate to `http://[your-raspberry-pi-ip]:5000`

3. Control Methods:
- Use arrow keys on your keyboard
- Click/tap the on-screen direction buttons
- All controls are real-time with no page refresh needed

## File Structure
├── camera_control.py # Main Python application 
├── templates/ 
│ └── index.html # Web interface template 
└── .gitignore # Git ignore file