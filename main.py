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
def home(): return "AI Trader Pro is LIVE"

def send_msg(text):
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=10)
    except: pass

def send_plot(symbol, df, caption, levels=None):
    try:
        plt.figure(figsize=(12, 6))
        # גרף מחיר וממוצעים 50, 150, 200
        plt.plot(df.index[-120:], df['Close'].tail(120), label='Price', color='black', linewidth=1.5)
        plt.plot(df.index[-120:], df['SMA50'].tail(120), label='SMA 50', color='blue', alpha=0.6)
        plt.plot(df.index[-120:], df['SMA150'].tail(120), label='SMA 150', color='orange', alpha=0.6)
        plt.plot(df.index[-120:], df['SMA200'].tail(120), label='SMA 200', color='red', linewidth=2)
        
        if levels:
            for l in levels:
                plt.axhline(y=l, color='gray', linestyle='--', alpha=0.3)

        plt.title(f"Detailed Analysis: {symbol}")
        plt.legend()
        plt.grid(True, alpha=0.1)
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        plt.close()
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", data={'chat_id': CHAT_ID, 'caption': caption, 'parse_mode': 'Markdown'}, files={'photo': buf}, timeout=20)
    except: pass

def analyze_pro(symbol, spy_perf, min_score=3):
    try:
        data = yf.download(symbol, period="2y", interval="1d", progress=False)
        if data.empty or len(data) < 200: return None, 0, "", []
        
        df = data.copy()
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
        close = df['Close'].dropna()
        df['SMA50'] = close.rolling(50).mean()
        df['SMA150'] = close.rolling(150).mean()
        df['SMA200'] = close.rolling(200).mean()
        
        last_p = float(close.iloc[-1])
        score = 0
        details = []

        # שיטת ניקוד קבועה ואמינה
        if last_p > df['SMA50'].iloc[-1]: score += 2; details.append("✅ מעל SMA50")
        if last_p > df['SMA150'].iloc[-1]: score += 2; details.append("✅ מעל SMA150")
        if last_p > df['SMA200'].iloc[-1]: score += 3; details.append("✅ מעל SMA200 (מגמה)")
        
        # חוזק יחסי
        perf_1m = (last_p / float(close.iloc[-21])) - 1
        if perf_1m > spy_perf: score += 3; details.append("💪 חוזק יחסי חיובי")

        # תמיכה והתנגדות שנתיים
        sup = float(df['Low'].tail(252).min())
        res = float(df['High'].tail(252).max())
        
        # בדיקת שבירה
        is_breakdown = last_p < float(df['Low'].tail(10).min()) * 1.01

        if score >= min_score or is_breakdown:
            rec = "🔴 מכירה דחופה" if is_breakdown else ("💎 קנייה" if score >= 8 else "⚖️ מעקב")
            msg = (f"🔍 **{symbol} | Pro Score: {score}/10**\n"
                   f"📢 המלצה: *{rec}*\n"
                   f"💰 מחיר: `{last_p:.2f}`\n"
                   f"📏 שיא שנתי: `{res:.2f}` | ⚓ שפל שנתי: `{sup:.2f}`\n"
                   f"------------------\n" + "\n".join(details))
            return df, score, msg, [sup, res]
        return None, 0, "", []
    except: return None, 0, "", []

def scanner():
    while True:
        try:
            spy = yf.download('SPY', period="1y", progress=False)['Close'].squeeze()
            if isinstance(spy, pd.DataFrame): spy = spy.iloc[:, 0]
            spy_perf = (float(spy.iloc[-1]) / float(spy.iloc[-21])) - 1
            
            # רשימת מניות מגוונת שנסרקת בלולאה יציבה
            tickers = ['NVDA', 'AAPL', 'TSLA', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NFLX', 'AMD', 'COST', 
                       'LUMI.TA', 'POLI.TA', 'BEZQ.TA', 'ICL.TA', 'NICE.TA', 'DSCT.TA', 'BTC-USD', 'GC=F']
            
            send_msg(f"🛰️ סורק אוטומטי התחיל סבב על {len(tickers)} נכסים...")
            for s in tickers:
                df, score, msg, lvls = analyze_pro(s.replace('.', '-'), spy_perf)
                if df is not None:
                    send_plot(s, df, msg, lvls)
                time.sleep(3) # מנוחה ארוכה יותר כדי למנוע קריסה
            
            send_msg("✅ סבב סריקה הושלם.")
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
                    df, score, msg, lvls = analyze_pro(t, spy_perf, min_score=0)
                    if df is not None: send_plot(t, df, msg, lvls)
        except: time.sleep(2)

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    Thread(target=scanner).start()
    listen()
