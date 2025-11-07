# ============================================================
# app_Render.py - Render 部署版 TradingView Webhook + 即時翻譯
# ============================================================

from flask import Flask, request, jsonify
import requests, json, os, threading
from deep_translator import GoogleTranslator

# ==========================
# 建立 Flask 應用
# ==========================
app = Flask(__name__)

# ==========================
# 讀取 Telegram 與本地語音設定
# ==========================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")  # Telegram Bot API Token
CHAT_ID = os.environ.get("CHAT_ID")                # 要發送的群組或個人 ID
LOCAL_SPEAKER_URL = os.environ.get("LOCAL_SPEAKER_URL")  # 本地語音播報端的 URL，例如 http://192.168.0.40:10000/speak

if not TELEGRAM_TOKEN or not CHAT_ID:
    print("❌ 請先在 Render 環境變數設定 TELEGRAM_TOKEN 與 CHAT_ID")
if not LOCAL_SPEAKER_URL:
    print("⚠️ 尚未設定 LOCAL_SPEAKER_URL（本地語音推播端 URL）")

# ==========================
# Telegram 傳送函式
# ==========================
def send_to_telegram(message: str):
    """將訊息發送到 Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        res = requests.post(url, json=payload)
        if res.status_code == 200:
            print("✅ Telegram 傳送成功")
        else:
            print("❌ Telegram 傳送失敗，HTTP:", res.status_code, res.text)
    except Exception as e:
        print("❌ Telegram 傳送失敗:", e)

# ==========================
# 傳送到本地語音端
# ==========================
def send_to_local_speaker(data: dict):
    """呼叫本地語音端 API 播報訊息"""
    if not LOCAL_SPEAKER_URL:
        print("⚠️ 未設定 LOCAL_SPEAKER_URL，略過語音播報")
        return
    try:
        res = requests.post(LOCAL_SPEAKER_URL, json=data, timeout=3)
        if res.status_code == 200:
            print("🔊 已發送至本地語音端")
        else:
            print("❌ 語音端回傳錯誤:", res.status_code, res.text)
    except Exception as e:
        print("❌ 無法連線到本地語音端:", e)

# ==========================
# 翻譯函式
# ==========================
def translate_text(text: str, source='zh-TW', target='en') -> str:
    try:
        return GoogleTranslator(source=source, target=target).translate(text)
    except Exception as e:
        print("❌ 翻譯失敗:", e)
        return text

# ==========================
# 測試首頁
# ==========================
@app.route('/')
def home():
    return "✅ TradingView Webhook Server 運作中！"

# ==========================
# 測試 Telegram
# ==========================
@app.route('/test', methods=['GET'])
def test_telegram():
    send_to_telegram("🚀 測試訊息：Telegram 發送功能正常！")
    return "✅ 測試訊息已發送至 Telegram"

# ==========================
# 全域鎖與事件佇列
# ==========================
lock = threading.Lock()  # 🔒 用於確保多執行緒修改 event_queue 時不衝突
event_queue = []         # 🧱 儲存最近收到的事件（FIFO）
event_id = 0             # 🔢 每筆事件的唯一編號

# ==========================
# TradingView Webhook 接收
# ==========================
@app.route('/webhook', methods=['POST'])
def webhook():
    """接收 TradingView JSON 並轉發至 Telegram + 本地語音端"""
        """
    📩 接收 TradingView 傳來的 JSON 訊號。
    處理步驟：
        1. 解析 JSON 資料
        2. 翻譯（可選）
        3. 建立唯一事件 ID
        4. 推送到 Telegram
        5. 推送到本地語音端
        6. 儲存事件於 event_queue 供查詢
    """
    global event_id
    try:
        data = request.get_json(force=True)
        print(f"📩 收到 TradingView JSON: {data}")
        # 翻譯內容
        translated_msg = translate_text(json.dumps(data, ensure_ascii=False))

        # 生成事件 ID 並記錄
        with lock:
            event_id += 1
            eid = event_id
            event_queue.append({"id": eid, "data": data})

        # 建立 Telegram 訊息
        telegram_message = (
            f"台指通知機器人:\n"
            f"編號:{eid}\n"
            f"{json.dumps(data, ensure_ascii=False)}\n\n"
            f"🈯翻譯內容:\n{translated_msg}"
        )

        send_to_telegram(telegram_message)
        #send_to_local_speaker({"id": eid, "data": data})
        #return jsonify({"status": "success", "id": eid}), 200

        # === ✅ 新增: 轉送到本地 Speaker webhook ===
        try:
            requests.post("http://192.168.0.40:10000/webhook", json={
                "id": eid,
                "signal": signal_text,
                "symbol": symbol,
                "price": price
            }, timeout=2)
            print("🎯 已轉送到本地 Speaker")
        except Exception as e:
            print("⚠️ 本地 Speaker 未連線:", e)

        # === 備用方案: 若有設定 LOCAL_SPEAKER_URL 也同步推送 ===
        if LOCAL_SPEAKER_URL:
            try:
                res = requests.post(LOCAL_SPEAKER_URL, json={"id": eid, "data": data}, timeout=2)
                if res.status_code == 200:
                    print("🔊 已發送至 LOCAL_SPEAKER_URL")
            except Exception as e:
                print("⚠️ LOCAL_SPEAKER_URL 推送失敗:", e)

        return jsonify({"status": "success", "id": eid}), 200

    except Exception as e:
        print("❌ Webhook 錯誤:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

# ==========================
# 提供 local_speaker 取得最新事件
# ==========================
@app.route('/events/latest', methods=['GET'])
def get_latest_event():
    """提供 local_speaker.py 取得最近事件的 API"""
    limit = int(request.args.get("limit", 10))  # 預設取最近10筆
    with lock:
        latest_events = list(event_queue)[-limit:]
    return jsonify(latest_events)

# ==========================
# 主程式入口
# ==========================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

