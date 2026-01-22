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
def home(): return "AI Master Scanner Active"

def send_msg(text):
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=10)
    except: pass

def send_plot(symbol, df, caption, sup, res):
    try:
        plt.figure(figsize=(12, 7))
        prices = df['Close'].tail(150)
        plt.plot(df.index[-150:], prices, label='Price', color='black', linewidth=1.5)
        plt.plot(df.index[-150:], df['SMA50'].tail(150), label='SMA 50', color='blue', alpha=0.6)
        plt.plot(df.index[-150:], df['SMA200'].tail(150), label='SMA 200', color='red', linewidth=2)
        
        plt.axhline(y=sup, color='green', linestyle='--', alpha=0.5, label='Support')
        plt.axhline(y=res, color='red', linestyle='--', alpha=0.5, label='Resistance')

        plt.title(f"AI Analysis: {symbol}")
        plt.legend(loc='best')
        plt.grid(True, alpha=0.1)
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=110)
        buf.seek(0)
        plt.close()
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", data={'chat_id': CHAT_ID, 'caption': caption, 'parse_mode': 'Markdown'}, files={'photo': buf}, timeout=25)
    except: pass

def detect_patterns(df):
    patterns = []
    close = df['Close'].tail(60).values
    lows = df['Low'].tail(60).values
    highs = df['High'].tail(60).values
    
    # תחתית כפולה (Double Bottom)
    if len(lows) > 40:
        min1 = np.min(lows[:20])
        min2 = np.min(lows[20:])
        if abs(min1 - min2) / min1 < 0.015:
            patterns.append("📉 תחתית כפולה (Double Bottom)")
            
    # פסגה כפולה (Double Top)
    if len(highs) > 40:
        max1 = np.max(highs[:20])
        max2 = np.max(highs[20:])
        if abs(max1 - max2) / max1 < 0.015:
            patterns.append("📈 פסגה כפולה (Double Top)")

    # זיהוי גאפים (Gaps) - בודק את היום האחרון מול שלשום
    if len(df) > 2:
        last_open = df['Open'].iloc[-1]
        prev_close = df['Close'].iloc[-2]
        gap_pct = (last_open - prev_close) / prev_close
        if gap_pct > 0.01: patterns.append(f"🚀 גאפ פריצה למעלה ({gap_pct:.1%})")
        elif gap_pct < -0.01: patterns.append(f"⚠️ גאפ ירידה למטה ({gap_pct:.1%})")
    
    # צלבים
    if df['SMA50'].iloc[-1] > df['SMA200'].iloc[-1] and df['SMA50'].iloc[-2] <= df['SMA200'].iloc[-2]:
        patterns.append("🌟 צלב זהב (Golden Cross)")
        
    return patterns

def analyze_master(symbol, spy_perf):
    try:
        data = yf.download(symbol, period="2y", progress=False)
        if data.empty or len(data) < 200: return None
        
        df = data.copy()
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
        close = df['Close'].dropna()
        df['SMA50'] = close.rolling(50).mean()
        df['SMA150'] = close.rolling(150).mean()
        df['SMA200'] = close.rolling(200).mean()
        
        last_p = float(close.iloc[-1])
        sup = float(df['Low'].tail(200).min())
        res = float(df['High'].tail(200).max())
        
        patterns = detect_patterns(df)
        score = 0
        if last_p > df['SMA50'].iloc[-1]: score += 3
        if last_p > df['SMA200'].iloc[-1]: score += 3
        if (last_p / float(close.iloc[-21])) - 1 > spy_perf: score += 4
        
        sl = max(sup * 0.98, last_p * 0.95)
        
        if score >= 6 or patterns:
            pattern_txt = "\n".join(patterns) if patterns else "אין תבנית מיוחדת"
            msg = (f"🎯 **{symbol} | Pro Score: {score}/10**\n"
                   f"📊 תבניות: {pattern_txt}\n"
                   f"💰 מחיר: `{last_p:.2f}`\n"
                   f"🛑 סטופ לוס: `{sl:.2f}`\n"
                   f"📏 התנגדות: `{res:.2f}` | ⚓ תמיכה: `{sup:.2f}`")
            return df, msg, sup, res
        return None
    except: return None

def scanner():
    groups = {
        "נאסד\"ק 100": ['AAPL', 'MSFT', 'AMZN', 'NVDA', 'GOOGL', 'META', 'TSLA', 'AVGO', 'COST', 'NFLX'],
        "ישראל - מדדים": ['LUMI.TA', 'POLI.TA', 'DSCT.TA', 'ICL.TA', 'NICE.TA', 'BEZQ.TA'],
        "סחורות": ['GC=F', 'CL=F', 'SI=F', 'NG=F', 'HG=F'], # זהב, נפט, כסף, גז, נחושת
        "קריפטו": ['BTC-USD', 'ETH-USD', 'SOL-USD', 'ADA-USD', 'XRP-USD'],
        "S&P 500": ['BRK-B', 'LLY', 'V', 'JPM', 'UNH', 'MA', 'WMT', 'PG']
    }
    
    while True:
        for name, tickers in groups.items():
            try:
                spy = yf.download('SPY', period="1y", progress=False)['Close']
                if isinstance(spy, pd.DataFrame): spy = spy.iloc[:, 0]
                spy_perf = (float(spy.iloc[-1]) / float(spy.iloc[-21])) - 1
                
                send_msg(f"⏳ **מתחיל סריקת סקטור: {name}**")
                for s in tickers:
                    res = analyze_master(s.replace('.', '-'), spy_perf)
                    if res: send_plot(s, res[0], res[1], res[2], res[3])
                    time.sleep(5)
                
                time.sleep(600) # המתנה של 10 דקות בין קבוצה לקבוצה
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
                    spy = yf.download('SPY', period="1y", progress=False)['Close']
                    if isinstance(spy, pd.DataFrame): spy = spy.iloc[:, 0]
                    spy_perf = (float(spy.iloc[-1]) / float(spy.iloc[-21])) - 1
                    res = analyze_master(t, spy_perf)
                    if res: send_plot(t, res[0], res[1], res[2], res[3])
        except: time.sleep(2)

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    Thread(target=scanner).start()
    listen()
