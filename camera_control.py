import logging
from flask import Flask, render_template, request, redirect, url_for, Response
from adafruit_servokit import ServoKit
import time
import sys
sys.path.append('/usr/lib/python3.11')  # Add system Python path
from picamera2 import Picamera2
import io
# import threading
from threading import Thread, Event, Lock
from time import sleep
import cv2
from threading import Thread
from datetime import datetime, timedelta
import os

# Set up logging
log_file_path = "/home/netrom/scripts/rpi_servo_camera/backend.log"
os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)

app = Flask(__name__)
kit = ServoKit(channels=16)

# Initialize servo angles
pan_angle = 64  # Pan starting position
tilt_angle = 19  # Tilt starting position

kit.servo[0].angle = pan_angle
kit.servo[1].angle = tilt_angle

# Initialize movement speed (delay in seconds)
movement_speed = 0.05  # Default speed
INCREMENT = 3

class Camera:
    def __init__(self):
        # self.camera = Picamera2()
        self.camera = None
        self.running = False
        self.lock = Lock()  # Prevent concurrent access
        
        # Initialize zoom level (1.0 = no zoom)
        self.zoom_level = 1.0
        self.max_zoom = 4.0  # Max 4x zoom
        self.min_zoom = 1.0  # No zoom
        
    def start(self):
        if not self.running:
            try:
                self.camera = Picamera2()
                config = self.camera.create_preview_configuration({"size": (3280, 2464)})
                self.camera.configure(config)
                self.camera.start()
                self.running = True
                logging.info("Camera started successfully.")
                
            except RuntimeError as e:
                logging.error(f"Failed to start the camera: {e}")
                self.camera = None  # Ensure the camera object is reset
                self.running = False

    def stop(self):
        with self.lock:
            if self.running:
                try:
                    self.camera.stop()
                    self.camera.close()
                    logging.info("Camera stopped successfully.")
                except Exception as e:
                    logging.error(f"Error while stopping the camera: {e}")
                finally:
                    self.camera = None
                    self.running = False
                    
    def capture_photo(self, save_directory):
        with self.lock:
            try:
                if not self.running:
                    logging.info("Camera is not running. Starting it for timelapse photo capture.")
                    self.start()
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = os.path.join(save_directory, f"photo_{timestamp}.jpg")
                self.camera.capture_file(filename)
                logging.info(f"Photo saved: {filename}")
                
            except Exception as e:
                logging.error(f"Error capturing photo: {e}")
            finally:
                # Stop the camera if it was started just for this photo
                if not timelapse_event.is_set() and self.running:
                    logging.info("Stopping camera after timelapse photo capture.")
                    self.stop()

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
        with self.lock:
            if not self.running:
                return None
            frame = self.camera.capture_array()
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # Convert frame to JPEG format
            _, jpeg = cv2.imencode('.jpg', frame)
            return jpeg.tobytes()

    def generate_video_feed():
        while True:
            try:
                frame = camera.get_frame()
                if frame is None:
                    print("No frame captured.")
                    continue  # Skip if no frame is captured
                yield (b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            except Exception as e:
                print(f"Error in video feed generation: {e}")
            time.sleep(0.1)

# Initialize camera
camera = Camera()

# Initialize timelapse
timelapse_thread = None
timelapse_event = Event()
timelapse_interval = 2 * 3600  # Default to 2 hours in seconds

# Idle timeout handling
idle_timeout = timedelta(minutes=1)  # Time after which resources will be stopped
last_activity = datetime.now()
activity_lock = Lock()
stop_event = Event()

def timelapse_worker():
    save_directory = "/home/netrom/scripts/rpi_servo_camera/timelapse_photos"
    os.makedirs(save_directory, exist_ok=True)
    while timelapse_event.is_set():
        try:
            camera.capture_photo(save_directory)
            logging.info("Timelapse photo captured.")
        except Exception as e:
            logging.error(f"Error during timelapse capture: {e}")
        time.sleep(timelapse_interval)

@app.route('/start_timelapse', methods=['POST'])
def start_timelapse():
    global timelapse_thread
    if not timelapse_event.is_set():
        timelapse_event.set()
        timelapse_thread = Thread(target=timelapse_worker, daemon=True)
        timelapse_thread.start()
        logging.info("Timelapse started.")
        return {'status': 'Timelapse started'}
    return {'status': 'Timelapse already running'}

@app.route('/stop_timelapse', methods=['POST'])
def stop_timelapse():
    timelapse_event.clear()
    logging.info("Timelapse stopped.")
    return {'status': 'Timelapse stopped'}

@app.route('/set_timelapse_interval', methods=['POST'])
def set_timelapse_interval():
    print("Starting timelapse")
    global timelapse_interval
    interval = int(request.form['interval'])  # Interval in seconds
    timelapse_interval = interval
    logging.info(f"Timelapse interval set to {interval} seconds.")
    return {'status': f'Timelapse interval set to {interval} seconds'}

def idle_monitor():
    while not stop_event.is_set():
        with activity_lock:
            if datetime.now() - last_activity > idle_timeout:
                logging.info("Idle timeout reached. Stopping resources.")
                camera.stop()
        time.sleep(5)  # Check every 5 seconds

Thread(target=idle_monitor, daemon=True).start()

@app.before_request
def update_last_activity():
    global last_activity
    with activity_lock:
        last_activity = datetime.now()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/camera_status', methods=['GET'])
def camera_status():
    return {'status': 'running' if camera.running else 'idle'}

@app.route('/video_feed')
def video_feed():
    camera.start()  # Start camera only when video feed is requested
    return Response(generate_video_feed(), mimetype='multipart/x-mixed-replace; boundary=frame')

def generate_video_feed():
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(0.1)

@app.route('/restart_video_feed', methods=['POST'])
def restart_video_feed():
    if not camera.running:
        logging.info("Restarting video feed.")
        camera.start()
    return {'status': 'Camera restarted'}

@app.route('/reset', methods=['POST'])
def reset():
    start_time = time.time()
    global pan_angle, tilt_angle

    # Reset servo angles to original starting positions
    pan_angle = 64  # Pan starting position
    tilt_angle = 19  # Tilt starting position
    kit.servo[0].angle = pan_angle
    kit.servo[1].angle = tilt_angle

    # Reset zoom to 1.0 (no zoom)
    camera.zoom_level = 1.0

    # Apply the zoom settings
    camera.set_zoom(zoom_in=False)  # calling set_zoom with zoom_in=False will ensure it doesn't go beyond min zoom
    # camera.set_zoom(zoom_in=False)  # If needed multiple times to ensure no zoom.
    logging.info("Resetting camera zoom and angles")

    return {'status': 'success'}

@app.route('/zoom', methods=['POST'])
def zoom():
    action = request.form['zoom']

    if action == 'in':
        camera.set_zoom(zoom_in=True)
    elif action == 'out':
        camera.set_zoom(zoom_in=False)

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

    Thread(target=move_servo_thread, args=(kit.servo[0], pan_angle)).start()
    Thread(target=move_servo_thread, args=(kit.servo[1], tilt_angle)).start()    
    return {'status': 'success'}

@app.route('/get_servo_position', methods=['GET'])
def get_servo_position():
    # Return current servo positions
    global pan_angle, tilt_angle
    return {'status': 'success', 'pan': pan_angle, 'tilt': tilt_angle}

if __name__ == '__main__':
    # Start the camera and timelapse on app start
    camera.start()
    logging.info("Flask app started. Camera initialized.")
    if not timelapse_event.is_set():
        timelapse_event.set()
        timelapse_thread = Thread(target=timelapse_worker, daemon=True)
        timelapse_thread.start()
        logging.info("Timelapse started automatically.")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)