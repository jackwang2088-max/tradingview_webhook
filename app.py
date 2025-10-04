from flask import Flask, request
import threading

app = Flask(__name__)

signals = {
    "signal1": "開多",
    "signal2": "開空",
    "signal3": "平多",
    "signal4": "平空",
}

def handle_signal(signal_name, data):
    msg = signals.get(signal_name, "未知訊號")
    price = data.get("price", "")
    print(f"[Webhook] {msg} - 價格: {price}")

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    signal = data.get("signal")
    if signal:
        threading.Thread(target=handle_signal, args=(signal, data)).start()
    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
