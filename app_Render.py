from flask import Flask, request, jsonify
print("🔥 VERSION 2026-06-02 05:35")
import requests, json, os, threading 
from deep_translator import GoogleTranslator

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

# ==========================
# 讀取 Telegram 與本地語音設定
# ==========================
# ========================== # 讀取 Telegram 與本地語音設定 # ==========================
#我的 Render 裡到底有什麼變數CHAT_ID和 LOCAL_SPEAKER_URL 和TELEGRAM_TOKEN
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()#Render中的環境中的設定變數# Telegram Bot API Token 
CHAT_ID = os.getenv("CHAT_ID", "").strip()#Render中的環境中的設定變數# 要發送的群組或個人 ID 
LOCAL_SPEAKER_URL = os.getenv("LOCAL_SPEAKER_URL", "").strip()#Render中的環境中的設定變數# 本地語音播報端的 URL，例如 http://192.168.0.40:10000/speak 

#print("TELEGRAM_TOKEN =", TELEGRAM_TOKEN)
#print("CHAT_ID =", CHAT_ID)
if not TELEGRAM_TOKEN or not CHAT_ID:
    print("❌ 請先在 Render 環境變數設定 TELEGRAM_TOKEN 與 CHAT_ID") 
if not LOCAL_SPEAKER_URL:
    print("⚠️ 尚未設定 LOCAL_SPEAKER_URL（本地語音推播端 URL）")

# ==========================
# 定義 Telegram 傳訊函式
# 為什麼有時成功有時 timeout
# 因為 TradingView 只看：我送出去後3秒內有沒有收到 HTTP 200
# ==========================
# =============================================================================
# def send_to_telegram(message: str):
#     """將訊息發送到 Telegram"""
#     url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
#     payload = {"chat_id": CHAT_ID, "text": message}
#     try:
#         res = requests.post(url, json=payload, timeout=2)
#         if res.status_code == 200:
#             print("✅ Telegram 傳送成功")
#         else:
#             print("❌ Telegram 傳送失敗，HTTP:", res.status_code, res.text)
#     except Exception as e:
#         print("❌ Telegram 傳送失敗:", e)
# =============================================================================
def send_to_telegram(message: str):
    import time
    t1 = time.time()# 記錄開始時間
    """
    傳送訊息到 Telegram Bot
    參數:
        message (str)
        要發送到 Telegram 的文字內容

    範例:
        send_to_telegram("Hello")
        send_to_telegram("台指突破高點")
    """
    # 建立 Telegram Bot API 網址
    # TELEGRAM_TOKEN 來自 Render 環境變數
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    # 建立要送給 Telegram API 的 JSON 資料
    payload = {
        # Telegram 群組或個人聊天室 ID
        "chat_id": CHAT_ID,
        # 要傳送的訊息內容
        "text": message
    }

    try:

        # 發送 HTTP POST 請求給 Telegram
        # json=payload 代表以 JSON 格式送出
        # timeout=2 代表最多等待 2 秒
        # 超過 2 秒沒回應就直接丟出例外錯誤
        res = requests.post(
            url,
            json=payload,
            timeout=2
        )

        # 印出 HTTP 狀態碼
        # 200 = 成功
        # 400 = 參數錯誤
        # 401 = Token 錯誤
        # 403 = 權限不足
        print("TG Status =", res.status_code)
        print("Telegram耗時 =",round(time.time() - t1, 3),"秒")

    except Exception as e:
        #Telegram timeout，目前你看不到「失敗花了多久」
        # 如果連線失敗、網路中斷、
        # Telegram 太慢、超過 timeout
        # 就會進入這裡
        
        print(#Telegram timeout，目前你看不到「失敗花了多久」
            "Telegram失敗耗時 =",
            round(time.time() - t1, 3),
            "秒"
        )

        print("Telegram timeout:", e)


# ==========================
# 測試首頁
# ==========================
@app.route('/')
def home():
    return "✅ TradingView Webhook Server 運作中！"

# ==========================
# 測試 Telegram==>https://你的Render網址/test===>請測https://tradingview-webhook-1-ogjq.onrender.com/test如果成功：Telegram 應收到：🚀 測試訊息：Telegram 發送功能正常！
# ==========================
@app.route('/test', methods=['GET'])
def test_telegram():
    send_to_telegram("🚀 測試訊息：Telegram 發送功能正常！")
    return "✅ 測試訊息已發送至 Telegram"


# ==========================
# 全域鎖與事件佇列
# ==========================
import threading
lock = threading.Lock()  # 🔒 用於確保多執行緒修改 event_queue 時不衝突
event_queue = []         # 🧱 儲存最近收到的事件（FIFO）
# =============================================================================
# event_id = 0             # 🔢 每筆事件的唯一編號
# =============================================================================

# ==========================
# 提供 local_speaker 讀取事件
# ==========================
@app.route('/events/latest', methods=['GET'])
def latest_events():

    limit = int(request.args.get("limit", 5))

    with lock:
        events = event_queue[-limit:]

    return jsonify(events)





# 建立 Flask 路由，當收到 POST 請求到 /webhook 時執行 webhook() 函式
@app.route('/webhook', methods=['POST'])
def webhook():# 定義 webhook 處理函式
 # 函式說明：接收 TradingView 傳來的 Webhook JSON 資料並轉發到 Telegram
    """接收 TradingView 的 Webhook JSON 並轉發到 Telegram + 本地語音端"""
    """
    📩 TG接收 TradingView 傳來的 JSON 訊號。
    處理步驟：
    1. 解析 JSON 資料
    2. 翻譯（可選）
    3. 建立唯一事件 ID
    4. 推送到 Telegram
    5. 推送到本地語音端
    6. 儲存事件於 event_queue 供查詢
    """
    # ============================================================
    #加一個時間測量在 webhook 開頭：
    import time
    start_time = time.time()
    # ============================================================
# =============================================================================
#     global event_id
# =============================================================================


    try:
        # 顯示原始收到的資料區塊標題
        print("========== 印出原始 Request BodRAW DATA 未解析前的位元組資料）==========")
        print(request.data)# 印出原始 Request Body（未解析前的位元組資料）
        # 顯示 HTTP Header 區塊標題
        print("========== 印出所有 HTTP Header 資訊 ==========")
        print(request.headers)# 印出所有 HTTP Header 資訊

        # 強制將收到的內容解析成 JSON# 即使 Content-Type 不是 application/json 也會嘗試解析
        data = request.get_json(force=True)
        # 顯示解析後 JSON 區塊標題
        print("========== 顯示解析後JSON DATA區塊標題 ==========")
        print(data)  # 印出解析完成的 Python Dictionary
        # 組合要傳送到 Telegram 的訊息內容
        msg = (
            # 第一行標題
            f"📊 TG收到由Tv Webhook資料：\n"
            # 將 JSON 格式化輸出
            # indent=2 代表縮排 2 格
            # ensure_ascii=False 代表保留中文不要轉 Unicode
            f"{json.dumps(data, indent=2, ensure_ascii=False)}"
        )

        # ==========================
        # Telegram開始計時
        # ==========================
        tg_start = time.time()
        # 發送 Telegram
        send_to_telegram(msg)# 呼叫 Telegram 發送函式
        # ==========================
        # 儲存事件供 local_speaker 讀取
        # ==========================
        global event_queue
        
        with lock:
            event_queue.append({
                "id": int(time.time()),
                "data": data
            })
        
            # 只保留最近100筆
            if len(event_queue) > 100:
                event_queue.pop(0)
        
        print("目前 event_queue =", event_queue)

       


        
        # ==========================
        # Telegram耗時
        # ==========================
        print(
            "Telegram區段耗時 =",
            round(time.time() - tg_start, 3),
            "秒"
        )

        # ==========================
        # Webhook總耗時
        # ==========================
        print(
            "Webhook總耗時 =",
            round(time.time() - start_time, 3),
            "秒"
        )
        # ==========================
        # 回傳成功給 TradingView
        # ==========================
        return jsonify({# 回傳成功
            "status": "success",
            "message": "Data received"
        }), 200

    except Exception as e:

        import traceback

        print("========== ERROR ==========")

        print(str(e))

        traceback.print_exc()

        # ==========================
        # 發生錯誤時也計算耗時
        # ==========================
        print(
            "Webhook失敗耗時 =",
            round(time.time() - start_time, 3),
            "秒"
        )

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    
    
# =============================================================================
# # ==========================
# # 測試 Telegram 傳送訊息
# # ==========================
# # =============================================================================
# # @app.route('/test', methods=['GET'])
# # =============================================================================
# def test_telegram():
#     """手動測試 Telegram 是否能收到訊息"""
#     send_to_telegram("🚀 測試訊息：Telegram 發送功能正常！")
#     return "✅ 測試訊息已發送至 Telegram"
# =============================================================================

# ==========================
# 程式入口
# ==========================
if __name__ == '__main__':
    # 本地測試用
    app.run(host='0.0.0.0', port=5000)
 
