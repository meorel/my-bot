import yfinance as yf
import pandas as pd
import requests
import time
from flask import Flask
from threading import Thread

TOKEN = "8456706482:AAFUhE3sdD7YZh4ESz1Mr4V15zYYLXgYtuM"
CHAT_ID = "605543691"

app = Flask('')
@app.route('/')
def home(): return "Scanner Diagnostics Active"

def send_msg(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.get(url, params={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"})

def get_sp500():
    return ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NFLX', 'LUMI.TA', 'POLI.TA']

def analyze_diagnostic(symbol, spy_perf):
    try:
        # כאן שיניתי את התקופה ל-2y כדי לוודא שיש מספיק נתונים לממוצע 200
        df = yf.download(symbol, period="2y", interval="1d", progress=False)
        if df.empty or len(df) < 200: 
            return None
        
        df['SMA50'] = df['Close'].rolling(window=50).mean()
        df['SMA150'] = df['Close'].rolling(window=150).mean()
        df['SMA200'] = df['Close'].rolling(window=200).mean()
        df['Vol_Avg'] = df['Volume'].rolling(window=20).mean()
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        score = 0
        details = []

        if last['Close'] > last['SMA150']:
            score += 2
            details.append("📈 מעל 150")
        
        if last['Close'] > last['SMA200']:
            score += 2
            details.append("🔋 מעל 200")

        if last['Volume'] > last['Vol_Avg']:
            score += 2
            details.append("🔥 ווליום תקין")

        # רף נמוך מאוד של 2 נקודות רק כדי לראות שזה עובד!
        if score >= 2:
            msg = f"✅ **נמצאה התאמה: {symbol}** (ציון: {score})\n" + "\n".join(details)
            return msg
        return None
    except Exception as e:
        return f"⚠️ שגיאה בניתוח {symbol}: {str(e)}"

def diagnostic_loop():
    while True:
        try:
            send_msg("🛠️ **מתחיל בדיקת מערכת על 10 מניות מובילות...**")
            spy = yf.download('SPY', period="1y", progress=False)
            spy_perf = (spy['Close'].iloc[-1] / spy['Close'].iloc[-21]) - 1
            
            tickers = get_sp500()
            for s in tickers:
                res = analyze_diagnostic(s, spy_perf)
                if res:
                    send_msg(res)
                time.sleep(2)
            
            send_msg("🏁 **הבדיקה הסתיימה. האם קיבלת הודעות על המניות למעלה?**")
            time.sleep(600)
        except Exception as e:
            send_msg(f"❌ קריסה בלופ: {str(e)}")
            time.sleep(60)

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    diagnostic_loop()
