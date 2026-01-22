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
def home(): return "AI Pro Trader - Full System Active"

def send_msg(text):
    requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"})

def send_plot(symbol, df, caption):
    try:
        plt.figure(figsize=(10, 6))
        # מציגים 120 ימי מסחר אחרונים בגרף
        plt.plot(df.index[-120:], df['Close'].tail(120), label='Price', color='blue', linewidth=2)
        plt.plot(df.index[-120:], df['SMA50'].tail(120), label='SMA50', color='orange', alpha=0.7)
        plt.plot(df.index[-120:], df['SMA200'].tail(120), label='SMA200', color='red', alpha=0.7)
        
        plt.title(f"Technical Analysis: {symbol}")
        plt.grid(True, alpha=0.2)
        plt.legend()
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", data={'chat_id': CHAT_ID, 'caption': caption, 'parse_mode': 'Markdown'}, files={'photo': buf})
    except Exception as e:
        print(f"Error sending plot: {e}")

def get_full_list():
    try:
        # משיכת S&P 500
        sp500 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]['Symbol'].tolist()
        # משיכת נאסד"ק 100
        nas100 = pd.read_html('https://en.wikipedia.org/wiki/Nasdaq-100')[4]['Ticker'].tolist()
        # רשימה אישית (ישראל, קריפטו, סחורות)
        others = ['LUMI.TA', 'POLI.TA', 'BEZQ.TA', 'NICE.TA', 'ICL.TA', 'BTC-USD', 'ETH-USD', 'GC=F', 'CL=F', 'SI=F']
        return list(set(sp500 + nas100 + others))
    except:
        return ['AAPL', 'NVDA', 'TSLA', 'MSFT', 'GOOGL', 'BTC-USD', 'GC=F', 'LUMI.TA']

def find_levels(df):
    """מזהה רמות תמיכה והתנגדות משמעותיות בשנה האחרונה"""
    recent_df = df.tail(252)
    # מחפשים אזורי מחיר שבהם היו הרבה סגירות (Clusters)
    prices = recent_df['Close'].values
    hist, bin_edges = np.histogram(prices, bins=15)
    # לוקחים את ה-bins עם הכי הרבה "ביקורים" של המחיר
    significant_bins = bin_edges[np.where(hist > (len(prices) * 0.1))] # לפחות 10% מהזמן
    return sorted(significant_bins.tolist())

def analyze_pro_engine(symbol, spy_perf, min_score=5):
    try:
        df = yf.download(symbol, period="2y", interval="1d", progress=False)
        if df.empty or len(df) < 250: return None, 0, ""
        
        # ניקוי שמות עמודות אם הם בפורמט Multi-index
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        
        close = df['Close'].squeeze()
        high = df['High'].squeeze()
        low = df['Low'].squeeze()
        open_p = df['Open'].squeeze()
        
        df['SMA50'] = close.rolling(50).mean()
        df['SMA200'] = close.rolling(200).mean()
        
        last_p = float(close.iloc[-1])
        prev_p = float(close.iloc[-2])
        score = 0
        details = []
        is_sell_alert = False

        # 1. צלב זהב טרי (חצייה ב-7 הימים האחרונים)
        is_cross = False
        for i in range(-7, 0):
            if df['SMA50'].iloc[i-1] <= df['SMA200'].iloc[i-1] and df['SMA50'].iloc[i] > df['SMA200'].iloc[i]:
                is_cross = True
                break
        if is_cross: 
            score += 5
            details.append("🌟 **צלב זהב טרי (איתות חזק!)**")

        # 2. תמיכה והתנגדות שנתית
        levels = find_levels(df)
        res_levels = [l for l in levels if l > last_p * 1.01]
        sup_levels = [l for l in levels if l < last_p * 0.99]
        
        main_res = min(res_levels) if res_levels else float(high.iloc[:-1].max())
        main_sup = max(sup_levels) if sup_levels else float(low.iloc[:-1].min())

        # זיהוי פריצה (חיובי) או שבירה (שלילי - התראת מכירה)
        if last_p > main_res and prev_p <= main_res:
            score += 3
            details.append(f"🚀 פריצת התנגדות משמעותית ({main_res:.2f})")
        elif last_p < main_sup and prev_p >= main_sup:
            is_sell_alert = True
            details.append(f"📉 **שבירת תמיכה שנתית ({main_sup:.2f}) - התראת מכירה!**")

        # 3. גאפים פתוחים (בדיקת שנה אחורה)
        gap_found = False
        for i in range(1, len(df)-1):
            # גאפ למעלה שטרם נסגר
            if float(open_p.iloc[i]) > float(close.iloc[i-1]) * 1.015:
                if float(low.iloc[i:].min()) > float(close.iloc[i-1]):
                    gap_found = True
                    break
        if gap_found:
            details.append("🕳️ קיים גאפ פתוח מהשנה האחרונה")

        # 4. חוזק יחסי (RS)
        stock_perf = (last_p / float(close.iloc[-21])) - 1
        if stock_perf > spy_perf:
            score += 2
            details.append("💪 חוזק יחסי חיובי (RS)")

        # סיכום המלצה
        if is_sell_alert:
            rec = "🔴 מכירה / יציאה"
            msg_type = "🚨 התראת שבירה"
        elif score >= 7:
            rec = "💎 קנייה חזקה"
            msg_type = "🟢 איתות קנייה"
        else:
            rec = "⚖️ החזקה / מעקב"
            msg_type = "🔍 עדכון שוטף"

        # החלטה אם לשלוח הודעה
        if score >= min_score or is_cross or is_sell_alert:
            msg = (f"{msg_type}: **{symbol}**\n"
                   f"🏆 ציון: {score}/10 | המלצה: *{rec}*\n"
                   f"💰 מחיר: `{last_p:.2f}`\n"
                   f"🧱 התנגדות קרובה: `{main_res:.2f}`\n"
                   f"⚓ תמיכה קרובה: `{main_sup:.2f}`\n"
                   f"------------------\n" + "\n".join(details))
            return df, score, msg
        return None, 0, ""
    except Exception as e:
        return None, 0, ""

def scanner_task():
    while True:
        try:
            send_msg("🛰️ **סורק AI התחיל סבב ניתוח עומק שנתי...**")
            # חישוב ביצועי מדד SPY להשוואה
            spy_data = yf.download('SPY', period="1y", progress=False)['Close'].squeeze()
            spy_perf = (float(spy_data.iloc[-1]) / float(spy_data.iloc[-21])) - 1
            
            tickers = get_full_list()
            found = 0
            for s in tickers:
                s = s.replace('.', '-') if '-' not in s else s
                df, score, msg = analyze_pro_engine(s, spy_perf, min_score=5)
                if df is not None:
                    send_plot(s, df, msg)
                    found += 1
                time.sleep(1.2)
            
            send_msg(f"✅ סבב הסתיים. נמצאו {found} הזדמנויות/איומים.")
            time.sleep(3600) # סריקה כל שעה
        except:
            time.sleep(60)

def listener_task():
    last_id = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={last_id+1}&timeout=20"
            res = requests.get(url).json()
            for u in res.get("result", []):
                last_id = u["update_id"]
                if "message" in u and "text" in u["message"]:
                    ticker = u["message"]["text"].upper().strip()
                    spy_data = yf.download('SPY', period="1y", progress=False)['Close'].squeeze()
                    spy_perf = (float(spy_data.iloc[-1]) / float(spy_data.iloc[-21])) - 1
                    df, score, msg = analyze_pro_engine(ticker, spy_perf, min_score=-10) # מציג הכל לבקשתך
                    if df is not None:
                        send_plot(ticker, df, msg)
                    else:
                        send_msg(f"❌ לא נמצאו נתונים עבור הסימול {ticker}")
        except:
            time.sleep(2)

if __name__ == "__main__":
    # הרצת השרת ב-Thread נפרד
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    # הרצת הסורק האוטומטי
    Thread(target=scanner_task).start()
    # הרצת המאזין להודעות בטלגרם
    listener_task()
