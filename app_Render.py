# =============================================================================
# TradingView Webhook → Render → Telegram + Local Speaker
# 第1步：建立 Flask 系統 + 讀取環境變數
# 流程：#
# TradingView
#      |
#      | Webhook JSON
#      ▼
# Render Flask Server
#
#      |
#      |
#      ├── TELEGRAM_TOKEN
#      ├── CHAT_ID
#      └── LOCAL_SPEAKER_URL#
# =============================================================================
# =============================================================================
# 第1步:匯入需要使用的套件
# =============================================================================
from flask import Flask, request, jsonify
print("🔥 VERSION 2026-08-03 01:40 DEBUG-LOG V2")# 用來顯示目前版本
import requests# HTTP連線套件# 用來呼叫 Telegram API
import json# JSON處理# TradingView 傳來的是 JSON 格式
import os# 讀取 Render 環境變數
import threading# 背景執行緒# 後面 Telegram 傳送會使用
from deep_translator import GoogleTranslator# 翻譯套件# TradingView 訊息可翻譯使用
import time
from datetime import datetime

# =============================================================================
# 第2步:建立 Flask 應用程式#
# Flask 是 Render 接收 TradingView webhook 的伺服器#
# TradingView 傳送：#
# POST /webhook#
# Flask 接收後開始處理#
# =============================================================================
app = Flask(__name__)

# =============================================================================
# 第3步：讀取 Render 環境變數
# Render Dashboard
#       |
#       ▼
# Environment Variables
# 裡面設定：#
# TELEGRAM_TOKEN
#     Telegram Bot 的身分密碼
# CHAT_ID
#     要接收 Telegram 訊息的聊天室 ID
# LOCAL_SPEAKER_URL
#     家中電腦 Python 語音播報網址
# 範例：#
# http://192.168.0.40:10000/speak
# =============================================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()#Render中的環境中的設定變數# Telegram Bot API Token 
CHAT_ID = os.getenv("CHAT_ID", "").strip()#Render中的環境中的設定變數# 要發送的群組或個人 ID 
LOCAL_SPEAKER_URL = os.getenv("LOCAL_SPEAKER_URL", "").strip()#Render中的環境中的設定變數# 本地語音播報端的 URL，例如 http://192.168.0.40:10000/speak 
# =============================================================================
# 第4步：啟動時檢查環境變數
# 如果 Render 沒設定
# 程式仍然啟動
# 但是會提醒錯誤
# =============================================================================
#print("TELEGRAM_TOKEN =", TELEGRAM_TOKEN)
#print("CHAT_ID =", CHAT_ID)
if not TELEGRAM_TOKEN or not CHAT_ID:
    print("❌ 請先在 Render 環境變數設定 TELEGRAM_TOKEN 與 CHAT_ID") 
else:
    print("✅ Telegram 設定讀取成功")
if not LOCAL_SPEAKER_URL:
    print("⚠️ 尚未設定 LOCAL_SPEAKER_URL（本地語音推播端 URL）")
else:
    print("✅ Local Speaker 設定讀取成功")
# =============================================================================
# 第5步：測試用首頁
# 瀏覽器輸入：
# https://你的Render網址/
# 如果看到： TradingView Webhook Server 運作中
# 代表 Flask 活著
# =============================================================================
@app.route('/')
def home():
    return "✅ TradingView Webhook Server 運作中！"
# =============================================================================
#  第6步：程式入口
# 注意： Render 啟動時通常由 gunicorn 呼叫
# 本段保留給本機測試
# =============================================================================
if __name__ == '__main__':
    # 本地測試用
    app.run(host='0.0.0.0', port=5000)
 
# =============================================================================
# 第7步：
# 建立 Telegram 背景傳送系統
# 目的：
# TradingView 不需要等待 Telegram
# Webhook 收到訊號後：
# 1. 放入 Queue
# 2. 立即回覆 TradingView 200
# 3. 背景 Thread 慢慢送 Telegram
# 解決：
# TradingView timeout
# =============================================================================
# =============================================================================
# 匯入 Queue
# Queue 是 Python 內建的排隊工具
# 功能：
# 先進來的訊息
# 先送出去
# FIFO:
# First In
# First Out
# =============================================================================
from queue import Queue
# =============================================================================
# 第8步：建立 Telegram 傳送佇列
# TradingView 訊號先放這裡
# 範例：
# telegram_queue
# [
#   "台指突破24000",
#   "KD黃金交叉"
# ]
# =============================================================================
telegram_queue = Queue()

# =============================================================================
# 第9步：Telegram 傳送函式
# 功能：真正呼叫 Telegram API
# 注意：
# 這個函式不直接給 webhook 使用，而是給背景 Thread 使用
# =============================================================================
def send_to_telegram(message: str):
    
    # 記錄開始時間，來觀察 Telegram 花多久
    t1 = time.time()
    """
    傳送訊息到 Telegram Bot參數:
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
        "chat_id": CHAT_ID,        # Telegram 群組或個人聊天室 ID
        "text": message            # 要傳送的訊息內容
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
        # 如果 Telegram timeout，目前你看不到「失敗花了多久」或網路錯誤
        # 如果連線失敗、網路中斷、
        # Telegram 太慢、超過 timeout
        # 就會進入這裡        
        print(#Telegram timeout，目前你看不到「失敗花了多久」
            "Telegram失敗耗時 =",
            round(time.time() - t1, 3),
            "秒"
        )
        print("Telegram timeout:", e)
# =============================================================================
# 第10步：背景 Telegram Worker，# 這是一個永遠等待工作的執行緒#
# 流程：
# Queue 有訊息
#       |
#       ▼
# worker取出
#       |
#       ▼
# send_to_telegram()
# =============================================================================

def telegram_worker():
    print("✅ Telegram背景執行緒啟動")
    print("Worker Queue ID=",id(telegram_queue))
    while True:
        # 等待 Queue 新訊息
        message = telegram_queue.get()
        print("③ Queue取出，開始送TG",time.strftime("%H:%M:%S"))

        try:            
            send_to_telegram(message)# 實際送Telegram
            print("④ TG 完成", time.strftime("%H:%M:%S"))
        except Exception as e:
            print("Telegram Worker Error:", e )
        finally:
            # 告知Queue：
            # 這筆完成
            telegram_queue.task_done()
# =============================================================================
# 第11步：啟動背景 Thread
# daemon=True
# 表示：
# Flask關閉
# Thread也一起結束
# =============================================================================
print("③ Telegram Worker 啟動", time.strftime("%H:%M:%S"))
threading.Thread(
    target=telegram_worker,
    daemon=True
).start()

# =============================================================================
# 第12步：測試 Telegram#
# 使用方式：#
# 瀏覽器輸入：#
# https://你的Render網址/test
# 成功：
# Telegram收到：
# 🚀 測試訊息：Telegram 發送功能正常！
# =============================================================================
@app.route("/test",methods=["GET"])
def test_telegram():
    # 注意：
    # 這裡不是直接send
    # 而是放入Queue
    # 模擬Webhook流程
    telegram_queue.put("🚀 測試訊息：Telegram 發送功能正常！")
    return ("✅ 測試訊息已加入Telegram Queue")

# =============================================================================
# 第13步：
# TradingView Webhook 接收中心
# 功能：
# 1. 接收 TradingView 傳來 JSON
# 2. 顯示原始資料
# 3. 解析 JSON
# 4. 建立 Telegram 訊息
# 5. 丟入 telegram_queue
# 注意：
# 這裡「不直接傳 Telegram」
# 只負責快速接收
# =============================================================================

@app.route("/webhook",methods=["POST"])
def webhook():
    import uuid
    # ============================================================
    # 建立唯一 Request ID
    # 用來區分每一次 TradingView webhook
    # ============================================================
    reqid = uuid.uuid4().hex[:8]
    # ============================================================
    # 記錄 webhook 開始時間
    # 用來測量：
    # TradingView → Flask → return 200 花多久
    # ============================================================
    start_time = time.time()
    print("\n")
    print("=" * 70)
    print(f"🚀 WEBHOOK START  Request ID: {reqid}")
    print("時間 =", datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"))
    print("=" * 70)
    print("Method =", request.method)
    print("Path   =", request.path)
    print("X-Request-Start =", request.headers.get("X-Request-Start"))
    # ============================================================
    # Render Proxy 收到 Request 的時間
    # X-Request-Start 是 Render 內部記錄的 Unix Timestamp(微秒)
    # 換算後方便與 Flask 收到時間比較
    # ============================================================
    
    x_request_start = request.headers.get("X-Request-Start")
    
    if x_request_start:
        try:
            proxy_time = datetime.utcfromtimestamp(
                int(x_request_start) / 1_000_000
            )
    
            print(
                "Render Proxy 收到時間(UTC) =",
                proxy_time.strftime("%Y-%m-%d %H:%M:%S.%f")
            )
    
            print(
                "Flask 收到時間(UTC)       =",
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")
            )
    
            print(
                "Render Proxy → Flask =",
                round(
                    (
                        datetime.utcnow() - proxy_time
                    ).total_seconds(),
                    6
                ),
                "秒"
            )
    
        except Exception as ex:
            print("X-Request-Start 解析失敗：", ex)


    print("Rndr-Id         =", request.headers.get("Rndr-Id"))
    print(
        f"① [{reqid}] Flask 收到 request :",
        datetime.now().strftime("%H:%M:%S.%f")
    )
    try:
        # ========================================================
        # 第1部分：
        # 印出 TradingView 原始資料
        # request.data:
        # 還沒有解析前的原始位元組資料
        # 用來除錯非常重要
        # ========================================================
        print("\n========== RAW DATA ==========")
        raw_bytes = request.data
        print(raw_bytes.decode("utf-8"))
        print(
            f"② [{reqid}] request.data 讀取完成 :",
            datetime.now().strftime("%H:%M:%S.%f"),
            "耗時",
            round(time.time()-start_time,6),
            "秒"
        )
        # ========================================================
        # 印出 HTTP Header
        # 可以確認：
        # TradingView 是否正確送 JSON
        # ========================================================
        print("\n========== HTTP HEADER ==========")
        print(request.headers)
        # ========================================================
        # 第2部分：
        # JSON解析
        # TradingView送：
        # {
        #    "signal":"BUY",
        #    "price":23000
        # }
        # 變成 Python dictionary
        # ========================================================
        raw = request.get_data(as_text=True)
        print("RAW =", raw)
        # 修正 TradingView 傳來的非法換行
        raw = raw.replace("\r\n", "\\n")
        raw = raw.replace("\n", "\\n")
        data = json.loads(raw)
        print("\n========== JSON DATA ==========")
        print(data)
        print(
            f"③ [{reqid}] JSON解析完成 :",
            datetime.now().strftime("%H:%M:%S.%f"),
            "耗時",
            round(time.time()-start_time,6),
            "秒"
        )
        # ========================================================
        # 第3部分：
        # 建立 Telegram 訊息
        # json.dumps:
        # dictionary
        #       ↓
        # 文字
        # ========================================================
        msg = (
            "📊 TG收到 TradingView Webhook\n\n"
            +
            json.dumps(
                data,
                indent=2,
                ensure_ascii=False
            )
        )
        print("\n========== Telegram Message ==========")
        print(msg)
        # ========================================================
        # 第4部分：
        # 放入 Telegram Queue
        # 注意：
        # 這裡沒有：
        # send_to_telegram(msg)
        # 因為直接送會造成 timeout
        # Queue 放入後立即返回
        # ========================================================
       
        print("Webhook Queue ID=",id(telegram_queue))        
        telegram_queue.put(msg)   
        print("✅ 已放入 Telegram Queue")
        print("Queue Size =", telegram_queue.qsize())
                
        print(
            f"④ [{reqid}] Queue加入完成 :",
            datetime.now().strftime("%H:%M:%S.%f"),
            "耗時",
            round(time.time()-start_time,6),
            "秒"
        )
        # ========================================================
        # 計算 Webhook 處理時間
        # 正常應該：
        # 0.001 ~ 0.01 秒左右
        # ========================================================
        webhook_time = time.time() - start_time
        print(
            "Webhook處理時間 =",
            round(webhook_time,4),
            "秒"
        )
        # ========================================================
        # 建立 HTTP Response
        # 測量：
        # Flask 建立回覆花多少時間
        # ========================================================
        print(
            f"⑤ [{reqid}] 準備建立 HTTP Response :",
            datetime.now().strftime("%H:%M:%S.%f")
        )
        resp = jsonify({
            "status": "success",
            "message": "Webhook received"
        })
        print(
            f"⑥ [{reqid}] Response 建立完成 :",
            datetime.now().strftime("%H:%M:%S.%f"),
            "總耗時",
            round(time.time()-start_time,6),
            "秒"
        )
        # ========================================================
        # 最重要：
        # 立即回覆 TradingView
        # TradingView只關心：
        # 3秒內收到 HTTP 200
        # ========================================================
        print(
            f"⑦ [{reqid}] Flask return 200 前 :",
            datetime.now().strftime("%H:%M:%S.%f")
        )

        print(
            f"⑧ [{reqid}] Flask 即將把 HTTP200 交給 Gunicorn :",
            datetime.now().strftime("%H:%M:%S.%f")
        )
        
        print("=" * 70)
        print(
            f"✅ WEBHOOK END Request ID={reqid}",
            "總耗時",
            round(time.time()-start_time,6),
            "秒"
        )
        print("=" * 70)
        return resp,200
    except Exception as e:
        # ========================================================
        # 錯誤處理
        # ========================================================
        import traceback
        print("\n========== ERROR ==========")
        print(
            f"❌ Request ID={reqid}"
        )
        print(str(e))
        traceback.print_exc()
        print(
            "Webhook失敗耗時 =",
            round(time.time()-start_time,4),
            "秒"
        )
        return jsonify({
            "status":"error",
            "message":str(e)
        }),500
# =============================================================================
# 第13步：完成目前完整流程：

# TradingView
#       |
#       ▼
#
# /webhook
#
#       |
#       |
#       ├── request.data
#       ├── JSON解析
#       ├── 建立msg
#       |
#       ▼
#
# telegram_queue.put()
#
#       |
#       ▼
#
# return 200
#
#
#       (TradingView 不 timeout)
#
#
# 背景：
#
# telegram_worker()
#
#       |
#       ▼
#
# Telegram API

# 下一段：
#
# 第14步：
#
# event_queue + /events/latest
#
# 提供給 local_speaker.py
#
# =============================================================================



# =============================================================================
# 第14步： 全域鎖與事件佇列
# event_queue 事件儲存系統
# 功能：保存 TradingView webhook事件
# 給：local_speaker.py 讀取並播放聲音
# =============================================================================
import threading
lock = threading.Lock()  # 🔒 用於確保多執行緒修改 event_queue 時不衝突
event_queue = []         # 🧱 儲存最近收到的事件（FIFO）
# ==========================
# 提供 local_speaker 讀取事件
# ==========================
@app.route('/events/latest', methods=['GET'])
def latest_events():

    limit = int(request.args.get("limit", 5))

    with lock:
        events = event_queue[-limit:]

    return jsonify(events)


# =============================================================================
# 第15步：程式啟動入口
# Render部署檢查
# =============================================================================
# =============================================================================
# 啟動前檢查函式
## 目的：
## Render重新啟動時
# 確認重要設定
## =============================================================================
def startup_check():
    print("\n==============================")
    print("🚀 TradingView Webhook Server")
    print("==============================\n")
    # --------------------------------------------------
    # 檢查 Telegram Token
    # --------------------------------------------------
    if TELEGRAM_TOKEN:
        print(            "✅ TELEGRAM_TOKEN OK"       )
    else:
        print(            "❌ TELEGRAM_TOKEN 缺少"        )
    # --------------------------------------------------
    # 檢查 Chat ID
    # --------------------------------------------------
    if CHAT_ID:
        print(
            "✅ CHAT_ID OK"
        )
    else:
        print(
            "❌ CHAT_ID 缺少"
        )

    # --------------------------------------------------
    # 檢查 Local Speaker
    # --------------------------------------------------
    if LOCAL_SPEAKER_URL:
        print(
            "✅ LOCAL_SPEAKER_URL OK"
        )
    else:
        print(
            "⚠️ LOCAL_SPEAKER_URL 未設定"
        )
    print("\n==============================")
    print("Webhook網址:")
    print("/webhook")
    print("Telegram測試:")
    print("/test")
    print("語音事件:")
    print("/events/latest")
    print("==============================\n")
# =============================================================================
# 執行啟動檢查
#
# Render啟動時會看到結果
#
# =============================================================================
#startup_check()
# =============================================================================
# 本機測試啟動
##
# Render正式環境：
## 使用 gunicorn
### 例如：
## gunicorn app:app
#
# 不會走下面
##
# 本機測試：
## python app.py
## 會走下面
## =============================================================================
if __name__ == "__main__":
    print(
        "🔥 本機 Flask 測試模式啟動"
    )
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )


# =============================================================================
# 
# # 建立 Flask 路由，當收到 POST 請求到 /webhook 時執行 webhook() 函式
# @app.route('/webhook', methods=['POST'])
# def webhook():# 定義 webhook 處理函式
#  # 函式說明：接收 TradingView 傳來的 Webhook JSON 資料並轉發到 Telegram
#     """接收 TradingView 的 Webhook JSON 並轉發到 Telegram + 本地語音端"""
#     """
#     📩 TG接收 TradingView 傳來的 JSON 訊號。
#     處理步驟：
#     1. 解析 JSON 資料
#     2. 翻譯（可選）
#     3. 建立唯一事件 ID
#     4. 推送到 Telegram
#     5. 推送到本地語音端
#     6. 儲存事件於 event_queue 供查詢
#     """
#     # ============================================================
#     #加一個時間測量在 webhook 開頭：
#     import time
#     start_time = time.time()
#     # ============================================================
# # =============================================================================
# #     global event_id
# # =============================================================================
# 
# 
#     try:
#         # 顯示原始收到的資料區塊標題
#         print("========== 印出原始 Request BodRAW DATA 未解析前的位元組資料）==========")
#         print(request.data)# 印出原始 Request Body（未解析前的位元組資料）
#         # 顯示 HTTP Header 區塊標題
#         print("========== 印出所有 HTTP Header 資訊 ==========")
#         print(request.headers)# 印出所有 HTTP Header 資訊
# 
#         # 強制將收到的內容解析成 JSON# 即使 Content-Type 不是 application/json 也會嘗試解析
#         data = request.get_json(force=True)
#         # 顯示解析後 JSON 區塊標題
#         print("========== 顯示解析後JSON DATA區塊標題 ==========")
#         print(data)  # 印出解析完成的 Python Dictionary
#         # 組合要傳送到 Telegram 的訊息內容
#         msg = (
#             # 第一行標題
#             f"📊 TG收到由Tv Webhook資料：\n"
#             # 將 JSON 格式化輸出
#             # indent=2 代表縮排 2 格
#             # ensure_ascii=False 代表保留中文不要轉 Unicode
#             f"{json.dumps(data, indent=2, ensure_ascii=False)}"
#         )
# 
#         # ==========================
#         # Telegram開始計時
#         # ==========================
#         tg_start = time.time()
#         # 發送 Telegram
#         send_to_telegram(msg)# 呼叫 Telegram 發送函式
#         # ==========================
#         # 儲存事件供 local_speaker 讀取
#         # ==========================
#         global event_queue
#         
#         with lock:
#             event_queue.append({
#                 "id": int(time.time()),
#                 "data": data
#             })
#         
#             # 只保留最近100筆
#             if len(event_queue) > 100:
#                 event_queue.pop(0)
#         
#         print("目前 event_queue =", event_queue)
# 
#        
# 
# 
#         
#         # ==========================
#         # Telegram耗時
#         # ==========================
#         print(
#             "Telegram區段耗時 =",
#             round(time.time() - tg_start, 3),
#             "秒"
#         )
# 
#         # ==========================
#         # Webhook總耗時
#         # ==========================
#         print(
#             "Webhook總耗時 =",
#             round(time.time() - start_time, 3),
#             "秒"
#         )
#         # ==========================
#         # 回傳成功給 TradingView
#         # ==========================
#         return jsonify({# 回傳成功
#             "status": "success",
#             "message": "Data received"
#         }), 200
# 
#     except Exception as e:
# 
#         import traceback
# 
#         print("========== ERROR ==========")
# 
#         print(str(e))
# 
#         traceback.print_exc()
# 
#         # ==========================
#         # 發生錯誤時也計算耗時
#         # ==========================
#         print(
#             "Webhook失敗耗時 =",
#             round(time.time() - start_time, 3),
#             "秒"
#         )
# 
#         return jsonify({
#             "status": "error",
#             "message": str(e)
#         }), 500
#     
#     
# # =============================================================================
# # # ==========================
# # # 測試 Telegram 傳送訊息
# # # ==========================
# # # =============================================================================
# # # @app.route('/test', methods=['GET'])
# # # =============================================================================
# # def test_telegram():
# #     """手動測試 Telegram 是否能收到訊息"""
# #     send_to_telegram("🚀 測試訊息：Telegram 發送功能正常！")
# #     return "✅ 測試訊息已發送至 Telegram"
# # =============================================================================
# =============================================================================


