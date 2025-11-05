# ============================================================
# app_Render.py - Render 部署版 TradingView Webhook
# ============================================================

from flask import Flask, request, jsonify
import requests, json, os

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
TELEGRAM_TOKEN = os.environ.get("8359395795:AAFywYmUfYeZlwGkUW-gBLNtcexoXUP-haA")
CHAT_ID = os.environ.get("831846934")

if not TELEGRAM_TOKEN or not CHAT_ID:
    print("❌ 請先在 Render 環境變數設定 TELEGRAM_TOKEN 與 CHAT_ID")

# ==========================
# 定義 Telegram 傳訊函式
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
# 測試首頁
# ==========================
@app.route('/')
def home():
    return "✅ TradingView Webhook Server 運作中！"

# ==========================
# 測試 Telegram 傳送訊息
# ==========================
@app.route('/test', methods=['GET'])
def test_telegram():
    """手動測試 Telegram 是否能收到訊息"""
    send_to_telegram("🚀 測試訊息：Telegram 發送功能正常！")
    return "✅ 測試訊息已發送至 Telegram"

# ==========================
# Webhook 接收 TradingView 訊息
# ==========================
@app.route('/webhook', methods=['POST'])
def webhook():
    """接收 TradingView 的 Webhook JSON 並轉發到 Telegram"""
    try:
        # 強制解析 JSON
        data = request.get_json(force=True)
        print("📩 收到 TradingView 資料:", data)

        # 組成訊息
        msg = f"📊 TradingView Webhook 收到資料：\n{json.dumps(data, indent=2, ensure_ascii=False)}"
        send_to_telegram(msg)

        # 回傳成功訊息
        return jsonify({"status": "success", "message": "Data received"}), 200
    except Exception as e:
        print("❌ Webhook 錯誤:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

# ==========================
# 程式入口
# ==========================
if __name__ == '__main__':
    # 本地測試用
    app.run(host='0.0.0.0', port=5000)
