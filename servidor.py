from flask import Flask, request, jsonify
from flask_cors import CORS
import os, time

app = Flask(__name__)
CORS(app)

API_KEY = os.environ.get("API_KEY", "")   # ponla en Render (Environment)

# ======== Estado compartido (con defaults útiles) ========
STATE = {
    "color": "blanco",            # texto: "verde", "azul", etc.
    "volumen": 50,                # int 0..100
    "voz_id": "default",          # id de voz (ej. "andrea")
    "wake_word": "raspy",         # palabra de activación
    "user_name": "",              # nombre de quien usa el asistente (ej. "Jona")
    # Extras opcionales (útiles para tu demo):
    "locale": "es-MX",            # idioma/país
    "tts_rate": 1.0,              # velocidad de TTS (0.5..1.5)
    "led_brightness": 100,        # brillo LEDs 0..100
    "thinking_effect": "spin",    # "spin" | "off"
    "mute": False,                # silenciar TTS/sonidos
    # Metadatos
    "updated_at": time.time(),
    "last_by": "",                # quién hizo el último cambio (header X-Client)
}

CLIENTS = set()  # "registrados" vía /vincular (opcional)
PID = os.getpid()

# ---------- helpers ----------
def require_key(req):
    # si no hay API_KEY configurada, permite (útil en pruebas)
    return (not API_KEY) or (req.headers.get("X-API-Key") == API_KEY)

def clamp(v, lo, hi): return max(lo, min(hi, v))

def apply_patch(d: dict, who: str = ""):
    """
    Aplica solo campos conocidos con validación básica.
    Ignora claves desconocidas.
    Lanza ValueError si el tipo/valor no es válido.
    """
    if "color" in d:
        STATE["color"] = str(d["color"])

    if "volumen" in d:
        v = int(d["volumen"])
        STATE["volumen"] = clamp(v, 0, 100)

    if "voz_id" in d:
        STATE["voz_id"] = str(d["voz_id"])

    if "wake_word" in d:
        w = str(d["wake_word"]).strip()
        if not w: raise ValueError("wake_word vacío")
        STATE["wake_word"] = w

    if "user_name" in d:
        STATE["user_name"] = str(d["user_name"]).strip()

    # ---- extras opcionales ----
    if "locale" in d:
        STATE["locale"] = str(d["locale"])

    if "tts_rate" in d:
        r = float(d["tts_rate"])
        STATE["tts_rate"] = clamp(r, 0.5, 1.5)

    if "led_brightness" in d:
        b = int(d["led_brightness"])
        STATE["led_brightness"] = clamp(b, 0, 100)

    if "thinking_effect" in d:
        te = str(d["thinking_effect"])
        if te not in ("spin","off"):
            raise ValueError("thinking_effect debe ser 'spin' u 'off'")
        STATE["thinking_effect"] = te

    if "mute" in d:
        if isinstance(d["mute"], bool):
            STATE["mute"] = d["mute"]
        elif str(d["mute"]).lower() in ("true","1","yes","on"):
            STATE["mute"] = True
        elif str(d["mute"]).lower() in ("false","0","no","off"):
            STATE["mute"] = False
        else:
            raise ValueError("mute debe ser booleano")

    # Metadatos
    STATE["updated_at"] = time.time()
    if who:
        STATE["last_by"] = who

# ---------- middlewares/health ----------
@app.after_request
def no_cache(resp):
    resp.headers["Cache-Control"] = "no-store"
    return resp

# ---------- rutas ----------
@app.get("/")
def root():
    return (
        "<h2>Servidor OK</h2>"
        "<p>Usa <code>/estado</code> (GET/POST), "
        "<code>/vincular</code> (POST) y <code>/schema</code> (GET).</p>"
    )

@app.get("/healthz")
def health():
    return "ok", 200

@app.get("/schema")
def schema():
    return jsonify({
        "fields": {
            "color": "str",
            "volumen": "int 0..100",
            "voz_id": "str",
            "wake_word": "str (palabra de activación)",
            "user_name": "str (nombre del usuario)",
            "locale": "str (ej. es-MX)",
            "tts_rate": "float 0.5..1.5",
            "led_brightness": "int 0..100",
            "thinking_effect": "str: spin|off",
            "mute": "bool",
            "updated_at": "epoch seconds",
            "last_by": "str (quién actualizó)",
            "_pid": "debug",
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
    who = request.headers.get("X-Client", "")
    try:
        apply_patch(data, who)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({**STATE, "_pid": PID})

@app.post("/vincular")
def vincular():
    """
    Registra un cliente (opcional) y/o asigna user_name rápido.
    body: { "cliente": "iphone_de_jona", "user_name": "Jona" }
    """
    data = request.get_json(force=True) or {}
    cliente = str(data.get("cliente","")).strip()
    user_name = str(data.get("user_name","")).strip()
    if cliente:
        CLIENTS.add(cliente)
        STATE["last_by"] = cliente
    if user_name:
        STATE["user_name"] = user_name
    STATE["updated_at"] = time.time()
    return jsonify({
        "ok": True,
        "registrados": sorted(CLIENTS),
        "estado": {**STATE, "_pid": PID}
    })

@app.post("/reset")
def reset():
    if not require_key(request):
        return ("forbidden", 403)
    defaults = {
        "color": "blanco",
        "volumen": 50,
        "voz_id": "default",
        "wake_word": "raspy",
        "user_name": "",
        "locale": "es-MX",
        "tts_rate": 1.0,
        "led_brightness": 100,
        "thinking_effect": "spin",
        "mute": False,
        "last_by": "",
    }
    STATE.update(defaults)
    STATE["updated_at"] = time.time()
    return jsonify({**STATE, "_pid": PID})

# --- ejecución local (Render usa gunicorn) ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
