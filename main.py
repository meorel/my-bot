import yfinance as yf
import pandas as pd
import requests
import time
import io
import matplotlib.pyplot as plt
from flask import Flask
from threading import Thread

# --- הגדרות מערכת ---
TOKEN = "8456706482:AAFUhE3sdD7YZh4ESz1Mr4V15zYYLXgYtuM"
CHAT_ID = "605543691"

app = Flask('')
@app.route('/')
def home(): return "Bot is Alive"

def send_msg(text):
    try:
        requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=10)
    except: pass

def send_plot(symbol, df, caption):
    try:
        plt.figure(figsize=(10, 5))
        plt.plot(df.index[-100:], df['Close'].tail(100), label='Price', color='blue')
        plt.title(f"Analysis: {symbol}")
        plt.grid(True, alpha=0.2)
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", data={'chat_id': CHAT_ID, 'caption': caption, 'parse_mode': 'Markdown'}, files={'photo': buf}, timeout=15)
    except: pass

def analyze_stock(symbol, spy_perf, min_score=5):
    try:
        # הורדת נתונים נקייה כדי למנוע את שגיאת ה-Series שראינו בלוגים
        data = yf.download(symbol, period="1y", interval="1d", progress=False)
        if data.empty or len(data) < 50: return None, 0, ""
        
        # תיקון קריטי למבנה הנתונים
        df = data.copy()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        close = df['Close'].dropna()
        last_p = float(close.iloc[-1])
        
        # חישוב אינדיקטורים בסיסיים
        sma50 = close.rolling(50).mean().iloc[-1]
        sma200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else sma50
        
        score = 0
        reasons = []
        
        if last_p > sma50: score += 3; reasons.append("📈 מעל ממוצע 50")
        if last_p > sma200: score += 3; reasons.append("🔋 מעל ממוצע 200")
        
        # בדיקת חוזק יחסי (RS)
        stock_perf = (last_p / float(close.iloc[-21])) - 1
        if stock_perf > spy_perf: score += 4; reasons.append("💪 חזקה מהשוק")
        
        # זיהוי שבירה (התראת מכירה)
        is_sell = last_p < float(df['Low'].tail(20).min()) * 1.01
        
        if score >= min_score or is_sell:
            rec = "🔴 למכירה" if is_sell else ("💎 קנייה" if score >= 8 else "⚖️ מעקב")
            msg = (f"🔍 **{symbol} | ציון: {score}/10**\n"
                   f"📢 המלצה: *{rec}*\n"
                   f"💰 מחיר: `{last_p:.2f}`\n"
                   f"------------------\n" + "\n".join(reasons))
            return df, score, msg
        return None, 0, ""
    except Exception as e:
        print(f"Error analyzing {symbol}: {e}")
        return None, 0, ""

def scanner():
    while True:
        try:
            send_msg("🛰️ **התחלת סריקה חכמה (S&P500 + ישראל)...**")
            spy = yf.download('SPY', period="1y", progress=False)['Close'].squeeze()
            if isinstance(spy, pd.DataFrame): spy = spy.iloc[:, 0]
            spy_perf = (float(spy.iloc[-1]) / float(spy.iloc[-21])) - 1
            
            # רשימה מאוזנת למניעת קריסת שרת
            tickers = ['NVDA', 'AAPL', 'TSLA', 'MSFT', 'GOOGL', 'AMZN', 'META', 'BTC-USD', 'GC=F', 'LUMI.TA', 'POLI.TA']
            
            found = 0
            for s in tickers:
                df, score, msg = analyze_stock(s, spy_perf)
                if df is not None:
                    send_plot(s, df, msg)
                    found += 1
                time.sleep(2) # הפסקה למניעת חסימה
            
            send_msg(f"✅ סריקה הושלמה. נמצאו {found} איתותים.")
            time.sleep(3600) # סריקה פעם בשעה
        except Exception as e:
            print(f"Scanner error: {e}")
            time.sleep(60)

def listen():
    last_id = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={last_id+1}&timeout=30"
            res = requests.get(url, timeout=35).json()
            for u in res.get("result", []):
                last_id = u["update_id"]
                if "message" in u and "text" in u["message"]:
                    t = u["message"]["text"].upper().strip()
                    spy = yf.download('SPY', period="1y", progress=False)['Close'].squeeze()
                    if isinstance(spy, pd.DataFrame): spy = spy.iloc[:, 0]
                    spy_perf = (float(spy.iloc[-1]) / float(spy.iloc[-21])) - 1
                    df, score, msg = analyze_stock(t, spy_perf, min_score=0)
                    if df is not None: send_plot(t, df, msg)
                    else: send_msg(f"❌ לא נמצאו נתונים עבור {t}")
        except: time.sleep(2)

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    Thread(target=scanner).start()
    listen()
