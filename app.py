import numpy as np
from flask import Flask, render_template, Response, request, jsonify
from flask_socketio import SocketIO, emit
import json, time, os
from threading import Thread
import cv2

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

CONFIG_PATH = "config.json"
POSES_PATH = "poses.json"

# Load config and poses
def load_json(path, default):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

config = load_json(CONFIG_PATH, {"yolo_enabled": {"front": False, "rear": False}})
poses = load_json(POSES_PATH, {})

@app.route("/")
def index():
    return render_template("full_ui.html")

@app.route("/pose/<pose>")
def set_pose(pose):
    if pose in poses:
        return jsonify({"status": "success", "pose": poses[pose]})
    return jsonify({"status": "error", "message": "Pose not found"})

@app.route("/save_pose", methods=["POST"])
def save_pose():
    data = request.json
    name = data.pop("name", "custom")
    poses[name] = data
    save_json(POSES_PATH, poses)
    return jsonify({"status": "success", "message": f"Pose '{name}' saved"})

@app.route("/mirror_pose", methods=["POST"])
def mirror_pose():
    data = request.json
    mirrored = {}
    for k, v in data.items():
        if "left" in k:
            mirrored[k.replace("left", "right")] = v
        elif "right" in k:
            mirrored[k.replace("right", "left")] = v
    return jsonify({"mirrored": mirrored})

@app.route("/reset_servos")
def reset_servos():
    default_pose = {joint: 90 for joint in [
        "fl_shoulder", "fl_arm", "fl_wrist",
        "fr_shoulder", "fr_arm", "fr_wrist",
        "rl_shoulder", "rl_arm", "rl_wrist",
        "rr_shoulder", "rr_arm", "rr_wrist"
    ]}
    return jsonify({"reset": default_pose})

@app.route("/servo_calibrate")
def calibrate():
    return jsonify({"status": "success"})

@app.route("/set_confidence", methods=["POST"])
def set_confidence():
    return jsonify({"status": "success"})

@app.route("/toggle_yolo")
def toggle_yolo():
    cam = request.args.get("cam")
    enabled = request.args.get("enabled") == "true"
    config["yolo_enabled"][cam] = enabled
    save_json(CONFIG_PATH, config)
    return jsonify({"status": "success"})

@app.route("/take_snapshot")
def take_snapshot():
    camera = request.args.get("camera", "front")
    path = f"static/snapshots/{camera}_{int(time.time())}.jpg"
    cv2.imwrite(path, 255 * (camera == "front"))  # Placeholder image
    return jsonify({"success": True, "path": "/" + path, "detections": []})

@app.route("/camera_status")
def camera_status():
    return jsonify({"front": True, "rear": True})

@app.route("/system_stats")
def system_stats():
    return jsonify({
        "cpu_temp": 55,
        "cpu_usage": 32,
        "ssd_temp": 45,
        "ssd_usage": 21
    })

@app.route("/esp32_status")
def esp32_status():
    return jsonify({
        "left": True,
        "right": True
    })

def gen_frames(camera_name="front"):
    while True:
        frame = 255 * (camera_name == "front") * np.ones((240, 320, 3), dtype=np.uint8)
        _, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route("/video_feed_front")
def video_feed_front():
    return Response(gen_frames("front"), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route("/video_feed_rear")
def video_feed_rear():
    return Response(gen_frames("rear"), mimetype='multipart/x-mixed-replace; boundary=frame')

@socketio.on("servo_update")
def handle_servo_update(data):
    joint = data.get("joint")
    value = data.get("value")
    emit("servo_ack", {"joint": joint, "value": value}, broadcast=True)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5001
)
