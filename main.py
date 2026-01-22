import yfinance as yf
import pandas as pd
import requests
import time
import io
import matplotlib.pyplot as plt
from flask import Flask
from threading import Thread

TOKEN = "8456706482:AAFUhE3sdD7YYU6sdD7YZh4ESz1Mr4V15zYYLXgYtuM" # וודא שהטוקן תקין
CHAT_ID = "605543691"

app = Flask('')
@app.route('/')
def home(): return "Advanced Pro Scanner Active"

def send_msg(text):
    requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"})

def send_plot(symbol, df, caption):
    try:
        plt.figure(figsize=(10, 6))
        plt.plot(df.index[-120:], df['Close'].tail(120), label='Price', color='blue', linewidth=2)
        plt.plot(df.index[-120:], df['SMA50'].tail(120), label='SMA50', color='orange', alpha=0.8)
        plt.plot(df.index[-120:], df['SMA200'].tail(120), label='SMA200', color='red', alpha=0.8)
        plt.title(f"Analysis: {symbol}")
        plt.grid(True, alpha=0.2)
        plt.legend()
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", data={'chat_id': CHAT_ID, 'caption': caption, 'parse_mode': 'Markdown'}, files={'photo': buf})
    except: pass

def get_full_list():
    try:
        sp500 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]['Symbol'].tolist()
        others = ['LUMI.TA', 'POLI.TA', 'BEZQ.TA', 'NICE.TA', 'ICL.TA', 'BTC-USD', 'ETH-USD', 'GC=F', 'CL=F']
        return list(set(sp500 + others))
    except: return ['AAPL', 'NVDA', 'TSLA', 'GC=F', 'LUMI.TA', 'BTC-USD']

def analyze_pro(symbol, spy_perf, min_score=5):
    try:
        df = yf.download(symbol, period="2y", interval="1d", progress=False)
        if df.empty or len(df) < 250: return None, 0, ""
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        
        close = df['Close'].squeeze()
        low = df['Low'].squeeze()
        high = df['High'].squeeze()
        open_p = df['Open'].squeeze()
        
        df['SMA50'] = close.rolling(50).mean()
        df['SMA200'] = close.rolling(200).mean()
        last_p = float(close.iloc[-1])
        
        score = 0
        details = []

        # 1. צלב זהב טרי (7 ימים אחרונים) - 4 נקודות!
        is_cross = False
        for i in range(-7, 0):
            if df['SMA50'].iloc[i-1] <= df['SMA200'].iloc[i-1] and df['SMA50'].iloc[i] > df['SMA200'].iloc[i]:
                is_cross = True
                break
        if is_cross:
            score += 4
            details.append("🌟 **צלב זהב טרי (פריצה!)**")

        # 2. תמיכה והתנגדות שנתית
        res_year = float(high.tail(252).max())
        sup_year = float(low.tail(252).min())
        
        # בדיקת קרבה להתנגדות (זהירות!)
        dist_to_res = (res_year - last_p) / last_p
        if dist_to_res < 0.015:
            score -= 2
            details.append("⚠️ זהירות: קרוב מאוד להתנגדות שנתית")
        elif last_p > res_year * 0.98:
            score += 2
            details.append("🚀 פריצת שיא שנתי / Cup & Handle")

        # 3. גאפים פתוחים (בדיקת 10 ימים אחרונים)
        for i in range(-10, 0):
            prev_close = float(close.iloc[i-1])
            curr_open = float(open_p.iloc[i])
            if abs(curr_open - prev_close) / prev_close > 0.01:
                details.append(f"🕳️ גאפ פתוח זוהה בטווח קרוב")
                break

        # 4. חוזק יחסי ומגמה
        if last_p > df['SMA50'].iloc[-1]: score += 2; details.append("📈 מעל ממוצע 50")
        if (last_p / float(close.iloc[-21])) - 1 > spy_perf: score += 2; details.append("💪 חזקה מהשוק (RS)")

        if score >= min_score or is_cross:
            rec = "💎 קנייה חזקה" if score >= 7 else "⚖️ החזקה / המתנה"
            if dist_to_res < 0.01: rec = "🧱 המתנה (קרוב להתנגדות)"
            
            msg = (f"🔍 **{symbol} | ציון: {score}/10**\n"
                   f"📢 המלצה: *{rec}*\n"
                   f"💰 מחיר: `{last_p:.2f}`\n"
                   f"📏 התנגדות שנתית: `{res_year:.2f}`\n"
                   f"⚓ תמיכה שנתית: `{sup_year:.2f}`\n"
                   f"------------------\n" + "\n".join(details))
            return df, score, msg
        return None, 0, ""
    except: return None, 0, ""

# ... (שאר פונקציות ה-Scanner וה-Listener נשארות זהות)
