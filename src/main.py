import os
import functions_framework
from flask import Flask, jsonify, request
from google.cloud import compute_v1
from discord_interactions import verify_key_decorator

# 환경 변수 설정
PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "gen-lang-client-0178728285") 
ZS_ZONE = os.environ.get("GCP_ZONE", "us-west1-b") 
INSTANCE_NAME = os.environ.get("INSTANCE_NAME", "trout-model")
DISCORD_PUBLIC_KEY = os.environ.get("DISCORD_PUBLIC_KEY")

app = Flask(__name__)

def get_instance_client():
    return compute_v1.InstancesClient()

# 인스턴스 상태 조회
def get_instance_state():
    try:
        client = get_instance_client()
        instance = client.get(project=PROJECT_ID, zone=ZS_ZONE, instance=INSTANCE_NAME)
        return instance.status
    except Exception as e:
        print(f"Error getting status: {e}")
        return "UNKNOWN"

# 인스턴스 시작
def start_instance():
    try:
        client = get_instance_client()
        operation = client.start(project=PROJECT_ID, zone=ZS_ZONE, instance=INSTANCE_NAME)
        return "🚀 서버 시작 명령을 보냈습니다. (완료까지 1~2분 소요)"
    except Exception as e:
        return f"❌ 서버 시작 실패: {str(e)}"

# 인스턴스 중지
def stop_instance():
    try:
        client = get_instance_client()
        operation = client.stop(project=PROJECT_ID, zone=ZS_ZONE, instance=INSTANCE_NAME)
        return "🛑 서버 중지 명령을 보냈습니다."
    except Exception as e:
        return f"❌ 서버 중지 실패: {str(e)}"

def handle_start():
    current_status = get_instance_state()
    
    if current_status == "RUNNING":
        return "✅ 서버가 이미 실행 중입니다."
    elif current_status in ["PROVISIONING", "STAGING"]:
        return "⏳ 서버가 이미 켜지는 중입니다."
    else:
        return start_instance()

def handle_stop():
    current_status = get_instance_state()

    if current_status == "TERMINATED":
        return "YZ 이미 서버가 꺼져 있습니다."
    elif current_status == "STOPPING":
        return "⏳ 서버가 이미 꺼지는 중입니다."
    else:
        return stop_instance()

def handle_status():
    state = get_instance_state()
    
    status_map = {
        "RUNNING": "✅ 실행 중 (RUNNING)",
        "TERMINATED": "mz 중지됨 (TERMINATED)",
        "STOPPING": "⏳ 종료 중 (STOPPING)",
        "PROVISIONING": "⏳ 생성 중 (PROVISIONING)",
        "STAGING": "⏳ 준비 중 (STAGING)",
        "SUSPENDED": "zz 절전 모드 (SUSPENDED)"
    }
    
    readable_status = status_map.get(state, f"⚠️ 상태: {state}")
    return f"현재 GPU 서버 상태:\n> {readable_status}"

@app.route("/", methods=["POST"])
def interactions():
    verify_key = verify_key_decorator(DISCORD_PUBLIC_KEY)
    if not verify_key(request):
        return "Invalid Request", 401

    raw_request = request.json
    return interact(raw_request)

def interact(raw_request):
    if raw_request["type"] == 1:  # PING
        return jsonify({"type": 1})  # PONG
    
    data = raw_request["data"]
    command_name = data["name"]
    
    # 명령어 처리
    if command_name == "hello":
        message_content = "GCP GPU 관리자 봇입니다."
    elif command_name == "start":
        message_content = handle_start()
    elif command_name == "stop":
        message_content = handle_stop()
    elif command_name == "status":
        message_content = handle_status()
    else:
        message_content = "알 수 없는 명령어입니다."

    return jsonify({
        "type": 4,
        "data": {"content": message_content}
    })

# Cloud Functions (gen2) entry point wrapper
@functions_framework.http
def discord_bot_entry(request):
    with app.request_context(request.environ):
        return app.full_dispatch_request()