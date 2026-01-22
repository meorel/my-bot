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
TOKEN = "8456706482:AAFUhE3sdD7YZh4ESz1Mr4V15zYYLXgYtuM"
CHAT_ID = "605543691"

app = Flask('')
sent_alerts = {} 

@app.route('/')
def home(): return "Systematic Scanner - Transparency Mode"

def send_msg(text):
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=15)
    except: pass

def send_plot(symbol, name, df, caption, sup, res):
    try:
        plt.figure(figsize=(10, 6))
        prices = df['Close'].tail(120)
        plt.plot(df.index[-120:], prices, label='Price', color='black', linewidth=1.5)
        plt.plot(df.index[-120:], df['SMA50'].tail(120), label='SMA 50', color='blue', alpha=0.5)
        plt.plot(df.index[-120:], df['SMA150'].tail(120), label='SMA 150', color='orange', alpha=0.5)
        plt.plot(df.index[-120:], df['SMA200'].tail(120), label='SMA 200', color='red', linewidth=1.5)
        plt.axhline(y=sup, color='green', linestyle='--', alpha=0.6)
        plt.axhline(y=res, color='red', linestyle='--', alpha=0.6)
        plt.title(f"{name} ({symbol})")
        plt.legend()
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0); plt.close()
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", data={'chat_id': CHAT_ID, 'caption': caption, 'parse_mode': 'Markdown'}, files={'photo': buf}, timeout=30)
    except: pass

def get_full_lists():
    try:
        sp500 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]['Symbol'].tolist()
        nasdaq100 = pd.read_html('https://en.wikipedia.org/wiki/Nasdaq-100')[4]['Ticker'].tolist()
        israel_core = ['LUMI.TA', 'POLI.TA', 'DSCT.TA', 'FIBI.TA', 'AZRG.TA', 'BEZQ.TA', 'NICE.TA', 'ICL.TA', 'ESLT.TA', 'AFCON.TA', 'ORL.TA', 'HRL.TA', 'TEVA.TA', 'DELEKG.TA', 'ENOG.TA', 'NWMD.TA', 'ALHE.TA', 'MTRX.TA', 'SPNS.TA', 'AMOT.TA', 'MELIS.TA']
        others = ['GC=F', 'CL=F', 'SI=F', '^TA35.TA', '^TA125.TA', 'BTC-USD', 'ETH-USD']
        return sorted(list(set(sp500 + nasdaq100 + israel_core + others)))
    except:
        return ['AAPL', 'MSFT', 'NVDA', 'LUMI.TA', 'BTC-USD', 'GC=F']

def get_clean_name(symbol, ticker_info):
    names = {'GC=F': 'זהב (Gold)', 'CL=F': 'נפט (Crude Oil)', 'SI=F': 'כסף (Silver)', 'BTC-USD': 'ביטקוין', 'ETH-USD': 'איתריום', '^TA35.TA': 'מדד ת"א 35', '^TA125.TA': 'מדד ת"א 125'}
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
            if datetime.now() < prev['time'] + timedelta(hours=8) and abs((last_p - prev['price'])/prev['price']) < 0.02:
                return None

        df['SMA50'] = df['Close'].rolling(50).mean()
        df['SMA150'] = df['Close'].rolling(150).mean()
        df['SMA200'] = df['Close'].rolling(200).mean()
        
        s50, s150, s200 = df['SMA50'].iloc[-1], df['SMA150'].iloc[-1], df['SMA200'].iloc[-1]
        sup, res = float(df['Low'].tail(252).min()), float(df['High'].tail(252).max())
        
        score = 0
        if last_p > s50: score += 3
        if last_p > s150: score += 2
        if last_p > s200: score += 2
        if (last_p / float(df['Close'].iloc[-21])) - 1 > spy_perf: score += 3

        if is_auto and not (score >= 8 or score <= 2): return None 
        
        rec = "💎 **קנייה חזקה**" if score >= 8 else "🔴 **מכירה/סיכון**" if score <= 2 else "⚖️ **נייטרלי**"
        
        personal = ""
        if my_price:
            profit = (last_p - my_price) / my_price
            personal = f"\n\n💬 **ייעוץ אישי:** קנית ב-{my_price:.2f} ({profit:.1%}). "
            personal += "המגמה תומכת - להחזיק." if score >= 7 else "זהירות - המגמה נחלשת, שקול יציאה."

        name = get_clean_name(symbol, ticker.info)
        msg = (f"🎯 **{name} ({symbol}) | ציון: {score}/10**\n"
               f"📢 **מסקנה:** {rec}\n\n"
               f"📍 ממוצע 50: `{s50:.2f}` ({'✅' if last_p > s50 else '❌'})\n"
               f"📍 ממוצע 150: `{s150:.2f}` ({'✅' if last_p > s150 else '❌'})\n"
               f"📍 ממוצע 200: `{s200:.2f}` ({'✅' if last_p > s200 else '❌'})\n\n"
               f"💰 מחיר: `{last_p:.2f}` | 🛑 סטופ: `{min(df['Low'].tail(20).min()*0.99, last_p*0.95):.2f}`\n"
               f"📏 התנגדות: `{res:.2f}` | ⚓ תמיכה: `{sup:.2f}`{personal}")
        
        if is_auto: sent_alerts[symbol] = {'time': datetime.now(), 'price': last_p}
        return df, msg, sup, res, name
    except: return None

def scanner():
    time.sleep(10)
    while True:
        all_tickers = get_full_lists()
        total = len(all_tickers)
        send_msg(f"🚀 **מתחיל סבב סריקה יסודי על {total} ניירות ערך.**")
        found_count = 0
        
        try:
            spy = yf.download('SPY', period="1mo", progress=False)['Close'].squeeze()
            spy_perf = (float(spy.iloc[-1]) / float(spy.iloc[0])) - 1
        except: spy_perf = 0
        
        for index, s in enumerate(all_tickers):
            if ".TA" in s and datetime.now().weekday() in [4, 5]: continue
            
            # דיווח התקדמות כל 100 מניות
            if index > 0 and index % 100 == 0:
                send_msg(f"⏳ בתהליך... נסרקו {index} מתוך {total} ניירות.")

            res = analyze_strategy(s.replace('.', '-'), spy_perf, is_auto=True)
            if res:
                send_plot(s, res[4], res[0], res[1], res[2], res[3])
                found_count += 1
                time.sleep(8)
            time.sleep(1.2) 
        
        send_msg(f"✅ **סבב מלא הושלם!**\nנסרקו {total} ניירות ערך.\nנמצאו {found_count} איתותים רלוונטיים.")
        time.sleep(600)

def listen():
    last_id = 0
    while True:
        try:
            r = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={last_id+1}&timeout=30").json()
            for u in r.get("result", []):
                last_id = u["update_id"]
                if "message" in u and "text" in u["message"]:
                    txt = u["message"]["text"].upper().strip()
                    try:
                        spy = yf.download('SPY', period="1mo", progress=False)['Close'].squeeze()
                        spy_perf = (float(spy.iloc[-1]) / float(spy.iloc[0])) - 1
                    except: spy_perf = 0
                    
                    if "BY" in txt:
                        parts = txt.split()
                        sym = parts[parts.index("BY")+1]
                        price = float(parts[parts.index("BY")+2])
                        res = analyze_strategy(sym, spy_perf, my_price=price, is_auto=False)
                    else:
                        res = analyze_strategy(txt, spy_perf, is_auto=False)
                    
                    if res: send_plot(txt.split()[-1], res[4], res[0], res[1], res[2], res[3])
        except: time.sleep(5)

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    Thread(target=scanner).start()
    listen()
