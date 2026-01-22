import yfinance as yf
import pandas as pd
import requests
import time
from flask import Flask
from threading import Thread

# --- הגדרות מערכת ---
TOKEN = "8456706482:AAFUhE3sdD7YZh4ESz1Mr4V15zYYLXgYtuM"
CHAT_ID = "605543691"

app = Flask('')
@app.route('/')
def home(): return "Fully Automated Professional Scanner Active"

def send_msg(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.get(url, params={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"})

def get_sp500():
    try:
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        return pd.read_html(url)[0]['Symbol'].tolist()
    except: return ['AAPL', 'NVDA', 'TSLA', 'MSFT', 'META', 'GOOGL', 'AMZN']

# רשימת מעקב מורחבת (ישראל, סחורות, קריפטו)
WATCHLIST = [
    'LUMI.TA', 'POLI.TA', 'BEZQ.TA', 'NICE.TA', 'ICL.TA', 'MNDY', 'ELTK',
    'GC=F', 'SI=F', 'CL=F', 'BTC-USD', 'ETH-USD', 'SOL-USD'
]

def analyze_full_engine(symbol, spy_perf):
    try:
        df = yf.download(symbol, period="1y", interval="1d", progress=False)
        if len(df) < 200: return None
        
        # חישוב אינדיקטורים
        df['SMA50'] = df['Close'].rolling(window=50).mean()
        df['SMA150'] = df['Close'].rolling(window=150).mean()
        df['SMA200'] = df['Close'].rolling(window=200).mean()
        df['Vol_Avg'] = df['Volume'].rolling(window=20).mean()
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        score = 0
        details = []

        # 1. צלבים (3 נק')
        if prev['SMA50'] <= prev['SMA200'] and last['SMA50'] > last['SMA200']:
            score += 3
            details.append("🌟 צלב זהב (50/200)")
        
        # 2. מגמת 150 (2 נק')
        if last['Close'] > last['SMA150']:
            score += 2
            details.append("📈 מגמה חיובית (מעל 150)")

        # 3. מבנה כוס וידית / פריצה (2 נק')
        high_1y = df['High'].max()
        if last['Close'] >= high_1y * 0.95:
            score += 2
            details.append("☕ מבנה כוס וידית / פריצת שיא")

        # 4. ווליום חריג (1.5 נק')
        if last['Volume'] > last['Vol_Avg'] * 1.5:
            score += 1.5
            details.append("🔥 ווליום חריג")

        # 5. חוזק יחסי RS (1.5 נק')
        stock_perf = (last['Close'] / df['Close'].iloc[-21]) - 1
        if stock_perf > spy_perf:
            score += 1.5
            details.append("💪 חוזק יחסי (חזקה מהשוק)")

        # תמיכה והתנגדות (למידע בלבד)
        support = df['Low'].tail(20).min()
        resistance = df['High'].tail(20).max()

        if score >= 7: # רק איתותים באמינות גבוהה
            msg = (f"🚀 **איתות עוצמתי זוהה: {symbol}**\n"
                   f"🏆 **ציון חוזק: {score}/10**\n"
                   f"💰 מחיר: `{last['Close']:.2f}$`\n"
                   f"------------------\n"
                   f"🔍 אינדיקטורים שהתקיימו:\n" + "\n".join(details) + "\n"
                   f"------------------\n"
                   f"🧱 התנגדות (20 יום): `{resistance:.2f}`\n"
                   f"⚓ תמיכה (20 יום): `{support:.2f}`\n"
                   f"🛡️ **סטופ לוס (4%): `{last['Close']*0.96:.2f}`**")
            return msg
        return None
    except: return None

def automation_loop():
    while True:
        try:
            send_msg("🛰️ **סורק ה-AI נכנס לסבב ניתוח עומק על כל השוק...**")
            # חישוב ביצועי שוק להשוואת RS
            spy = yf.download('SPY', period="1y", progress=False)
            spy_perf = (spy['Close'].iloc[-1] / spy['Close'].iloc[-21]) - 1
            
            full_list = get_sp500() + WATCHLIST
            found = 0
            for s in full_list:
                s = s.replace('.', '-') if '-' not in s else s
                res = analyze_full_engine(s, spy_perf)
                if res:
                    send_msg(res)
                    found += 1
                time.sleep(0.6) # מניעת חסימה מ-Yahoo
            
            send_msg(f"✅ סבב הסריקה הסתיים. נמצאו {found} איתותים בציון גבוה.")
            time.sleep(3600) # סריקה כל שעה
        except: time.sleep(60)

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    automation_loop()
