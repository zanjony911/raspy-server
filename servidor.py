from flask import Flask, request, jsonify
from flask_cors import CORS
import os, time

app = Flask(__name__)
CORS(app)

API_KEY = os.environ.get("API_KEY", "")  # si no la pones, permite escribir sin llave

STATE = {
    "color": "blanco",
    "volumen": 50,
    "voz_id": "default",
    "wake_word": "raspy",
    "led_brightness": 100,
    "updated_at": time.time(),
}

PID = os.getpid()

def require_key(req):
    return (not API_KEY) or (req.headers.get("X-API-Key") == API_KEY)

def clamp(v, lo, hi): 
    return max(lo, min(hi, v))

def apply_patch(d: dict):
    if "color" in d:
        STATE["color"] = str(d["color"])

    if "volumen" in d:
        STATE["volumen"] = clamp(int(d["volumen"]), 0, 100)

    if "voz_id" in d:
        STATE["voz_id"] = str(d["voz_id"])

    if "wake_word" in d:
        w = str(d["wake_word"]).strip()
        if not w: 
            raise ValueError("wake_word vacío")
        STATE["wake_word"] = w

    if "led_brightness" in d:
        b = clamp(int(d["led_brightness"]), 0, 100)
        STATE["led_brightness"] = b

    STATE["updated_at"] = time.time()

@app.after_request
def no_cache(resp):
    resp.headers["Cache-Control"] = "no-store"
    return resp

@app.get("/")
def root():
    return "<h2>Servidor OK</h2><p>Usa /estado (GET/POST) y /schema (GET).</p>"

@app.get("/schema")
def schema():
    return jsonify({
        "fields": {
            "color": "str",
            "volumen": "int 0..100",
            "voz_id": "str",
            "wake_word": "str",
            "led_brightness": "int 0..100",
            "updated_at": "epoch",
            "_pid": "debug"
        }
    })

@app.get("/estado")
def get_estado():
    return jsonify({**STATE, "_pid": PID})

@app.post("/estado")
def set_estado():
    if not require_key(request):
        return ("forbidden", 403)
    data = request.get_json(force=True) or {}
    try:
        apply_patch(data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({**STATE, "_pid": PID})

@app.post("/reset")
def reset():
    defaults = {
        "color": "blanco",
        "volumen": 50,
        "voz_id": "default",
        "wake_word": "raspy",
        "led_brightness": 100,
    }
    STATE.update(defaults)
    STATE["updated_at"] = time.time()
    return jsonify({**STATE, "_pid": PID})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
