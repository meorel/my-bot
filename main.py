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
def home(): return "Systematic Global & Israel Scanner Active"

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
        # ארה"ב: S&P 500 + NASDAQ 100
        sp500 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]['Symbol'].tolist()
        nasdaq100 = pd.read_html('https://en.wikipedia.org/wiki/Nasdaq-100')[4]['Ticker'].tolist()
        
        # ישראל: רשימת ליבה של מניות מובילות (בנקים, ביטחון, נדל"ן, אנרגיה)
        israel_core = [
            'LUMI.TA', 'POLI.TA', 'DSCT.TA', 'FIBI.TA', 'AZRG.TA', 'BEZQ.TA', 'NICE.TA', 'ICL.TA', 
            'ESLT.TA', 'AFCON.TA', 'ORL.TA', 'HRL.TA', 'MGDL.TA', 'CLIS.TA', 'TEVA.TA', 'DELEKG.TA',
            'ENOG.TA', 'NWMD.TA', 'ALHE.TA', 'MTRX.TA', 'SPNS.TA', 'OPK.TA', 'DRCO.TA', 'AMOT.TA',
            'SANO.TA', 'STRS.TA', 'ELCO.TA', 'HAPL.TA', 'MELIS.TA', 'SHL.TA'
        ]
        
        # סחורות ומדדים
        others = ['GC=F', 'CL=F', 'SI=F', '^TA35.TA', '^TA125.TA', 'BTC-USD', 'ETH-USD']
        
        return sorted(list(set(sp500 + nasdaq100 + israel_core + others)))
    except:
        return ['AAPL', 'MSFT', 'NVDA', 'LUMI.TA', 'BTC-USD', 'GC=F']

def get_clean_name(symbol, ticker_info):
    names = {
        'GC=F': 'זהב (Gold)', 'CL=F': 'נפט (Crude Oil)', 'SI=F': 'כסף (Silver)', 
        'BTC-USD': 'ביטקוין', 'ETH-USD': 'איתריום', '^TA35.TA': 'מדד ת"א 35', '^TA125.TA': 'מדד ת"א 125'
    }
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
            if datetime.now() < prev['time'] + timedelta(hours=12) and abs((last_p - prev['price'])/prev['price']) < 0.025:
                return None

        name = get_clean_name(symbol, ticker.info)
        df['SMA50'] = df['Close'].rolling(50).mean()
        df['SMA150'] = df['Close'].rolling(150).mean()
        df['SMA200'] = df['Close'].rolling(200).mean()
        
        s50, s150, s200 = df['SMA50'].iloc[-1], df['SMA150'].iloc[-1], df['SMA200'].iloc[-1]
        sup, res = float(df['Low'].tail(252).min()), float(df['High'].tail(252).max())
        
        score = 0
        if last_p > s50: score += 3
        if last_p > s150: score += 2
        if last_p > s200: score += 2
        
        perf_1m = (last_p / float(df['Close'].iloc[-21])) - 1
        if perf_1m > spy_perf: score += 3

        if is_auto and not (score >= 8 or score <= 2): return None 
        
        rec = "💎 **קנייה חזקה**" if score >= 8 else "🔴 **מכירה/סיכון**" if score <= 2 else "⚖️ **נייטרלי**"
        sl = min(float(df['Low'].tail(20).min()) * 0.99, last_p * 0.95)
        
        msg = (f"🎯 **{name} ({symbol}) | ציון: {score}/10**\n"
               f"📢 **מסקנה:** {rec}\n\n"
               f"📍 ממוצע 50: `{s50:.2f}` ({'✅' if last_p > s50 else '❌'})\n"
               f"📍 ממוצע 150: `{s150:.2f}` ({'✅' if last_p > s150 else '❌'})\n"
               f"📍 ממוצע 200: `{s200:.2f}` ({'✅' if last_p > s200 else '❌'})\n\n"
               f"💰 מחיר: `{last_p:.2f}` | 🛑 סטופ: `{sl:.2f}`\n"
               f"📏 התנגדות: `{res:.2f}` | ⚓ תמיכה: `{sup:.2f}`")
        
        if is_auto: sent_alerts[symbol] = {'time': datetime.now(), 'price': last_p}
        return df, msg, sup, res, name
    except: return None

def scanner():
    time.sleep(10)
    send_msg("🚀 **המערכת הוגדרה לסריקה שעתי סיסטמטית הכוללת את מדדי ישראל וארה\"ב.**")
    
    while True:
        all_tickers = get_full_lists()
        total_tickers = len(all_tickers)
        chunk_size = total_tickers // 6
        
        for i in range(6):
            start_idx = i * chunk_size
            end_idx = (i + 1) * chunk_size if i < 5 else total_tickers
            current_chunk = all_tickers[start_idx:end_idx]
            
            try:
                spy = yf.download('SPY', period="1mo", progress=False)['Close'].squeeze()
                spy_perf = (float(spy.iloc[-1]) / float(spy.iloc[0])) - 1
            except: spy_perf = 0
            
            for s in current_chunk:
                is_israel = ".TA" in s
                # דילוג על ישראל בסופ"ש (שישי-שבת)
                if is_israel and datetime.now().weekday() in [4, 5]: continue
                
                res = analyze_strategy(s.replace('.', '-'), spy_perf, is_auto=True)
                if res:
                    send_plot(s, res[4], res[0], res[1], res[2], res[3])
                    time.sleep(10)
                time.sleep(1.8) # השהייה יסודית למניעת חסימות
            
            time.sleep(60) 
        
        send_msg(f"🔄 **הושלמה סריקה שעתי מלאה.**\nנסרקו בהצלחה {total_tickers} ניירות ערך כולל ישראל, ארה\"ב וסחורות.")
        time.sleep(300)

def listen():
    last_id = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={last_id+1}&timeout=30"
            r = requests.get(url, timeout=35).json()
            for u in r.get("result", []):
                last_id = u["update_id"]
                if "message" in u and "text" in u["message"]:
                    txt = u["message"]["text"].upper().strip()
                    try:
                        spy = yf.download('SPY', period="1mo", progress=False)['Close'].squeeze()
                        spy_perf = (float(spy.iloc[-1]) / float(spy.iloc[0])) - 1
                    except: spy_perf = 0
                    
                    if txt.startswith("BY "):
                        p = txt.split()
                        res = analyze_strategy(p[1], spy_perf, my_price=float(p[2]), is_auto=False)
                    else:
                        res = analyze_strategy(txt, spy_perf, is_auto=False)
                    
                    if res: send_plot(txt.split()[-1], res[4], res[0], res[1], res[2], res[3])
        except: time.sleep(5)

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    Thread(target=scanner).start()
    listen()
