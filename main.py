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
def home(): return "Professional Full Scanner Online"

def send_msg(text):
    requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"})

def send_plot(symbol, df, caption):
    try:
        plt.figure(figsize=(10, 6))
        plt.plot(df.index[-100:], df['Close'].tail(100), label='Price', color='blue', linewidth=2)
        plt.plot(df.index[-100:], df['SMA50'].tail(100), label='SMA50', color='orange', linestyle='--')
        plt.plot(df.index[-100:], df['SMA150'].tail(100), label='SMA150', color='green', linewidth=1.5)
        plt.plot(df.index[-100:], df['SMA200'].tail(100), label='SMA200', color='red', linewidth=1.5)
        plt.title(f"Technical Analysis: {symbol}")
        plt.legend()
        plt.grid(True, alpha=0.3)
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", data={'chat_id': CHAT_ID, 'caption': caption, 'parse_mode': 'Markdown'}, files={'photo': buf})
    except: pass

def get_full_list():
    try:
        sp500 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]['Symbol'].tolist()
        nas100 = pd.read_html('https://en.wikipedia.org/wiki/Nasdaq-100')[4]['Ticker'].tolist()
        others = ['LUMI.TA', 'POLI.TA', 'BEZQ.TA', 'NICE.TA', 'ICL.TA', 'BTC-USD', 'ETH-USD', 'GC=F', 'CL=F', 'SI=F']
        return list(set(sp500 + nas100 + others))
    except:
        return ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'TSLA', 'META', 'LUMI.TA', 'BTC-USD', 'GC=F']

def analyze_engine(symbol, spy_perf, min_to_send=5):
    try:
        df = yf.download(symbol, period="2y", interval="1d", progress=False)
        if df.empty or len(df) < 200: return None, 0, ""
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        close = df['Close'].squeeze()
        high = df['High'].squeeze()
        df['SMA50'] = close.rolling(50).mean()
        df['SMA150'] = close.rolling(150).mean()
        df['SMA200'] = close.rolling(200).mean()
        df['Vol_Avg'] = df['Volume'].rolling(20).mean()
        
        last = float(close.iloc[-1])
        score = 0
        reasons = []
        
        if last > df['SMA150'].iloc[-1]: score += 2; reasons.append("📈 מעל מגמת 150")
        if last > df['SMA200'].iloc[-1]: score += 2; reasons.append("🔋 מעל ממוצע 200")
        if df['SMA50'].iloc[-1] > df['SMA200'].iloc[-1]: score += 2; reasons.append("🌟 צלב זהב (50/200)")
        if last >= float(high.max()) * 0.95: score += 2; reasons.append("☕ מבנה כוס וידית")
        if (last / float(close.iloc[-21])) - 1 > spy_perf: score += 2; reasons.append("💪 חזקה מהשוק (RS)")
        
        if score >= min_to_send:
            rec = "💎 קנייה חזקה" if score >= 8 else "⚖️ החזקה / מעקב"
            if last < df['SMA150'].iloc[-1]: rec = "⚠️ למכירה / המתנה"
            
            support = float(close.tail(20).min())
            resistance = float(high.tail(20).max())
            
            msg = (f"🔍 **איתות: {symbol} | ציון: {score}/10**\n"
                   f"📢 המלצה: *{rec}*\n"
                   f"💰 מחיר: `{last:.2f}` | סטופ: `{last*0.96:.2f}`\n"
                   f"🧱 התנגדות: `{resistance:.2f}` | ⚓ תמיכה: `{support:.2f}`\n"
                   f"------------------\n" + "\n".join(reasons))
            return df, score, msg
        return None, 0, ""
    except: return None, 0, ""

def scanner_loop():
    while True:
        try:
            send_msg("🛰️ **סורק AI התחיל סריקה מלאה (S&P500, נאסד\"ק, ישראל)...**")
            spy = yf.download('SPY', period="1y", progress=False)['Close'].squeeze()
            spy_perf = (float(spy.iloc[-1]) / float(spy.iloc[-21])) - 1
            
            tickers = get_full_list()
            found = 0
            for s in tickers:
                s = s.replace('.', '-') if '-' not in s else s
                df, score, msg = analyze_engine(s, spy_perf, min_to_send=5)
                if df is not None:
                    send_plot(s, df, msg)
                    found += 1
                time.sleep(1.2) # מניעת חסימה
            
            send_msg(f"✅ סבב הסתיים. נמצאו {found} הזדמנויות.")
            time.sleep(3600)
        except: time.sleep(60)

def bot_listener():
    last_id = 0
    while True:
        try:
            res = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={last_id+1}&timeout=20").json()
            for u in res.get("result", []):
                last_id = u["update_id"]
                if "message" in u and "text" in u["message"]:
                    ticker = u["message"]["text"].upper().strip()
                    spy = yf.download('SPY', period="1y", progress=False)['Close'].squeeze()
                    spy_perf = (float(spy.iloc[-1]) / float(spy.iloc[-21])) - 1
                    df, score, msg = analyze_engine(ticker, spy_perf, min_to_send=0)
                    if df is not None: send_plot(ticker, df, msg)
                    else: send_msg(f"❌ לא נמצאו נתונים עבור {ticker}")
        except: time.sleep(2)

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    Thread(target=scanner_loop).start()
    bot_listener()
