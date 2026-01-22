import yfinance as yf
import pandas as pd
import requests
import time
import io
import matplotlib.pyplot as plt
from flask import Flask
from threading import Thread
from datetime import datetime

# --- הגדרות ---
TOKEN = "8456706482:AAFUhE3sdD7YZh4ESz1Mr4V15zYYLXgYtuM"
CHAT_ID = "605543691"

app = Flask('')
@app.route('/')
def home(): return "AI Market Giant Scanner Active"

def send_msg(text):
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=10)
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
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", data={'chat_id': CHAT_ID, 'caption': caption, 'parse_mode': 'Markdown'}, files={'photo': buf}, timeout=25)
    except: pass

def get_full_lists():
    # שליחת רשימות מלאות
    try:
        sp500 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]['Symbol'].tolist()
        nasdaq100 = pd.read_html('https://en.wikipedia.org/wiki/Nasdaq-100')[4]['Ticker'].tolist()
        israel = [
            'LUMI.TA', 'POLI.TA', 'DSCT.TA', 'FIBI.TA', 'AZRG.TA', 'BEZQ.TA', 'NICE.TA', 'ICL.TA', 
            'ESLT.TA', 'ORL.TA', 'HRL.TA', 'MGDL.TA', 'CLIS.TA', 'PSTR.TA', 'TASE.TA', 'DEDO.TA'
        ]
        commodities = ['GC=F', 'CL=F', 'SI=F', 'NG=F', 'HG=F', 'ZC=F']
        crypto = ['BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'XRP-USD']
        return list(set(sp500 + nasdaq100 + israel + commodities + crypto))
    except:
        return ['AAPL', 'MSFT', 'NVDA', 'LUMI.TA', 'BTC-USD', 'GC=F']

def analyze_strategy(symbol, spy_perf, my_price=None):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="2y")
        if df.empty or len(df) < 200: return None
        
        name = ticker.info.get('longName', symbol)
        last_p = float(df['Close'].iloc[-1])
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

        # המלצה חכמה
        if score >= 8: rec = "💎 **קנייה חזקה**"
        elif score <= 3: rec = "🔴 **מכירה/סיכון**"
        else: return None # לא שולח סתם מניות "פרווה" בסריקה אוטומטית
        
        sl = min(float(df['Low'].tail(20).min()) * 0.99, last_p * 0.95)
        
        consult_msg = ""
        if my_price:
            profit = (last_p - my_price) / my_price
            consult_msg = f"\n\n💬 **ייעוץ:** קנית ב-{my_price:.2f} ({profit:.1%}). "
            consult_msg += "להחזיק" if profit > -0.05 else "שקול חיתוך הפסד"

        msg = (f"🎯 **{name} ({symbol}) | ציון: {score}/10**\n"
               f"📢 **המלצה:** {rec}\n"
               f"💰 מחיר: `{last_p:.2f}` | 🛑 סטופ: `{sl:.2f}`\n"
               f"📏 התנגדות: `{res:.2f}` | ⚓ תמיכה: `{sup:.2f}`"
               f"{consult_msg}")
        
        return df, msg, sup, res, name
    except: return None

def scanner():
    while True:
        all_tickers = get_full_lists()
        spy = yf.download('SPY', period="1mo", progress=False)['Close'].squeeze()
        spy_perf = (float(spy.iloc[-1]) / float(spy.iloc[0])) - 1
        
        # חלוקה לקבוצות של 10 כדי לא להיחסם
        for i in range(0, len(all_tickers), 10):
            batch = all_tickers[i:i+10]
            current_day = datetime.now().weekday() # 0=Mon, 4=Fri
            
            for s in batch:
                # סינון ימי מסחר ישראל (שני-שישי)
                if ".TA" in s and current_day > 4: continue 
                
                res = analyze_strategy(s.replace('.', '-'), spy_perf)
                if res: send_plot(s, res[4], res[0], res[1], res[2], res[3])
                time.sleep(5)
            
            time.sleep(300) # המתנה של 5 דקות בין עשיריות

def listen():
    last_id = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={last_id+1}&timeout=30"
            res = requests.get(url, timeout=35).json()
            for u in res.get("result", []):
                last_id = u["update_id"]
                if "message" in u and "text" in u["message"]:
                    txt = u["message"]["text"].upper().strip()
                    spy = yf.download('SPY', period="1mo", progress=False)['Close'].squeeze()
                    spy_perf = (float(spy.iloc[-1]) / float(spy.iloc[0])) - 1
                    if txt.startswith("BY "):
                        parts = txt.split()
                        res = analyze_strategy(parts[1], spy_perf, my_price=float(parts[2]))
                    else:
                        res = analyze_strategy(txt, spy_perf)
                    if res: send_plot(txt.split()[-1], res[4], res[0], res[1], res[2], res[3])
        except: time.sleep(2)

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    Thread(target=scanner).start()
    listen()
