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
def home(): return "AI Strategic Advisor - Stable Version"

def send_msg(text):
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=10)
    except: pass

def send_plot(symbol, df, caption, sup, res):
    try:
        plt.figure(figsize=(12, 7))
        prices = df['Close'].tail(150)
        plt.plot(df.index[-150:], prices, label='Price', color='black', linewidth=1.8)
        plt.plot(df.index[-150:], df['SMA50'].tail(150), label='SMA 50 (Trend)', color='blue', alpha=0.5)
        plt.plot(df.index[-150:], df['SMA200'].tail(150), label='SMA 200 (Major)', color='red', linewidth=2)
        
        plt.axhline(y=sup, color='green', linestyle='--', alpha=0.6, label='Major Support')
        plt.axhline(y=res, color='red', linestyle='--', alpha=0.6, label='Major Resistance')

        plt.title(f"Strategic Analysis: {symbol}")
        plt.legend(loc='upper left')
        plt.grid(True, alpha=0.15)
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=110)
        buf.seek(0); plt.close()
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", data={'chat_id': CHAT_ID, 'caption': caption, 'parse_mode': 'Markdown'}, files={'photo': buf}, timeout=25)
    except: pass

def analyze_strategy(symbol, spy_perf, my_price=None):
    try:
        data = yf.download(symbol, period="2y", progress=False)
        if data.empty or len(data) < 250: return None
        
        df = data.copy()
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        close = df['Close'].dropna()
        last_p = float(close.iloc[-1])
        df['SMA50'] = close.rolling(50).mean()
        df['SMA200'] = close.rolling(200).mean()
        
        # זיהוי רמות שנתיות (תמיכה והתנגדות משמעותיות)
        sup_year = float(df['Low'].tail(252).min())
        res_year = float(df['High'].tail(252).max())
        
        score = 0
        details = []
        
        # 1. מגמה מול ממוצעים
        if last_p > df['SMA50'].iloc[-1]: score += 3; details.append("🔼 מגמה חיובית בטווח הקצר")
        if last_p > df['SMA200'].iloc[-1]: score += 3; details.append("🚀 מגמה ראשית חיובית")
        
        # 2. חוזק מול השוק (SPY)
        perf_1m = (last_p / float(close.iloc[-21])) - 1
        if perf_1m > spy_perf: score += 4; details.append("💪 חזקה מהשוק (RS)")

        # 3. ניתוח מומנטום כניסה/יציאה
        dist_from_low = (last_p - sup_year) / sup_year
        if score >= 8:
            if last_p > res_year * 0.98: rec = "⚖️ **החזק: קרובה לשיא שנתי, המתן לפריצה לפני כניסה חדשה**"
            else: rec = "💎 **קנייה: מומנטום חיובי ופוטנציאל המשך**"
        elif score <= 4:
            rec = "🔴 **מכירה/התרחקות: הנייר נחלש משמעותית**"
        else:
            rec = "⏳ **מעקב: מחפשת כיוון ברור**"

        # 4. סטופ לוס חכם (תמיכה טכנית אחרונה, מינימום 5%)
        tech_sup = float(df['Low'].tail(20).min())
        sl = min(tech_sup * 0.99, last_p * 0.95)

        # 5. ניתוח אישי (התייעצות)
        consult_msg = ""
        if my_price:
            profit = (last_p - my_price) / my_price
            status = "ברווח" if profit > 0 else "בהפסד"
            consult_msg = (f"\n\n💬 **ייעוץ אישי:**\n"
                           f"קנית ב-{my_price:.2f}, אתה כרגע {status} של `{profit:.1%}`.\n")
            if profit < -0.06: consult_msg += "🛑 המלצה: המניה מתחת למחיר הקנייה. אם יורד מהסטופ - חתוך."
            elif profit > 0.12: consult_msg += "💰 המלצה: רווח יפה! כדאי להעלות סטופ למחיר כניסה או לממש חלק."
            else: consult_msg += "🧘 המלצה: אין שינוי בתוכנית, להמשיך להחזיק."

        msg = (f"🎯 **{symbol} | Pro Score: {score}/10**\n\n"
               f"📢 **המלצה:** {rec}\n"
               f"💰 מחיר: `{last_p:.2f}`\n"
               f"🛑 סטופ-לוס אסטרטגי: `{sl:.2f}`\n\n"
               f"🔍 **מבט טכני (שנה אחורה):**\n"
               f"📏 התנגדות שנתיים: `{res_year:.2f}`\n"
               f"⚓ תמיכה שנתיים: `{sup_year:.2f}`\n"
               f"{' '.join(details)}"
               f"{consult_msg}")
        
        return df, msg, sup_year, res_year
    except: return None

def scanner():
    # חלוקה לסבבים לאורך השעה
    groups = {
        "Nasdaq 100": ['AAPL', 'MSFT', 'AMZN', 'NVDA', 'GOOGL', 'META', 'TSLA', 'NFLX'],
        "Israel Real Estate & Banks": ['LUMI.TA', 'POLI.TA', 'DSCT.TA', 'AZRG.TA', 'BEZQ.TA'],
        "Commodities": ['GC=F', 'CL=F', 'SI=F', 'NG=F'],
        "Crypto": ['BTC-USD', 'ETH-USD', 'SOL-USD']
    }
    while True:
        for name, tickers in groups.items():
            try:
                spy = yf.download('SPY', period="1y", progress=False)['Close'].squeeze()
                if isinstance(spy, pd.DataFrame): spy = spy.iloc[:, 0]
                spy_perf = (float(spy.iloc[-1]) / float(spy.iloc[-21])) - 1
                
                send_msg(f"🕒 **סריקה תקופתית: {name}**")
                for s in tickers:
                    res = analyze_strategy(s.replace('.', '-'), spy_perf)
                    if res: send_plot(s, res[0], res[1], res[2], res[3])
                    time.sleep(5)
                time.sleep(600) # מנוחה של 10 דקות
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
                    txt = u["message"]["text"].upper().strip()
                    spy = yf.download('SPY', period="1y", progress=False)['Close'].squeeze()
                    if isinstance(spy, pd.DataFrame): spy = spy.iloc[:, 0]
                    spy_perf = (float(spy.iloc[-1]) / float(spy.iloc[-21])) - 1
                    
                    if txt.startswith("BY "): # פורמט: BY NVDA 125.5
                        parts = txt.split()
                        if len(parts) == 3:
                            sym, price = parts[1], float(parts[2])
                            res = analyze_strategy(sym, spy_perf, my_price=price)
                            if res: send_plot(sym, res[0], res[1], res[2], res[3])
                    else:
                        res = analyze_strategy(txt, spy_perf)
                        if res: send_plot(txt, res[0], res[1], res[2], res[3])
        except: time.sleep(2)

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    Thread(target=scanner).start()
    listen()
