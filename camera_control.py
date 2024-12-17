from flask import Flask, render_template, request, redirect, url_for, Response
from adafruit_servokit import ServoKit
import time
import sys
sys.path.append('/usr/lib/python3.11')  # Add system Python path
from picamera2 import Picamera2
import io
import threading
from time import sleep
import cv2

app = Flask(__name__)
kit = ServoKit(channels=16)

# Initialize servo angles
pan_angle = 90  # Center position
tilt_angle = 90  # Center position
kit.servo[0].angle = pan_angle
kit.servo[1].angle = tilt_angle

# Initialize movement speed (delay in seconds)
movement_speed = 0.05  # Default speed
INCREMENT = 5

class Camera:
    def __init__(self):
        # Force NullPreview on initialization
        self.camera = Picamera2()
        # self.camera.start_preview(NullPreview())  # Explicitly use NullPreview
        self.camera.configure(self.camera.create_preview_configuration())

        # Use AWB control properly with integer values
        AWB_MODE_AUTO = 0  # Corresponds to AWB auto mode
        self.camera.set_controls({"AwbMode": AWB_MODE_AUTO})
        
        # Optionally set custom AWB gains (example: manual gains)
        # self.camera.set_controls({"AwbEnable": False, "ColourGains": (1.5, 1.0)})

        self.camera.start()

    def get_frame(self):
        frame = self.camera.capture_array()
        _, jpeg = cv2.imencode('.jpg', frame)
        return jpeg.tobytes()

# Initialize camera
camera = Camera()

@app.route('/video_feed')
def video_feed():
    def generate():
        while True:
            frame = camera.get_frame()
            yield (b'--frame\r\n'
                  b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    
    return Response(generate(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/set_speed', methods=['POST'])
def set_speed():
    global movement_speed
    speed_ms = int(request.form['speed'])
    movement_speed = speed_ms / 1000.0  # Convert ms to seconds
    return {'status': 'success'}

@app.route('/move', methods=['POST'])
def move():
    global pan_angle, tilt_angle
    direction = request.form['direction']
    if direction == 'left':
        pan_angle = max(0, pan_angle - INCREMENT)
    elif direction == 'right':
        pan_angle = min(180, pan_angle + INCREMENT)
    elif direction == 'up':
        tilt_angle = max(0, tilt_angle - INCREMENT)
    elif direction == 'down':
        tilt_angle = min(180, tilt_angle + INCREMENT)
    elif direction == 'up_left':
        pan_angle = max(0, pan_angle - INCREMENT)
        tilt_angle = max(0, tilt_angle - INCREMENT)
    elif direction == 'up_right':
        pan_angle = min(180, pan_angle + INCREMENT)
        tilt_angle = max(0, tilt_angle - INCREMENT)
    elif direction == 'down_left':
        pan_angle = max(0, pan_angle - INCREMENT)
        tilt_angle = min(180, tilt_angle + INCREMENT)
    elif direction == 'down_right':
        pan_angle = min(180, pan_angle + INCREMENT)
        tilt_angle = min(180, tilt_angle + INCREMENT)

    time.sleep(movement_speed)
    kit.servo[0].angle = pan_angle
    kit.servo[1].angle = tilt_angle
    return {'status': 'success'}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
