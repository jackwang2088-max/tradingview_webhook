# ============================================================
# app_Render.py - Render 部署版 TradingView Webhook + 即時翻譯
# ============================================================

from flask import Flask, request, jsonify  # Flask 用於建立 Web 伺服器
import requests, json, os                  # requests 用於 HTTP 請求，os 用於讀取環境變數
from deep_translator import GoogleTranslator  # 用於即時翻譯文字

import threading  # ✅ 新增：保護多線程存取 last_event
# ==========================
# 建立 Flask 應用
# ==========================
app = Flask(__name__)

# ==========================
# 讀取 Telegram 設定（建議使用 Render 環境變數）
# 在 Render → Dashboard → Environment → Environment Variables 設定
# TELEGRAM_TOKEN：Telegram Bot Token
# CHAT_ID：Telegram 收訊聊天 ID
# ==========================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
LOCAL_SPEAKER_URL = os.environ.get("LOCAL_SPEAKER_URL")  # ✅ 新增：本地端語音服務 URL，例如 http://192.168.0.40:10000/speak

if not TELEGRAM_TOKEN or not CHAT_ID:
    print("❌ 請先在 Render 環境變數設定 TELEGRAM_TOKEN 與 CHAT_ID")
if not LOCAL_SPEAKER_URL:                              # ✅ 新增：
    print("⚠️ 尚未設定 LOCAL_SPEAKER_URL（本地語音推播端 URL）")# ✅ 新增：


# ==========================
# 定義 Telegram 傳訊函式send_to_telegram
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
# 語音通知傳送到本地端
# ==========================
def send_to_local_speaker(data: dict):
    """呼叫本地語音端 API，讓電腦播報"""
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
# 即時翻譯函式
# ==========================
def translate_text(text: str, source='zh-TW', target='en') -> str:
    """
    使用 GoogleTranslator 將文字即時翻譯
    source：原文字語言
    target：目標翻譯語言
    """
    try:
        translated = GoogleTranslator(source=source, target=target).translate(text)
        return translated
    except Exception as e:
        print("❌ 翻譯失敗:", e)
        return text  # 若翻譯失敗，回傳原文
        
# ==========================
# 測試首頁
# ==========================
@app.route('/')
def home():
    return "✅ TradingView Webhook Server 運作中111111！"

# ==========================
# 測試 Telegram 傳送訊息
# ==========================
@app.route('/test', methods=['GET'])
def test_telegram():
    """手動測試 Telegram 是否能收到訊息"""
    send_to_telegram("🚀 測試訊息：Telegram 發送功能正常！")
    return "✅ 測試訊息已發送至 Telegram"

# ==========================
# 全局事件鎖與事件資料
# ==========================
lock = threading.Lock()     #建立一個 鎖（Lock）物件，用來確保多線程存取共享資料時不會同時修改造成衝突。
event_queue = []  # 存所有事件
#last_event = {"id": 0, "data": None}  #建立一個全局字典，記錄最新的 webhook 事件資料：• "id"：事件序號，每收到一次 webhook 就 +1     • "data"：實際收到的 JSON 資料
event_id = 0

# ==========================
# Webhook 接收 TradingView 訊息
# 它是一個 Flask 路由裝飾器（decorator）。代表「任何 HTTP POST 請求送到 /webhook，都會觸發下面的函數」。它本身不限制來源，只是定義路徑跟方法。
# 在 TradingView 裡，你設定 webhook URL 時，可以設定一個 JSON 內容，例如：
# {
#   "signal": "1分SAR做空_open",
#   "symbol": "TXF1!",
#   "price": 28071,
#   "time": "2025-11-06T05:28:00Z"
#  }
# 這個 JSON 就是「你在 TradingView Webhook 的訊息欄裡寫的內容」。
# 當 TV 觸發時，它會以 HTTP POST 把這個 JSON 送到 https://你的伺服器/webhook。
# ==========================
@app.route('/webhook', methods=['POST'])
def webhook():
    global event_id
    data = request.get_json(force=True)
    
    # 🔐 加鎖確保多線程安全
    with lock:
        event_id += 1
        event_queue.append({"id": event_id, "data": data})
        
    # ======= 建立要傳給 Telegram 的訊息格式 =======
    json_text = json.dumps(data, ensure_ascii=False)
    telegram_message = f"台指通知機器人:\n編號:{event_id}\n{json_text}"
    
    # ======= 傳送至 Telegram =======
    send_to_telegram(json.dumps(data, ensure_ascii=False))
    
    # ======= 同步傳送至本地語音端 =======
    local_data = data.copy()      # 加上事件編號供本地顯示
    local_data["id"] = event_id  # 加上事件編號供本地顯示
    send_to_local_speaker(data)
    return jsonify({"status": "success"}), 200
    """
    接收 TradingView 的 Webhook JSON 並翻譯後轉發到 Telegram
    """
    try:
        # 強制把 POST body 當 JSON 解析成 Python dict。
        data = request.get_json(force=True)
        print(f"📩 收到 TradingView 資料轉成 Python字典: {data}")

        # 把Python dict串接組成訊息文字
        original_msg = f"📊 TradingView Webhook 收到資料：\n{json.dumps(data, indent=2, ensure_ascii=False)}"
        print(f"📩 把Python dict串接組成訊息文字 : {original_msg}")

        # 記錄事件
        with lock:
            last_event["id"] += 1
            last_event["data"] = data
            #🔹 用法與功能 with lock:
            #表示進入一個鎖定區塊，確保這段程式碼在任何時候只有一個線程可以執行。
            #執行完畢後自動釋放鎖。
            #last_event["id"] += 1
            #每收到一個新的 webhook 事件就讓事件 ID +1，方便 local_poller 判斷「哪些事件是新事件」。
            #last_event["data"] = data
            #把剛收到的 webhook JSON 資料存到全局事件資料裡，讓 local_poller.py 輪詢時可以讀取。
        
        # ===== 把接組成訊息文字透過translate_text即時翻譯訊息 =====
        translated_msg = translate_text(original_msg)
        print(f"📩 把傳送給Telegram 資料即時翻譯 : {translated_msg}")
        
        # ===== 把把接組成訊息文字透過translate_text即時翻譯訊息發送到 Telegram =====
        send_to_telegram(translated_msg)
        
        # ===== 把把接組成訊息文字透過translate_text即時翻譯訊息傳送到本地語音端 =====
        send_to_local_speaker(data)
        
        
        # 回傳成功訊息
        #return jsonify({"status": "success", "message": "Data received"}), 200
        return jsonify({"status": "success", "message": "已發送到 Telegram + 語音端"}), 200
    except Exception as e:
        print("❌ Webhook 錯誤:", e)
        return jsonify({"status": "error", "message": str(e)}), 500


# ==========================
# 本地端輪詢查詢最新事件
# local_poller.py 將透過 /events/latest 拉取事件
# ==========================
@app.route('/events/latest', methods=['GET'])
def get_latest_event():
    """提供 local_poller.py 取得最新事件的 API"""
    with lock:
        #return jsonify(last_event)
        return jsonify(event_queue)  # ✅ 回傳所有事件
        
# ==========================
# 程式入口
# ==========================
if __name__ == '__main__':
    # 本地測試用
    app.run(host='0.0.0.0', port=5000)












