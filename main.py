import yfinance as yf
import pandas as pd
import requests
import time
import io
import matplotlib.pyplot as plt
import mplfinance as mpf
from flask import Flask
from threading import Thread

# --- הגדרות ---
TOKEN = "8456706482:AAFUhE3sdD7YZh4ESz1Mr4V15zYYLXgYtuM"
CHAT_ID = "605543691"

app = Flask('')
@app.route('/')
def home(): return "Scanner with Graphics & Logic Active"

def send_msg(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.get(url, params={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"})

def send_photo(photo_buf, caption):
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    requests.post(url, data={'chat_id': CHAT_ID, 'caption': caption, 'parse_mode': 'Markdown'}, files={'photo': photo_buf})

def get_sp500():
    try:
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        return pd.read_html(url)[0]['Symbol'].tolist()
    except: return ['AAPL', 'NVDA', 'TSLA', 'MSFT', 'META']

WATCHLIST = ['LUMI.TA', 'POLI.TA', 'BEZQ.TA', 'NICE.TA', 'ICL.TA', 'BTC-USD', 'ETH-USD', 'GC=F', 'CL=F']

def analyze_and_plot(symbol, spy_perf, min_score=5):
    try:
        df = yf.download(symbol, period="1y", interval="1d", progress=False)
        if df.empty or len(df) < 150: return None
        
        close = df['Close'].squeeze()
        high = df['High'].squeeze()
        
        df['SMA50'] = close.rolling(window=50).mean()
        df['SMA150'] = close.rolling(window=150).mean()
        df['SMA200'] = close.rolling(window=200).mean()
        
        last_price = float(close.iloc[-1])
        last_sma50 = float(df['SMA50'].iloc[-1])
        last_sma150 = float(df['SMA150'].iloc[-1])
        last_sma200 = float(df['SMA200'].iloc[-1])
        
        score = 0
        reasons = []

        # לוגיקת ניקוד
        if last_price > last_sma150: score += 2; reasons.append("✅ מעל מגמת 150")
        if last_price > last_sma200: score += 1; reasons.append("✅ מעל ממוצע 200")
        if last_sma50 > last_sma200: score += 2; reasons.append("🌟 מבנה צלב זהב")
        if last_price >= float(high.max()) * 0.96: score += 2; reasons.append("☕ מבנה כוס וידית")
        
        perf = (last_price / float(close.iloc[-21])) - 1
        if perf > spy_perf: score += 2; reasons.append("💪 חוזק יחסי חיובי")

        if score >= min_score:
            # המלצה
            recommendation = "💎 קנייה" if score >= 7 else "⚖️ החזקה / מעקב"
            if last_price < last_sma150: recommendation = "⚠️ המתנה/מכירה"

            # יצירת גרף
            buf = io.BytesIO()
            ap = mpf.make_addplot(df[['SMA50', 'SMA150', 'SMA200']].tail(100))
            mpf.plot(df.tail(100), type='candle', style='charles', addplot=ap, savefig=dict(fname=buf, format='png'), title=f"{symbol} Analysis")
            buf.seek(0)

            msg = (f"📊 **{symbol} | ציון: {score}/10**\n"
                   f"📢 המלצה: *{recommendation}*\n"
                   f"💰 מחיר שוק: `{last_price:.2f}`\n"
                   f"🛡️ סטופ לוס: `{last_price*0.96:.2f}`\n"
                   f"------------------\n" + "\n".join(reasons))
            
            send_photo(buf, msg)
            return True
        return False
    except: return False

def scanner_engine():
    while True:
        try:
            send_msg("🛰️ **סורק אוטומטי התחיל סבב (כולל גרפים והמלצות)...**")
            spy = yf.download('SPY', period="1y", progress=False)['Close'].squeeze()
            spy_perf = (float(spy.iloc[-1]) / float(spy.iloc[-21])) - 1
            
            full_list = get_sp500() + WATCHLIST
            found = 0
            for s in full_list:
                s = s.replace('.', '-') if '-' not in s else s
                if analyze_and_plot(s, spy_perf, min_score=5):
                    found += 1
                time.sleep(1) # גרפים דורשים יותר זמן עיבוד
            
            send_msg(f"✅ סבב הסתיים. נמצאו {found} איתותים.")
            time.sleep(3600)
        except: time.sleep(60)

def listen_to_user():
    last_id = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={last_id+1}&timeout=30"
            res = requests.get(url).json()
            if "result" in res:
                for u in res["result"]:
                    last_id = u["update_id"]
                    if "message" in u and "text" in u["message"]:
                        ticker = u["message"]["text"].upper().strip()
                        spy = yf.download('SPY', period="1y", progress=False)['Close'].squeeze()
                        spy_perf = (float(spy.iloc[-1]) / float(spy.iloc[-21])) - 1
                        analyze_and_plot(ticker, spy_perf, min_score=0) # מציג הכל לבקשת משתמש
        except: time.sleep(5)

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    Thread(target=scanner_engine).start()
    listen_to_user()
