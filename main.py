import yfinance as yf
import pandas as pd
import requests
import time
from flask import Flask
from threading import Thread

# --- הגדרות ---
TOKEN = "8456706482:AAFUhE3sdD7YZh4ESz1Mr4V15zYYLXgYtuM"
CHAT_ID = "605543691"

app = Flask('')
@app.route('/')
def home(): return "Professional Scanner Fixed & Active"

def send_msg(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.get(url, params={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"})

def get_sp500():
    try:
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        return pd.read_html(url)[0]['Symbol'].tolist()
    except: return ['AAPL', 'NVDA', 'TSLA', 'MSFT', 'META', 'GOOGL', 'AMZN']

WATCHLIST = ['LUMI.TA', 'POLI.TA', 'BEZQ.TA', 'NICE.TA', 'ICL.TA', 'BTC-USD', 'ETH-USD', 'GC=F', 'CL=F']

def analyze_stock(symbol, spy_perf):
    try:
        df = yf.download(symbol, period="2y", interval="1d", progress=False)
        if df.empty or len(df) < 200: return None
        
        # תיקון השגיאה - הפיכת הנתונים לסדרות פשוטות
        close = df['Close'].squeeze()
        high = df['High'].squeeze()
        volume = df['Volume'].squeeze()
        
        sma50 = close.rolling(window=50).mean()
        sma150 = close.rolling(window=150).mean()
        sma200 = close.rolling(window=200).mean()
        vol_avg = volume.rolling(window=20).mean()
        
        last_price = float(close.iloc[-1])
        prev_price = float(close.iloc[-2])
        last_sma50 = float(sma50.iloc[-1])
        prev_sma50 = float(sma50.iloc[-2])
        last_sma150 = float(sma150.iloc[-1])
        last_sma200 = float(sma200.iloc[-1])
        prev_sma200 = float(sma200.iloc[-2])
        
        score = 0
        reasons = []

        # 1. צלב זהב (3 נק')
        if prev_sma50 <= prev_sma200 and last_sma50 > last_sma200:
            score += 3
            reasons.append("🌟 צלב זהב (50/200)")
        
        # 2. מעל 150 (2 נק')
        if last_price > last_sma150:
            score += 2
            reasons.append("📈 מעל ממוצע 150")

        # 3. כוס וידית/שיא (2 נק')
        if last_price >= float(high.max()) * 0.95:
            score += 2
            reasons.append("☕ מבנה כוס וידית / שיא")

        # 4. ווליום (1.5 נק')
        if float(volume.iloc[-1]) > float(vol_avg.iloc[-1]) * 1.5:
            score += 1.5
            reasons.append("🔥 ווליום חריג")

        # 5. חוזק יחסי (1.5 נק')
        perf = (last_price / float(close.iloc[-21])) - 1
        if perf > spy_perf:
            score += 1.5
            reasons.append("💪 חזקה מהשוק (RS)")

        if score >= 6: # רף 6 כדי שנתחיל לראות תוצאות איכותיות
            support = float(close.tail(20).min())
            resis = float(high.tail(20).max())
            msg = (f"🚀 **איתות בציון {score}/10: {symbol}**\n"
                   f"💰 מחיר: `{last_price:.2f}`\n"
                   f"------------------\n" + "\n".join(reasons) + "\n"
                   f"------------------\n"
                   f"🧱 התנגדות: `{resis:.2f}` | ⚓ תמיכה: `{support:.2f}`\n"
                   f"🛡️ סטופ לוס (4%): `{last_price*0.96:.2f}`")
            return msg
        return None
    except: return None

def scanner():
    while True:
        try:
            send_msg("🛰️ **סורק AI מתוקן מתחיל סבב עומק...**")
            spy = yf.download('SPY', period="1y", progress=False)['Close'].squeeze()
            spy_perf = (float(spy.iloc[-1]) / float(spy.iloc[-21])) - 1
            
            full_list = get_sp500() + WATCHLIST
            found = 0
            for s in full_list:
                s = s.replace('.', '-') if '-' not in s else s
                res = analyze_stock(s, spy_perf)
                if res:
                    send_msg(res)
                    found += 1
                time.sleep(0.7)
            
            send_msg(f"✅ סבב הסתיים. נמצאו {found} איתותים.")
            time.sleep(3600)
        except: time.sleep(60)

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    scanner()
