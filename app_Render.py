# ============================================================
# app_Render.py - Render 部署版 TradingView Webhook + 即時翻譯
# ============================================================

from flask import Flask, request, jsonify  # Flask 用於建立 Web 伺服器
import requests, json, os                  # requests 用於 HTTP 請求，os 用於讀取環境變數
from deep_translator import GoogleTranslator  # 用於即時翻譯文字
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
    """
    接收 TradingView 的 Webhook JSON 並翻譯後轉發到 Telegram
    """
    try:
        # 強制解析 JSON
        data = request.get_json(force=True)
        print("📩 收到 TradingView 資料:", data)

        # 組成訊息文字# Telegram 訊息
        original_msg = f"📊 TradingView Webhook 收到資料：\n{json.dumps(data, indent=2, ensure_ascii=False)}"

        # ===== 即時翻譯訊息 =====
        translated_msg = translate_text(original_msg)

        # ===== 發送翻譯後訊息到 Telegram =====
        send_to_telegram(translated_msg)
        
        # ===== 傳送到本地語音端 =====
        send_to_local_speaker(data)
        
        
        # 回傳成功訊息
        #return jsonify({"status": "success", "message": "Data received"}), 200
        return jsonify({"status": "success", "message": "已發送到 Telegram + 語音端"}), 200
    except Exception as e:
        print("❌ Webhook 錯誤:", e)
        return jsonify({"status": "error", "message": str(e)}), 500
# ==========================
# 程式入口
# ==========================
if __name__ == '__main__':
    # 本地測試用
    app.run(host='0.0.0.0', port=5000)



