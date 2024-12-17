from flask import Flask, render_template, request, redirect, url_for, Response
from flask import Flask, render_template, request, Response
from adafruit_servokit import ServoKit
import time
import cv2

app = Flask(__name__)
kit = ServoKit(channels=16)

# Initialize camera
camera = cv2.VideoCapture(0)  # Use appropriate camera index

# Initialize servo angles
pan_angle = 90  # Center position
tilt_angle = 90  # Center position
camera = cv2.VideoCapture(0)

pan_angle = 90
tilt_angle = 90
kit.servo[0].angle = pan_angle
kit.servo[1].angle = tilt_angle

# Initialize movement speed (delay in seconds)
movement_speed = 0.05  # Default speed

# Define movement increments
movement_speed = 0.05
INCREMENT = 5

def generate_frames():
    while True:
        # Capture frame-by-frame
        success, frame = camera.read()
        if not success:
            break
        else:
            # Encode frame as JPEG
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            # Yield frame in byte format
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    # Video streaming route
    # return Response(generate_frames(),
    #                 mimetype='multipart/x-mixed-replace; boundary=frame')
    return "Video feed not available"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/set_speed', methods=['POST'])
def set_speed():
    global movement_speed
    speed_ms = int(request.form['speed'])
    movement_speed = speed_ms / 1000.0  # Convert ms to seconds
    return redirect(url_for('index'))

    movement_speed = speed_ms / 1000.0
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
    return redirect(url_for('index'))

    return {'status': 'success'}
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)