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
def home(): return "Scanner Fixed - Ultimate Stability Mode"

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
        plt.title(f"{name}")
        plt.legend()
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0); plt.close()
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", data={'chat_id': CHAT_ID, 'caption': caption, 'parse_mode': 'Markdown'}, files={'photo': buf}, timeout=30)
    except: pass

def get_static_list():
    # רשימה יציבה שלא תלויה באתרים חיצוניים
    israel = ['LUMI.TA', 'POLI.TA', 'DSCT.TA', 'FIBI.TA', 'AZRG.TA', 'BEZQ.TA', 'NICE.TA', 'ICL.TA', 'ESLT.TA', 'AFCON.TA', 'ORL.TA', 'HRL.TA', 'TEVA.TA', 'DELEKG.TA', 'ENOG.TA', 'NWMD.TA', 'ALHE.TA', 'MTRX.TA', 'SPNS.TA', 'AMOT.TA', 'MELIS.TA']
    commodities = ['GC=F', 'CL=F', 'SI=F', '^TA35.TA', '^TA125.TA', 'BTC-USD', 'ETH-USD']
    usa_major = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NFLX', 'AMD', 'INTC', 'PYPL', 'DIS', 'BA', 'JPM', 'V', 'MA', 'COST', 'WMT', 'LLY', 'AVGO', 'CRM', 'ORCL', 'ADBE', 'NKE', 'PLTR', 'NBR']
    # כאן ניתן להוסיף עוד מאות מניות ידנית במידת הצורך
    return sorted(list(set(israel + commodities + usa_major)))

def get_clean_name(symbol):
    names = {'GC=F': 'זהב (Gold)', 'CL=F': 'נפט (Crude Oil)', 'SI=F': 'כסף (Silver)', 'BTC-USD': 'ביטקוין', 'ETH-USD': 'איתריום', '^TA35.TA': 'מדד ת"א 35', '^TA125.TA': 'מדד ת"א 125'}
    if symbol in names: return names[symbol]
    try:
        info = yf.Ticker(symbol).info
        return f"{info.get('longName', symbol)} ({symbol})"
    except: return symbol

def analyze_strategy(symbol, spy_perf, my_price=None, is_auto=False):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="2y")
        if df.empty or len(df) < 200: return None
        
        last_p = float(df['Close'].iloc[-1])
        
        # עדכון רק אם המחיר זז ב-3% (מונע ספאם)
        if is_auto and symbol in sent_alerts:
            if abs((last_p - sent_alerts[symbol]) / sent_alerts[symbol]) < 0.03: return None

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
            personal += "המגמה תומכת - להחזיק." if score >= 7 else "זהירות - מגמה נחלשת."

        name = get_clean_name(symbol)
        msg = (f"🎯 **{name} | ציון: {score}/10**\n"
               f"📢 **מסקנה:** {rec}\n\n"
               f"📍 ממוצע 50: `{s50:.2f}` ({'✅' if last_p > s50 else '❌'})\n"
               f"📍 ממוצע 150: `{s150:.2f}` ({'✅' if last_p > s150 else '❌'})\n"
               f"📍 ממוצע 200: `{s200:.2f}` ({'✅' if last_p > s200 else '❌'})\n\n"
               f"💰 מחיר: `{last_p:.2f}` | 🛑 סטופ: `{min(df['Low'].tail(20).min()*0.99, last_p*0.95):.2f}`\n"
               f"📏 התנגדות: `{res:.2f}` | ⚓ תמיכה: `{sup:.2f}`{personal}")
        
        if is_auto: sent_alerts[symbol] = last_p
        return df, msg, sup, res, name
    except: return None

def scanner():
    while True:
        all_tickers = get_static_list()
        send_msg(f"🚀 **מתחיל סריקה על {len(all_tickers)} ניירות ערך.**")
        try:
            spy = yf.download('SPY', period="1mo", progress=False)['Close'].squeeze()
            spy_perf = (float(spy.iloc[-1]) / float(spy.iloc[0])) - 1
        except: spy_perf = 0
        
        for s in all_tickers:
            if ".TA" in s and datetime.now().weekday() in [4, 5]: continue
            res = analyze_strategy(s.replace('.', '-'), spy_perf, is_auto=True)
            if res:
                send_plot(s, res[4], res[0], res[1], res[2], res[3])
                time.sleep(10)
            time.sleep(1.2)
        
        send_msg(f"✅ סבב מלא הושלם.")
        time.sleep(1800)

def listen():
    last_id = 0
    while True:
        try:
            r = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={last_id+1}&timeout=30").json()
            for u in r.get("result", []):
                last_id = u["update_id"]
                if "message" in u and "text" in u["message"]:
                    txt = u["message"]["text"].upper().strip()
                    send_msg(f"⏳ מנתח עבורך את {txt}...") # אישור קבלה מיידי
                    
                    try:
                        spy = yf.download('SPY', period="1mo", progress=False)['Close'].squeeze()
                        spy_perf = (float(spy.iloc[-1]) / float(spy.iloc[0])) - 1
                    except: spy_perf = 0
                    
                    if "BY" in txt:
                        parts = txt.split()
                        res = analyze_strategy(parts[1], spy_perf, my_price=float(parts[2]), is_auto=False)
                    else:
                        res = analyze_strategy(txt, spy_perf, is_auto=False)
                    
                    if res: send_plot(txt, res[4], res[0], res[1], res[2], res[3])
                    else: send_msg(f"❌ לא מצאתי נתונים עבור {txt}. וודא שהסימבול נכון (למשל NVDA או LUMI.TA)")
        except: time.sleep(2)

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    Thread(target=scanner).start()
    listen()
