from flask import Flask, request, jsonify
from flask_cors import CORS
import os, time, re

app = Flask(__name__)
CORS(app)

API_KEY = os.environ.get("API_KEY", "")  # si no la pones, permite escribir sin llave

# ID de Camila (puedes sobreescribir por entorno)
CAMILA_ID = os.environ.get("ELEVEN_VOICE_ID_CAMILA", "86V9x9hrQds83qf7zaGn")
CAMILA_NAME = os.environ.get("ELEVEN_VOICE_NAME_CAMILA", "camila")

# -------- Helpers --------
def require_key(req):
    return (not API_KEY) or (req.headers.get("X-API-Key") == API_KEY)

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

_VOICE_ID_RE = re.compile(r"^[A-Za-z0-9]{6,}$")

def safe_voice_id(raw):
    """
    Normaliza el voice_id:
    - Si viene vacío o 'default' → CAMILA_ID
    - Si no parece un ID válido (regex) → CAMILA_ID
    - Si viene algo válido → se respeta
    """
    if raw is None:
        return CAMILA_ID
    s = str(raw).strip()
    if not s or s.lower() == "default":
        return CAMILA_ID
    if not _VOICE_ID_RE.match(s):
        return CAMILA_ID
    return s

# -------- Estado --------
STATE = {
    "color": "blanco",
    "volumen": 50,
    "voz_id": CAMILA_ID,          # <-- ya no 'default'
    "voz_name": CAMILA_NAME,      # opcional/informativo
    "wake_word": "raspy",
    "led_brightness": 100,
    "updated_at": time.time(),
}
PID = os.getpid()

def apply_patch(d: dict):
    if "color" in d:
        STATE["color"] = str(d["color"])

    if "volumen" in d:
        STATE["volumen"] = clamp(int(d["volumen"]), 0, 100)

    # Acepta voz_id (ID directo). Si viene vacío/default → fuerza Camila
    if "voz_id" in d:
        STATE["voz_id"] = safe_voice_id(d["voz_id"])

    # (Opcional) si mandas nombre por separado, lo guardamos informativo
    if "voz_name" in d:
        STATE["voz_name"] = str(d["voz_name"]).strip() or CAMILA_NAME

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
    return "<h2>Servidor OK</h2><p>Usa /estado (GET/POST), /schema (GET) y /reset (POST).</p>"

@app.get("/schema")
def schema():
    return jsonify({
        "fields": {
            "color": "str",
            "volumen": "int 0..100",
            "voz_id": "str (ID ElevenLabs) — nunca 'default'; si es inválido, se usa Camila",
            "voz_name": "str (opcional, informativo)",
            "wake_word": "str",
            "led_brightness": "int 0..100",
            "updated_at": "epoch",
            "_pid": "debug"
        },
        "defaults": {
            "voz_id": CAMILA_ID,
            "voz_name": CAMILA_NAME
        }
    })

@app.get("/estado")
def get_estado():
    # Defensa extra en runtime por si alguien editó STATE a mano
    STATE["voz_id"] = safe_voice_id(STATE.get("voz_id"))
    if not STATE.get("voz_name"):
        STATE["voz_name"] = CAMILA_NAME
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
    # Defensa extra
    STATE["voz_id"] = safe_voice_id(STATE.get("voz_id"))
    if not STATE.get("voz_name"):
        STATE["voz_name"] = CAMILA_NAME
    return jsonify({**STATE, "_pid": PID})

@app.post("/reset")
def reset():
    defaults = {
        "color": "blanco",
        "volumen": 50,
        "voz_id": CAMILA_ID,     # <-- fuerza Camila al reset
        "voz_name": CAMILA_NAME,
        "wake_word": "raspy",
        "led_brightness": 100,
    }
    STATE.update(defaults)
    STATE["updated_at"] = time.time()
    return jsonify({**STATE, "_pid": PID})

if __name__ == "__main__":
    # Puedes exportar ELEVEN_VOICE_ID_CAMILA="TU_ID" para cambiar Camila sin tocar el código
    app.run(host="0.0.0.0", port=5000)
