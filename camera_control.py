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
from threading import Thread
from datetime import datetime

# PROFILING
# import cProfile
# import pstats
# import io

app = Flask(__name__)
kit = ServoKit(channels=16)

# Initialize servo angles
pan_angle = 85  # Pan starting position
tilt_angle = 19  # Tilt starting position

kit.servo[0].angle = pan_angle
kit.servo[1].angle = tilt_angle

# Initialize movement speed (delay in seconds)
movement_speed = 0.05  # Default speed
INCREMENT = 3

class Camera:
    def __init__(self):
        self.camera = Picamera2()
        
        # Set maximum resolution (3280x2464)
        config = self.camera.create_preview_configuration({"size": (3280, 2464)})
        # config = self.camera.create_preview_configuration({"size": (1640, 1232)})
        # config = self.camera.create_preview_configuration({"size": (2592, 1944)})
        self.camera.configure(config)
        self.camera.start()
        
        # Initialize zoom level (1.0 = no zoom)
        self.zoom_level = 1.0
        self.max_zoom = 4.0  # Max 4x zoom
        self.min_zoom = 1.0  # No zoom

    def set_zoom(self, zoom_in=True):
        # Adjust zoom level
        if zoom_in:
            self.zoom_level = min(self.max_zoom, self.zoom_level + 0.5)
        else:
            self.zoom_level = max(self.min_zoom, self.zoom_level - 0.5)
        
        # Calculate ROI based on zoom level
        width = int(3280 / self.zoom_level)
        height = int(2464 / self.zoom_level)
        x_offset = (3280 - width) // 2
        y_offset = (2464 - height) // 2
        
        # Apply new ROI to camera
        self.camera.set_controls({"ScalerCrop": (x_offset, y_offset, width, height)})

    def get_frame(self):
        frame = self.camera.capture_array()
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # Convert BGR to RGB
        _, jpeg = cv2.imencode('.jpg', frame)
        return jpeg.tobytes()


# Initialize camera
camera = Camera()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_video_feed(), mimetype='multipart/x-mixed-replace; boundary=frame')

def generate_video_feed():
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(0.1)

# @app.route('/video_feed')
# def video_feed():
#     def generate():
#         while True:
#             frame = camera.get_frame()
#             yield (b'--frame\r\n'
#                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    
#     return Response(generate(),
#                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/reset', methods=['POST'])
def reset():
    start_time = time.time()
    global pan_angle, tilt_angle

    # Reset servo angles to original starting positions
    pan_angle = 85
    tilt_angle = 19
    kit.servo[0].angle = pan_angle
    kit.servo[1].angle = tilt_angle

    # Reset zoom to 1.0 (no zoom)
    camera.zoom_level = 1.0

    # Apply the zoom settings
    camera.set_zoom(zoom_in=False)  # calling set_zoom with zoom_in=False will ensure it doesn't go beyond min zoom
    # camera.set_zoom(zoom_in=False)  # If needed multiple times to ensure no zoom.

    end_time = time.time()
    print(f"Reset operation took {end_time - start_time} seconds")

    return {'status': 'success'}

@app.route('/zoom', methods=['POST'])
def zoom():
    start_time = time.time()
    action = request.form['zoom']

    # Log before zoom action
    print("Zoom action started:", action, "at", time.time() - start_time, "s")

    if action == 'in':
        camera.set_zoom(zoom_in=True)
    elif action == 'out':
        camera.set_zoom(zoom_in=False)

    # Log after zoom action
    print("Zoom action completed at", time.time() - start_time, "s")

    return {'status': 'success'}

@app.route('/set_speed', methods=['POST'])
def set_speed():
    global movement_speed
    speed_ms = int(request.form['speed'])
    movement_speed = speed_ms / 1000.0  # Convert ms to seconds
    return {'status': 'success'}

@app.route('/set_increment', methods=['POST'])
def set_increment():
    global INCREMENT
    increment_value = int(request.form['increment'])
    INCREMENT = increment_value  # Update the global increment value
    return {'status': 'success'}

def move_servo_thread(servo, angle):
    servo.angle = angle

@app.route('/move', methods=['POST'])
def move():
    request_time = datetime.utcnow()  # Timestamp when the request is received
    print(f"Request received at: {request_time.isoformat()}")
    start_time = time.time()
    global pan_angle, tilt_angle
    direction = request.form['direction']

    if direction == 'left':
        # Swap logic: Pan angle should increase when moving left
        pan_angle = min(180, pan_angle + INCREMENT)
    elif direction == 'right':
        # Swap logic: Pan angle should decrease when moving right
        pan_angle = max(0, pan_angle - INCREMENT)
    
    elif direction == 'up':
        tilt_angle = max(0, tilt_angle - INCREMENT)

    elif direction == 'down':
        tilt_angle = min(180, tilt_angle + INCREMENT)
    
    elif direction == 'up_left':
        pan_angle = min(180, pan_angle + INCREMENT)  # Swapped
        tilt_angle = max(0, tilt_angle - INCREMENT)
    
    elif direction == 'up_right':
        pan_angle = max(0, pan_angle - INCREMENT)  # Swapped
        tilt_angle = max(0, tilt_angle - INCREMENT)
    
    elif direction == 'down_left':
        pan_angle = min(180, pan_angle + INCREMENT)  # Swapped
        tilt_angle = min(180, tilt_angle + INCREMENT)
    
    elif direction == 'down_right':
        pan_angle = max(0, pan_angle - INCREMENT)  # Swapped
        tilt_angle = min(180, tilt_angle + INCREMENT)

    # time.sleep(movement_speed)
    # kit.servo[0].angle = pan_angle
    # kit.servo[1].angle = tilt_angle

    Thread(target=move_servo_thread, args=(kit.servo[0], pan_angle)).start()
    Thread(target=move_servo_thread, args=(kit.servo[1], tilt_angle)).start()

    response_time = datetime.utcnow()  # Timestamp when the response is sent
    print(f"Request processed and response sent at: {response_time.isoformat()}")
    print(f"Total processing time: {(response_time - request_time).total_seconds()} seconds")
    

    end_time = time.time()
    print("Move request duration:", end_time - start_time, "seconds")
    return {'status': 'success'}

@app.route('/get_servo_position', methods=['GET'])
def get_servo_position():
    # Return current servo positions
    global pan_angle, tilt_angle
    return {'status': 'success', 'pan': pan_angle, 'tilt': tilt_angle}

if __name__ == '__main__':
    # PROFILING
    # profiler = cProfile.Profile()
    # profiler.enable()

    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)#, use_reloader=False) 

    # PROFILING REPORT
    # profiler.disable()
    # stream = io.StringIO()
    # stats = pstats.Stats(profiler, stream=stream)
    # stats.strip_dirs()
    # stats.sort_stats("cumulative")  # Sort by cumulative time
    # stats.print_stats()
    # print(stream.getvalue())  # Output profile stats to the console or save to a file