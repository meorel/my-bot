import yfinance as yf
import pandas as pd
import requests
import time
import io
import matplotlib.pyplot as plt
import numpy as np
from flask import Flask
from threading import Thread

# --- הגדרות מערכת ---
TOKEN = "8456706482:AAFUhE3sdD7YZh4ESz1Mr4V15zYYLXgYtuM"
CHAT_ID = "605543691"

app = Flask('')
@app.route('/')
def home(): return "AI Pro Trader System - Status: Active"

def send_msg(text):
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=10)
    except: pass

def send_plot(symbol, df, caption, levels=None):
    try:
        plt.figure(figsize=(12, 7))
        # מחיר וממוצעים
        plt.plot(df.index[-150:], df['Close'].tail(150), label='Price', color='black', linewidth=1.5)
        plt.plot(df.index[-150:], df['SMA50'].tail(150), label='SMA 50 (Short)', color='blue', alpha=0.7)
        plt.plot(df.index[-150:], df['SMA150'].tail(150), label='SMA 150 (Mid)', color='orange', alpha=0.7)
        plt.plot(df.index[-150:], df['SMA200'].tail(150), label='SMA 200 (Long)', color='red', alpha=0.8, linewidth=2)
        
        # רמות תמיכה והתנגדות
        if levels:
            for l in levels:
                color = 'green' if l < df['Close'].iloc[-1] else 'red'
                plt.axhline(y=l, color=color, linestyle='--', alpha=0.2)

        plt.title(f"Detailed Analysis: {symbol}", fontsize=14)
        plt.grid(True, alpha=0.15)
        plt.legend(loc='best')
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=120)
        buf.seek(0)
        plt.close()
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", data={'chat_id': CHAT_ID, 'caption': caption, 'parse_mode': 'Markdown'}, files={'photo': buf}, timeout=20)
    except Exception as e:
        print(f"Plot Error: {e}")

def get_levels(df):
    high_all = float(df['High'].tail(252).max())
    low_all = float(df['Low'].tail(252).min())
    curr = float(df['Close'].iloc[-1])
    # רמות משמעותיות לפי פיבונאצ'י ושיאים
    levels = [high_all, low_all, (high_all + low_all)/2]
    return sorted(list(set(levels)))

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
        reasons = []

        # לוגיקת ניקוד קבועה
        if last_p > df['SMA50'].iloc[-1]: score += 2; reasons.append("✅ מעל SMA50 (טווח קצר)")
        if last_p > df['SMA150'].iloc[-1]: score += 2; reasons.append("✅ מעל SMA150 (טווח בינוני)")
        if last_p > df['SMA200'].iloc[-1]: score += 3; reasons.append("✅ מעל SMA200 (מגמה ראשית)")
        
        # חוזק יחסי
        perf_1m = (last_p / float(close.iloc[-21])) - 1
        if perf_1m > spy_perf: score += 3; reasons.append("💪 חזקה מהשוק (RS)")

        levels = get_levels(df)
        res = min([l for l in levels if l > last_p * 1.01] or [df['High'].max()])
        sup = max([l for l in levels if l < last_p * 0.99] or [df['Low'].min()])

        if score >= min_score:
            rec = "💎 קנייה חזקה" if score >= 8 else "⚖️ מעקב"
            msg = (f"🔍 **{symbol} | Pro Score: {score}/10**\n"
                   f"📢 המלצה: *{rec}*\n"
                   f"💰 מחיר: `{last_p:.2f}`\n"
                   f"📏 התנגדות: `{res:.2f}` | ⚓ תמיכה: `{sup:.2f}`\n"
                   f"------------------\n" + "\n".join(reasons))
            return df, score, msg, levels
        return None, 0, "", []
    except: return None, 0, "", []

def scanner():
    while True:
        try:
            spy = yf.download('SPY', period="1y", progress=False)['Close'].squeeze()
            if isinstance(spy, pd.DataFrame): spy = spy.iloc[:, 0]
            spy_perf = (float(spy.iloc[-1]) / float(spy.iloc[-21])) - 1
            send_msg("🛰️ **סורק מורחב התחיל: ארה"ב (S&P500) + ישראל...**")
            
            # רשימה מורחבת
            tickers = [
                'NVDA', 'AAPL', 'TSLA', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NFLX', 'AMD', 'AVGO', 'COST', 'SMCI',
                'LUMI.TA', 'POLI.TA', 'BEZQ.TA', 'ICL.TA', 'NICE.TA', 'DSCT.TA', 'FIBI.TA', 'AZRG.TA',
                'BTC-USD', 'ETH-USD', 'GC=F', 'CL=F'
            ]
            
            found = 0
            for s in tickers:
                df, score, msg, lvls = analyze_pro(s.replace('.', '-'), spy_perf)
                if df is not None:
                    send_plot(s, df, msg, lvls)
                    found += 1
                time.sleep(1.5)
            
            send_msg(f"✅ סבב הסתיים. נמצאו {found} הזדמנויות רלוונטיות.")
            time.sleep(7200) # סריקה כל שעתיים
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
                    else: send_msg(f"❌ לא נמצאו נתונים עבור {t}")
        except: time.sleep(2)

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    Thread(target=scanner).start()
    listen()
