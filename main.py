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

# --- רשימות מניות "ברזל" (למניעת קריסות אינטרנט) ---
ISRAEL_STOCKS = ['LUMI.TA', 'POLI.TA', 'DSCT.TA', 'FIBI.TA', 'AZRG.TA', 'BEZQ.TA', 'NICE.TA', 'ICL.TA', 'ESLT.TA', 'TEVA.TA', 'DELEKG.TA', 'ENOG.TA', 'ORL.TA', 'AMOT.TA', 'MELIS.TA']
# כאן מוטמעים המדדים הגדולים (קיצור של ה-S&P והנאסד"ק לטובת יציבות מקסימלית)
USA_LIST = ['AAPL','MSFT','NVDA','GOOGL','AMZN','META','TSLA','BRK-B','LLY','AVGO','V','JPM','UNH','MA','COST','HD','PG','NFLX','JNJ','ABBV','BAC','CRM','ORCL','ADBE','AMD','CVX','WMT','TMO','CSCO','ABT','DHR','INTU','GE','QCOM','CAT','AXP','PFE','DIS','MS','PM','IBM','INTC','AMAT','UNP','LOW','TXN','SPGI','HON','RTX','GS','BKNG','SBUX','PLTR','UBER']
COMMODITIES = ['GC=F', 'CL=F', 'SI=F', '^TA35.TA', '^TA125.TA', 'BTC-USD', 'ETH-USD']

ALL_TICKERS = sorted(list(set(ISRAEL_STOCKS + USA_LIST + COMMODITIES)))

@app.route('/')
def home(): return "Scanner Pro - Ironclad Version"

def send_msg(text):
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=10)
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
        plt.legend(); buf = io.BytesIO(); plt.savefig(buf, format='png'); buf.seek(0); plt.close()
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", data={'chat_id': CHAT_ID, 'caption': caption, 'parse_mode': 'Markdown'}, files={'photo': buf}, timeout=20)
    except: pass

def analyze_strategy(symbol, spy_perf, my_price=None, is_auto=False):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="2y")
        if df.empty or len(df) < 200: return None
        
        last_p = float(df['Close'].iloc[-1])
        
        # סינון חזרות בסריקה אוטומטית (פעם ב-12 שעות)
        if is_auto and symbol in sent_alerts:
            if datetime.now() < sent_alerts[symbol] + timedelta(hours=12): return None

        df['SMA50'] = df['Close'].rolling(50).mean()
        df['SMA150'] = df['Close'].rolling(150).mean()
        df['SMA200'] = df['Close'].rolling(200).mean()
        
        s50, s150, s200 = df['SMA50'].iloc[-1], df['SMA150'].iloc[-1], df['SMA200'].iloc[-1]
        sup, res = float(df['Low'].tail(252).min()), float(df['High'].tail(252).max())
        
        # חישוב ציון קשוח (0-10)
        score = 0
        if last_p > s50: score += 3
        if last_p > s150: score += 2
        if last_p > s200: score += 2
        if (last_p / float(df['Close'].iloc[-21])) - 1 > spy_perf: score += 3

        # סינון איכות: רק הזדמנויות קצה בסריקה אוטומטית
        if is_auto and not (score >= 9 or score <= 1): return None 
        
        rec = "💎 **קנייה חזקה**" if score >= 9 else "🔴 **מכירה/סיכון**" if score <= 1 else "⚖️ **נייטרלי**"
        
        personal = ""
        if my_price:
            profit = (last_p - my_price) / my_price
            personal = f"\n\n💬 **ייעוץ אישי:** מחיר קנייה: {my_price:.2f} ({profit:+.1%})\n"
            personal += "✅ המגמה חזקה מאוד - מומלץ להחזיק." if score >= 8 else "⚠️ המגמה נחלשת - שקול מימוש/סטופ."

        # שמות בעברית לסחורות
        names_dict = {'GC=F': 'זהב (Gold)', 'CL=F': 'נפט (Oil)', 'SI=F': 'כסף (Silver)', '^TA35.TA': 'ת"א 35', '^TA125.TA': 'ת"א 125', 'BTC-USD': 'ביטקוין'}
        name = names_dict.get(symbol, ticker.info.get('longName', symbol))
        
        msg = (f"🎯 **{name} ({symbol}) | ציון: {score}/10**\n"
               f"📢 **מסקנה:** {rec}\n\n"
               f"📍 ממוצע 50: `{s50:.2f}` ({'✅' if last_p > s50 else '❌'})\n"
               f"📍 ממוצע 150: `{s150:.2f}` ({'✅' if last_p > s150 else '❌'})\n"
               f"📍 ממוצע 200: `{s200:.2f}` ({'✅' if last_p > s200 else '❌'})\n\n"
               f"💰 מחיר: `{last_p:.2f}` | 🛑 סטופ: `{last_p*0.95:.2f}`\n"
               f"📏 התנגדות: `{res:.2f}` | ⚓ תמיכה: `{sup:.2f}`{personal}")
        
        if is_auto: sent_alerts[symbol] = datetime.now()
        return df, msg, sup, res, name
    except: return None

def scanner():
    time.sleep(10)
    while True:
        send_msg(f"🚀 **מתחיל סבב סריקה יסודי על {len(ALL_TICKERS)} ניירות ערך.**")
        try:
            spy = yf.download('SPY', period="1mo", progress=False)['Close'].squeeze()
            spy_perf = (float(spy.iloc[-1]) / float(spy.iloc[0])) - 1
        except: spy_perf = 0
        
        found = 0
        for s in ALL_TICKERS:
            # דילוג על ישראל בסופ"ש
            if ".TA" in s and datetime.now().weekday() in [4, 5]: continue
            res = analyze_strategy(s, spy_perf, is_auto=True)
            if res:
                send_plot(s, res[4], res[0], res[1], res[2], res[3])
                found += 1
                time.sleep(5)
            time.sleep(0.5)
        
        send_msg(f"✅ **סבב הושלם.** נמצאו {found} איתותי איכות.")
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
                    send_msg(f"⏳ מנתח את {txt}...")
                    
                    try:
                        spy = yf.download('SPY', period="1mo", progress=False)['Close'].squeeze()
                        spy_perf = (float(spy.iloc[-1]) / float(spy.iloc[0])) - 1
                    except: spy_perf = 0
                    
                    if "BY" in txt: # פורמט: BY NVDA 120
                        parts = txt.split()
                        res = analyze_strategy(parts[1], spy_perf, my_price=float(parts[2]), is_auto=False)
                    else:
                        res = analyze_strategy(txt, spy_perf, is_auto=False)
                    
                    if res: send_plot(txt, res[4], res[0], res[1], res[2], res[3])
                    else: send_msg(f"❌ לא נמצאו נתונים עבור {txt}. נסה סימול מדויק.")
        except: time.sleep(2)

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    Thread(target=scanner).start()
    listen()
