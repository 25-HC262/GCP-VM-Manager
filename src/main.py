import os
import requests
import functions_framework
from flask import Flask, jsonify, request
from discord_interactions import verify_key

# 환경 변수 설정
PROJECT_ID = os.environ.get("PROJECT_ID", "gen-lang-client-0178728285")
ZS_ZONE = os.environ.get("GCP_ZONE", "asia-northeast3-b")
INSTANCE_NAME = os.environ.get("INSTANCE_NAME", "trout-model")
DISCORD_PUBLIC_KEY = os.environ.get("DISCORD_PUBLIC_KEY")
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

app = Flask(__name__)

def get_instance_client():
    from google.cloud import compute_v1
    return compute_v1.InstancesClient()

def get_instance_state():
    try:
        client = get_instance_client()
        instance = client.get(project=PROJECT_ID, zone=ZS_ZONE, instance=INSTANCE_NAME)
        return instance.status
    except Exception as e:
        print(f"Error getting status: {e}")
        return "UNKNOWN"

def start_instance():
    try:
        client = get_instance_client()
        operation = client.start(project=PROJECT_ID, zone=ZS_ZONE, instance=INSTANCE_NAME)
        return "서버 시작 명령을 보냈습니다. (완료까지 1~2분 소요)"
    except Exception as e:
        return f"❌ 서버 시작 실패: {str(e)}"

def stop_instance():
    try:
        client = get_instance_client()
        operation = client.stop(project=PROJECT_ID, zone=ZS_ZONE, instance=INSTANCE_NAME)
        return "서버 중지 명령을 보냈습니다."
    except Exception as e:
        return f"❌ 서버 중지 실패: {str(e)}"

def handle_start():
    current_status = get_instance_state()
    
    if current_status == "RUNNING":
        return "서버가 이미 실행 중입니다."
    elif current_status in ["PROVISIONING", "STAGING"]:
        return "서버가 이미 켜지는 중입니다."
    else:
        return start_instance()

def handle_stop():
    current_status = get_instance_state()

    if current_status == "TERMINATED":
        return "서버가 이미 꺼져 있습니다."
    elif current_status == "STOPPING":
        return "서버가 이미 꺼지는 중입니다."
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

@app.route("/cron", methods=["POST", "GET"])
def scheduled_check():
    state = get_instance_state()
    
    if state == "RUNNING":
        if DISCORD_WEBHOOK_URL:
            message = {
                "content": f"🚨 [비용 경고] GPU 서버(`{INSTANCE_NAME}`)가 켜져 있습니다!\n사용하지 않는다면 `/stop` 명령어로 꺼주세요. 💸"
            }
            try:
                requests.post(DISCORD_WEBHOOK_URL, json=message)
                return "Notification sent", 200
            except Exception as e:
                return f"Failed to send webhook: {e}", 500
        else:
            return "Webhook URL not configured", 500
            
    return f"Server is {state}. No notification sent.", 200

@app.route("/", methods=["POST"])
def interactions():
    # 헤더에서 서명 정보 추출
    signature = request.headers.get('X-Signature-Ed25519')
    timestamp = request.headers.get('X-Signature-Timestamp')
    
    if signature is None or timestamp is None:
        return 'Bad request signature', 401

    # verify_key로 수동 검증
    if not verify_key(request.data, signature, timestamp, DISCORD_PUBLIC_KEY):
        return 'Bad request signature', 401

    raw_request = request.json
    return interact(raw_request)

def interact(raw_request):
    if raw_request["type"] == 1:
        return jsonify({"type": 1})
    
    # 명령어 데이터 추출
    data = raw_request["data"]
    command_name = data["name"]
    
    # 명령어 분기 처리
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

@functions_framework.http
def discord_bot_entry(request):
    with app.request_context(request.environ):
        return app.full_dispatch_request()