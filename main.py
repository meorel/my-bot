import os
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import mplfinance as mpf
import io
import requests
import time
from flask import Flask
from threading import Thread

# שרת לשמירה על הבוט חי ב-Render
app = Flask('')
@app.route('/')
def home(): return "Trading Bot 24/7 is Active"

def run_web():
    app.run(host='0.0.0.0', port=8080)

TOKEN = "8456706482:AAFUhE3sdD7YZh4ESz1Mr4V15zYYLXgYtuM"
CHAT_ID = "605543691"

def send_msg(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.get(url, params={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"})

def get_comprehensive_analysis(symbol):
    try:
        # 1. משיכת נתונים (מניה + שוק)
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="1y")
        spy = yf.Ticker("SPY").history(period="1y")
        
        if df.empty or len(df) < 150:
            return f"❌ לא נמצאו מספיק נתונים עבור {symbol}. נסה סימול מוכר יותר."

        # 2. חישובים טכניים
        df['SMA50'] = df['Close'].rolling(window=50).mean()
        df['SMA150'] = df['Close'].rolling(window=150).mean()
        df['Vol_Avg'] = df['Volume'].rolling(window=20).mean()
        
        last_price = df['Close'].iloc[-1]
        sma50 = df['SMA50'].iloc[-1]
        sma150 = df['SMA150'].iloc[-1]
        
        # 3. זיהוי צלבים (זהב/מוות)
        prev_sma50 = df['SMA50'].iloc[-2]
        prev_sma150 = df['SMA150'].iloc[-2]
        if prev_sma50 <= prev_sma150 and sma50 > sma150: cross = "🌟 **צלב זהב (איתות קניה חזק!)**"
        elif prev_sma50 >= prev_sma150 and sma50 < sma150: cross = "💀 **צלב מוות (איתות מכירה!)**"
        else: cross = "⚖️ אין חצייה טרייה"

        # 4. כוס וידית ופריצות
        year_high = df['High'].max()
        if last_price >= year_high * 0.95: structure = "☕ מבנה 'כוס וידית' / פריצת שיא"
        elif last_price > sma50 and last_price > sma150: structure = "📈 מומנטום חיובי"
        else: structure = "📉 מבנה דל"

        # 5. חוזק יחסי מול ה-S&P 500
        stock_perf = (df['Close'].iloc[-1] / df['Close'].iloc[-21]) - 1
        spy_perf = (spy['Close'].iloc[-1] / spy['Close'].iloc[-21]) - 1
        rs = "💪 חזקה מהשוק" if stock_perf > spy_perf else "🔌 חלשה מהשוק"

        # 6. ניתוח מחזורים
        vol_ratio = df['Volume'].iloc[-1] / df['Vol_Avg'].iloc[-1]
        vol_desc = "🔥 מחזור חריג!" if vol_ratio > 1.5 else "📊 מחזור תקין"

        # 7. יצירת הגרף (60 ימים אחרונים)
        buf = io.BytesIO()
        ap = mpf.make_addplot(df[['SMA50', 'SMA150']].tail(60))
        mpf.plot(df.tail(60), type='candle', style='charles', addplot=ap,
                 title=f"\n{symbol} - Full Report", savefig=dict(fname=buf, format='png'))
        buf.seek(0)
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", data={'chat_id': CHAT_ID}, files={'photo': buf})

        # 8. הרכבת ההודעה
        status_150 = "✅ מעל ממוצע 150 (לונג)" if last_price > sma150 else "❌ מתחת לממוצע 150 (שורט)"
        stop_loss = last_price * 0.96

        msg = (f"💎 *דו''ח ניתוח מלא: {symbol}*\n"
               f"--------------------------\n"
               f"💰 מחיר נוכחי: `{last_price:.2f}$`\n"
               f"📊 מגמה ראשית: {status_150}\n"
               f"⚡ איתות: {cross}\n"
               f"🏗️ מבנה מחיר: {structure}\n"
               f"🌎 מול השוק: {rs}\n"
               f"📈 ווליום: {vol_desc}\n"
               f"🛡️ **סטופ לוס (4%): `{stop_loss:.2f}$`**\n"
               f"--------------------------\n"
               f"📏 SMA 50: `{sma50:.2f}`\n"
               f"📏 SMA 150: `{sma150:.2f}`")
        return msg
    except Exception as e: return f"⚠️ שגיאה בניתוח {symbol}: המערכת לא זיהתה את הסימול."

def main():
    last_id = 0
    send_msg("🚀 *הבוט המקצועי מוכן ב-Render!* \nשלח סימול (למשל: NVDA, GC=F, ETH-USD)")
    while True:
        try:
            updates = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={last_id+1}&timeout=20").json()
            if updates.get("result"):
                for u in updates["result"]:
                    last_id = u["update_id"]
                    if "message" in u and "text" in u["message"]:
                        ticker = u["message"]["text"].upper().strip()
                        send_msg(f"🧐 סורק את `{ticker}` לעומק...")
                        send_msg(get_comprehensive_analysis(ticker))
        except: time.sleep(5)

if __name__ == "__main__":
    Thread(target=run_web).start()
    main()