import yfinance as yf
import pandas as pd
import requests
import time
import io
import matplotlib.pyplot as plt
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta

# --- הגדרות ---
# ודא שהטוקן הזה מדויק ושלם (כולל ה-M בסוף)
TOKEN = "8456706482:AAFUhE3sdD7YZh4ESz1Mr4V15zYYLXgYtuM"
CHAT_ID = "605543691"

app = Flask('')
sent_alerts = {} # זיכרון התראות ושינויי מחיר

@app.route('/')
def home(): return "Strategic Market Scanner Active"

def send_msg(text):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.get(url, params={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=10)
    except: pass

def send_plot(symbol, name, df, caption, sup, res):
    try:
        plt.figure(figsize=(10, 6))
        prices = df['Close'].tail(120)
        plt.plot(df.index[-120:], prices, label='Price', color='black', linewidth=1.5)
        plt.plot(df.index[-120:], df['SMA50'].tail(120), label='50', color='blue', alpha=0.4)
        plt.plot(df.index[-120:], df['SMA150'].tail(120), label='150', color='orange', alpha=0.4)
        plt.plot(df.index[-120:], df['SMA200'].tail(120), label='200', color='red', linewidth=1.5)
        plt.axhline(y=sup, color='green', linestyle='--', alpha=0.5)
        plt.axhline(y=res, color='red', linestyle='--', alpha=0.5)
        plt.title(f"{name} ({symbol})")
        plt.legend()
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0); plt.close()
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", 
                      data={'chat_id': CHAT_ID, 'caption': caption, 'parse_mode': 'Markdown'}, 
                      files={'photo': buf}, timeout=25)
    except: pass

def get_full_lists():
    try:
        sp500 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]['Symbol'].tolist()
        nasdaq100 = pd.read_html('https://en.wikipedia.org/wiki/Nasdaq-100')[4]['Ticker'].tolist()
        # רשימת ישראל מורחבת
        israel = ['LUMI.TA', 'POLI.TA', 'DSCT.TA', 'FIBI.TA', 'AZRG.TA', 'BEZQ.TA', 'NICE.TA', 'ICL.TA', 'ESLT.TA', 'AFCON.TA', 'ORL.TA', 'HRL.TA', 'MGDL.TA', 'CLIS.TA']
        # סחורות וקריפטו
        others = ['GC=F', 'CL=F', 'SI=F', 'BTC-USD', 'ETH-USD', 'SOL-USD']
        return sorted(list(set(sp500 + nasdaq100 + israel + others)))
    except:
        return ['AAPL', 'MSFT', 'NVDA', 'LUMI.TA', 'BTC-USD', 'GC=F']

def get_clean_name(symbol, ticker_info):
    names = {
        'GC=F': 'זהב (Gold)',
        'CL=F': 'נפט (Crude Oil)',
        'SI=F': 'כסף (Silver)',
        'BTC-USD': 'ביטקוין (Bitcoin)',
        'ETH-USD': 'איתריום (Ethereum)'
    }
    if symbol in names: return names[symbol]
    return ticker_info.get('longName', symbol)

def analyze_strategy(symbol, spy_perf, my_price=None, is_auto=False):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="2y")
        if df.empty or len(df) < 200: return None
        
        last_p = float(df['Close'].iloc[-1])
        
        if is_auto and symbol in sent_alerts:
            prev = sent_alerts[symbol]
            if datetime.now() < prev['time'] + timedelta(hours=12) and abs((last_p - prev['price'])/prev['price']) < 0.02:
                return None

        name = get_clean_name(symbol, ticker.info)
        df['SMA50'] = df['Close'].rolling(50).mean()
        df['SMA150'] = df['Close'].rolling(150).mean()
        df['SMA200'] = df['Close'].rolling(200).mean()
        
        sup = float(df['Low'].tail(252).min())
        res = float(df['High'].tail(252).max())
        
        score = 0
        if last_p > df['SMA50'].iloc[-1]: score += 3
        if last_p > df['SMA150'].iloc[-1]: score += 2
        if last_p > df['SMA200'].iloc[-1]: score += 2
        
        perf_1m = (last_p / float(df['Close'].iloc[-21])) - 1
        if perf_1m > spy_perf: score += 3

        if score >= 8: rec = "💎 **קנייה חזקה**"
        elif score <= 2: rec = "🔴 **מכירה/סיכון**"
        else: return None 
        
        sl = min(float(df['Low'].tail(20).min()) * 0.99, last_p * 0.95)
        
        consult = ""
        if my_price:
            profit = (last_p - my_price) / my_price
            consult = f"\n\n💬 **ייעוץ:** קנית ב-{my_price:.2f} ({profit:.1%}). "
            consult += "להחזיק" if profit > -0.05 else "שקול חיתוך הפסד"

        msg = (f"🎯 **{name} ({symbol}) | ציון: {score}/10**\n"
               f"📢 **המלצה:** {rec}\n"
               f"💰 מחיר: `{last_p:.2f}` | 🛑 סטופ: `{sl:.2f}`\n"
               f"📏 התנגדות: `{res:.2f}` | ⚓ תמיכה: `{sup:.2f}`{consult}")
        
        if is_auto: sent_alerts[symbol] = {'time': datetime.now(), 'price': last_p}
        return df, msg, sup, res, name
    except: return None

def scanner():
    time.sleep(10) # המתנה לעליית השרת
    send_msg("🚀 **המערכת עלתה לאוויר ומתחילה סריקה מלאה של כ-630 ניירות ערך.**")
    while True:
        all_tickers = get_full_lists()
        found_any = False
        try:
            spy = yf.download('SPY', period="1mo", progress=False)['Close'].squeeze()
            spy_perf = (float(spy.iloc[-1]) / float(spy.iloc[0])) - 1
        except: spy_perf = 0
        
        for s in all_tickers:
            is_israel = ".TA" in s
            if is_israel and datetime.now().weekday() > 4: continue
            
            res = analyze_strategy(s.replace('.', '-'), spy_perf, is_auto=True)
            if res:
                send_plot(s, res[4], res[0], res[1], res[2], res[3])
                found_any = True
                time.sleep(10)
            else:
                time.sleep(0.5)
        
        msg = "🔄 **סבב סריקה מלא הושלם.**"
        if not found_any: msg += "\nלא נמצאו הזדמנויות חדשות כרגע."
        send_msg(msg)
        time.sleep(60)

def listen():
    last_id = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={last_id+1}&timeout=30"
            r = requests.get(url, timeout=35).json()
            for u in r.get("result", []):
                last_id = u["update_id"]
                if "message" in u and "text" in u["message"]:
                    txt = u["message"]["text"].upper().strip()
                    try:
                        spy = yf.download('SPY', period="1mo", progress=False)['Close'].squeeze()
                        spy_perf = (float(spy.iloc[-1]) / float(spy.iloc[0])) - 1
                    except: spy_perf = 0
                    
                    if txt.startswith("BY "):
                        p = txt.split()
                        res = analyze_strategy(p[1], spy_perf, my_price=float(p[2]), is_auto=False)
                    else:
                        res = analyze_strategy(txt, spy_perf, is_auto=False)
                    
                    if res: send_plot(txt.split()[-1], res[4], res[0], res[1], res[2], res[3])
        except: time.sleep(5)

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    Thread(target=scanner).start()
    listen()
