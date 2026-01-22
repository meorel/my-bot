import yfinance as yf
import pandas as pd
import requests
import time
import io
import matplotlib.pyplot as plt
import numpy as np
from flask import Flask
from threading import Thread

# --- הגדרות ---
TOKEN = "8456706482:AAFUhE3sdD7YZh4ESz1Mr4V15zYYLXgYtuM"
CHAT_ID = "605543691"

app = Flask('')
@app.route('/')
def home(): return "System Online & Responsive"

def send_msg(text):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.get(url, params={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=10)
    except: pass

def send_plot(symbol, df, caption):
    try:
        plt.figure(figsize=(10, 5))
        plt.plot(df.index[-100:], df['Close'].tail(100), label='Price', color='blue')
        plt.plot(df.index[-100:], df['SMA50'].tail(100), label='SMA50', color='orange')
        plt.plot(df.index[-100:], df['SMA200'].tail(100), label='SMA200', color='red')
        plt.title(f"{symbol} Analysis")
        plt.grid(True, alpha=0.2)
        plt.legend()
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()
        url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
        requests.post(url, data={'chat_id': CHAT_ID, 'caption': caption, 'parse_mode': 'Markdown'}, files={'photo': buf}, timeout=15)
    except: pass

def get_pro_list():
    try:
        # רשימה מאובטחת של מניות מובילות + ישראל + קריפטו
        base = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'TSLA', 'META', 'AVGO', 'NFLX', 'COST']
        isr = ['LUMI.TA', 'POLI.TA', 'BEZQ.TA', 'NICE.TA', 'ICL.TA']
        crypto = ['BTC-USD', 'ETH-USD', 'GC=F', 'CL=F']
        # נסיעה להביא את ה-S&P 500
        sp500 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]['Symbol'].head(50).tolist()
        return list(set(base + isr + crypto + sp500))
    except:
        return ['AAPL', 'NVDA', 'TSLA', 'BTC-USD', 'GC=F', 'LUMI.TA']

def analyze_logic(symbol, spy_perf, min_score=5):
    try:
        df = yf.download(symbol, period="1y", interval="1d", progress=False)
        if df.empty or len(df) < 100: return None, 0, ""
        
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        close = df['Close'].squeeze()
        df['SMA50'] = close.rolling(50).mean()
        df['SMA200'] = close.rolling(200).mean()
        
        last_p = float(close.iloc[-1])
        prev_p = float(close.iloc[-2])
        score = 0
        details = []
        is_alert = False

        # 1. צלב זהב ופריצות
        if df['SMA50'].iloc[-1] > df['SMA200'].iloc[-1] and df['SMA50'].iloc[-2] <= df['SMA200'].iloc[-2]:
            score += 5; details.append("🌟 צלב זהב טרי!")
        
        res_year = float(df['High'].iloc[:-1].max())
        sup_year = float(df['Low'].iloc[:-1].min())

        if last_p > res_year:
            score += 3; details.append("🚀 פריצת שיא שנתי!")
        elif last_p < sup_year:
            is_alert = True; details.append("🚨 שבירת תמיכה שנתית!")

        # 2. גאפים פתוחים
        if float(df['Open'].iloc[-1]) > float(close.iloc[-2]) * 1.02:
            details.append("🕳️ גאפ פתיחה עוצמתי")

        # 3. חוזק יחסי
        perf = (last_p / float(close.iloc[-21])) - 1
        if perf > spy_perf: score += 2; details.append("💪 חזקה מהשוק")

        if score >= min_score or is_alert:
            rec = "🔴 מכירה" if is_alert else ("💎 קנייה" if score >= 7 else "⚖️ מעקב")
            msg = (f"🔍 **{symbol} | ציון: {score}/10**\n"
                   f"📢 המלצה: *{rec}*\n"
                   f"💰 מחיר: `{last_p:.2f}`\n"
                   f"📏 התנגדות: `{res_year:.2f}` | ⚓ תמיכה: `{sup_year:.2f}`\n"
                   f"------------------\n" + "\n".join(details))
            return df, score, msg
        return None, 0, ""
    except: return None, 0, ""

def scanner_loop():
    while True:
        try:
            spy = yf.download('SPY', period="1y", progress=False)['Close'].squeeze()
            spy_perf = (float(spy.iloc[-1]) / float(spy.iloc[-21])) - 1
            send_msg("🛰️ **סורק אוטומטי התחיל סבב...**")
            
            tickers = get_pro_list()
            found = 0
            for s in tickers:
                s = s.replace('.', '-')
                df, score, msg = analyze_logic(s, spy_perf, min_score=5)
                if df is not None:
                    send_plot(s, df, msg)
                    found += 1
                time.sleep(1.5) # קצב בטוח
            
            send_msg(f"✅ סבב הסתיים. נמצאו {found} הזדמנויות.")
            time.sleep(3600)
        except: time.sleep(60)

def telegram_listener():
    last_id = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={last_id+1}&timeout=30"
            res = requests.get(url, timeout=35).json()
            for u in res.get("result", []):
                last_id = u["update_id"]
                if "message" in u and "text" in u["message"]:
                    ticker = u["message"]["text"].upper().strip()
                    spy = yf.download('SPY', period="1y", progress=False)['Close'].squeeze()
                    spy_perf = (float(spy.iloc[-1]) / float(spy.iloc[-21])) - 1
                    df, score, msg = analyze_logic(ticker, spy_perf, min_score=-1)
                    if df is not None: send_plot(ticker, df, msg)
                    else: send_msg(f"❌ לא נמצאו נתונים עבור {ticker}")
        except: time.sleep(2)

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    Thread(target=scanner_loop).start() # סורק ברקע
    telegram_listener() # מגיב מיידית להודעות
