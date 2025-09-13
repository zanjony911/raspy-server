from flask import Flask, request, jsonify
from flask_cors import CORS
import os, time

app = Flask(__name__)
CORS(app)  # permite que apps móviles/web llamen sin bloquear por CORS

# Estado compartido (memoria simple en el servidor)
STATE = {
    "color": "blanco",
    "volumen": 50,
    "voz_id": "default",
    "updated_at": time.time()
}

# Seguridad: exige una API_KEY en el header X-API-Key para cambiar el estado
def require_key(req):
    api_key = os.environ.get("API_KEY", "")
    if not api_key:
        # si no configuraste API_KEY en Render, cualquiera podría escribir (no recomendado)
        return True
    return req.headers.get("X-API-Key") == api_key

@app.get("/estado")
def get_estado():
    return jsonify(STATE)

@app.post("/estado")
def set_estado():
    if not require_key(request):
        return ("forbidden", 403)
    data = request.get_json(force=True) or {}
    if "color" in data:   STATE["color"]   = str(data["color"])
    if "volumen" in data: STATE["volumen"] = int(data["volumen"])
    if "voz_id" in data:  STATE["voz_id"]  = str(data["voz_id"])
    STATE["updated_at"] = time.time()
    return jsonify(STATE)

# (opcional) endpoint de "vinculación" MUY simple
# Tu app puede mandar {"cliente":"iphone_de_jona"} y el server responde ok.
@app.post("/vincular")
def vincular():
    data = request.get_json(force=True) or {}
    cliente = str(data.get("cliente", "desconocido"))
    return jsonify({"ok": True, "cliente": cliente, "mensaje": "Vinculación aceptada"})
