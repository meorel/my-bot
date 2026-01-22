import yfinance as yf
import pandas as pd
import requests
import time
import io
import matplotlib.pyplot as plt
from flask import Flask
from threading import Thread

# --- הגדרות ---
TOKEN = "8456706482:AAFUhE3sdD7YZh4ESz1Mr4V15zYYLXgYtuM"
CHAT_ID = "605543691"

app = Flask('')
@app.route('/')
def home(): return "Scanner Online"

def send_msg(text):
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=10)
    except: pass

def send_plot(symbol, df, caption):
    try:
        plt.figure(figsize=(10, 5))
        plt.plot(df.index[-100:], df['Close'].tail(100), label='Price', color='blue')
        plt.title(f"Analysis: {symbol}")
        plt.grid(True, alpha=0.2)
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", data={'chat_id': CHAT_ID, 'caption': caption, 'parse_mode': 'Markdown'}, files={'photo': buf}, timeout=15)
    except: pass

def analyze_stock(symbol, spy_perf, min_score=3): # רף כניסה נמוך יותר
    try:
        data = yf.download(symbol, period="1y", interval="1d", progress=False)
        if data.empty or len(data) < 50: return None, 0, ""
        
        df = data.copy()
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
        close = df['Close'].dropna()
        last_p = float(close.iloc[-1])
        
        # חישוב אינדיקטורים
        sma50 = close.rolling(50).mean().iloc[-1]
        sup_year = float(df['Low'].min())
        res_year = float(df['High'].max())
        
        score = 0
        details = []
        
        if last_p > sma50: score += 4; details.append("📈 מעל מגמת 50 יום")
        if (last_p / float(close.iloc[-21])) - 1 > spy_perf: score += 4; details.append("💪 עוצמה יחסית גבוהה")
        if last_p < sup_year * 1.05: score += 2; details.append("⚓ קרוב לתמיכה שנתית (הזדמנות)")

        is_sell = last_p < float(df['Low'].tail(10).min()) * 1.005
        
        if score >= min_score or is_sell:
            rec = "🔴 למכירה" if is_sell else ("💎 קנייה" if score >= 7 else "⚖️ מעקב")
            msg = (f"🔍 **{symbol} | ציון: {score}/10**\n"
                   f"📢 המלצה: *{rec}*\n"
                   f"💰 מחיר: `{last_p:.2f}`\n"
                   f"📏 התנגדות: `{res_year:.2f}` | ⚓ תמיכה: `{sup_year:.2f}`\n"
                   f"------------------\n" + "\n".join(details))
            return df, score, msg
        return None, 0, ""
    except: return None, 0, ""

def scanner():
    while True:
        try:
            send_msg("🛰️ **סורק AI מתחיל סבב על מניות מובילות...**")
            spy = yf.download('SPY', period="1y", progress=False)['Close'].squeeze()
            if isinstance(spy, pd.DataFrame): spy = spy.iloc[:, 0]
            spy_perf = (float(spy.iloc[-1]) / float(spy.iloc[-21])) - 1
            
            # רשימה מורחבת
            tickers = ['NVDA', 'AAPL', 'TSLA', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NFLX', 'AMD', 'AVGO', 'BTC-USD', 'ETH-USD', 'GC=F', 'LUMI.TA', 'POLI.TA', 'NICE.TA']
            
            found = 0
            for s in tickers:
                df, score, msg = analyze_stock(s.replace('.', '-'), spy_perf)
                if df is not None:
                    send_plot(s, df, msg)
                    found += 1
                time.sleep(2)
            
            send_msg(f"✅ סבב הסתיים. נמצאו {found} מניות מעניינות.")
            time.sleep(3600)
        except: time.sleep(60)

def listen():
    last_id = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={last_id+1}&timeout=30"
            res = requests.get(url, timeout=35).json()
            for u in res.get("result", []):
                last_id = u["update_id"]
                if "message" in u and "text" in u["message"]:
                    t = u["message"]["text"].upper().strip()
                    spy = yf.download('SPY', period="1y", progress=False)['Close'].squeeze()
                    if isinstance(spy, pd.DataFrame): spy = spy.iloc[:, 0]
                    spy_perf = (float(spy.iloc[-1]) / float(spy.iloc[-21])) - 1
                    df, score, msg = analyze_stock(t, spy_perf, min_score=0)
                    if df is not None: send_plot(t, df, msg)
        except: time.sleep(2)

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    Thread(target=scanner).start()
    listen()
