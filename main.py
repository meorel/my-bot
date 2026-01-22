import yfinance as yf
import pandas as pd
import requests
import time
import io
import matplotlib.pyplot as plt
import numpy as np
from flask import Flask
from threading import Thread

# --- הגדרות מערכת ---
TOKEN = "8456706482:AAFUhE3sdD7YZh4ESz1Mr4V15zYYLXgYtuM"
CHAT_ID = "605543691"

app = Flask('')
@app.route('/')
def home(): return "AI Pro Trader - Full System Online"

def send_msg(text):
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=10)
    except: pass

def send_plot(symbol, df, caption, levels=None):
    try:
        plt.figure(figsize=(10, 6))
        plt.plot(df.index[-120:], df['Close'].tail(120), label='Price', color='blue', linewidth=2)
        plt.plot(df.index[-120:], df['SMA50'].tail(120), label='SMA50', color='orange', alpha=0.8)
        plt.plot(df.index[-120:], df['SMA200'].tail(120), label='SMA200', color='red', alpha=0.8)
        
        # ציור רמות תמיכה והתנגדות שנמצאו
        if levels:
            for l in levels:
                plt.axhline(y=l, color='gray', linestyle='--', alpha=0.3)

        plt.title(f"Technical Analysis: {symbol}")
        plt.grid(True, alpha=0.1)
        plt.legend()
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", data={'chat_id': CHAT_ID, 'caption': caption, 'parse_mode': 'Markdown'}, files={'photo': buf}, timeout=15)
    except: pass

def get_levels(df):
    """מציאת רמות מחיר משמעותיות מהשנה האחרונה"""
    prices = df['Close'].tail(252).values
    hist, bin_edges = np.histogram(prices, bins=15)
    # לוקחים רמות שבהן המחיר שהה מעל 10% מהשנה
    significant_levels = bin_edges[np.where(hist > 25)]
    return sorted(significant_levels.tolist())

def analyze_pro(symbol, spy_perf, min_score=3):
    try:
        data = yf.download(symbol, period="2y", interval="1d", progress=False)
        if data.empty or len(data) < 250: return None, 0, ""
        
        df = data.copy()
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
        close = df['Close'].dropna()
        high = df['High'].dropna()
        low = df['Low'].dropna()
        open_p = df['Open'].dropna()
        
        df['SMA50'] = close.rolling(50).mean()
        df['SMA200'] = close.rolling(200).mean()
        
        last_p = float(close.iloc[-1])
        prev_p = float(close.iloc[-2])
        score = 0
        details = []
        is_sell = False

        # 1. צלב זהב טרי (7 ימים)
        for i in range(-7, 0):
            if df['SMA50'].iloc[i-1] <= df['SMA200'].iloc[i-1] and df['SMA50'].iloc[i] > df['SMA200'].iloc[i]:
                score += 5; details.append("🌟 **צלב זהב טרי (פריצה חזקה)**"); break

        # 2. תמיכה והתנגדות שנתית
        levels = get_levels(df)
        res_levels = [l for l in levels if l > last_p * 1.01]
        sup_levels = [l for l in levels if l < last_p * 0.99]
        
        main_res = min(res_levels) if res_levels else float(high.max())
        main_sup = max(sup_levels) if sup_levels else float(low.min())

        if last_p > main_res and prev_p <= main_res:
            score += 3; details.append(f"🚀 פריצת התנגדות שנתית ({main_res:.2f})")
        elif last_p < main_sup and prev_p >= main_sup:
            is_sell = True; details.append(f"📉 **שבירת תמיכה ({main_sup:.2f}) - התראת מכירה!**")

        # 3. גאפים פתוחים (שנתי)
        for i in range(1, len(df)-1):
            if float(open_p.iloc[i]) > float(close.iloc[i-1]) * 1.015:
                if float(low.iloc[i:].min()) > float(close.iloc[i-1]):
                    details.append("🕳️ גאפ פתוח מהשנה האחרונה טרם נסגר"); break

        # 4. חוזק יחסי (RS) ומגמה
        if last_p > df['SMA50'].iloc[-1]: score += 2; details.append("📈 מעל ממוצע 50")
        if (last_p / float(close.iloc[-21])) - 1 > spy_perf: score += 2; details.append("💪 חזקה מהשוק")

        if score >= min_score or is_sell:
            rec = "🔴 למכירה" if is_sell else ("💎 קנייה" if score >= 7 else "⚖️ מעקב")
            msg_type = "🚨 התראה" if is_sell else "🔍 איתות"
            msg = (f"{msg_type}: **{symbol} | ציון: {score}/10**\n"
                   f"📢 המלצה: *{rec}*\n"
                   f"💰 מחיר: `{last_p:.2f}`\n"
                   f"📏 התנגדות: `{main_res:.2f}` | ⚓ תמיכה: `{main_sup:.2f}`\n"
                   f"------------------\n" + "\n".join(details))
            return df, score, msg, levels
        return None, 0, "", []
    except:
