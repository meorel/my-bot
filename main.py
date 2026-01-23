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

# --- מאגר סימולים (S&P 500 + NASDAQ 100 + ISRAEL + COMMODITIES) ---
USA_STOCKS = ['AAPL','MSFT','NVDA','GOOGL','AMZN','META','TSLA','BRK-B','LLY','AVGO','V','JPM','UNH','MA','COST','HD','PG','NFLX','JNJ','ABBV','BAC','CRM','ORCL','ADBE','AMD','CVX','WMT','TMO','CSCO','ABT','DHR','INTU','GE','QCOM','CAT','AXP','PFE','DIS','MS','PM','IBM','INTC','AMAT','UNP','LOW','TXN','SPGI','HON','RTX','GS','BKNG','SBUX','PLTR','UBER','LRCX','ELV','ISRG','MDLZ','PGR','VRTX','REGN','TJX','PANW','LMT','CB','CI','BSX','MMC','AMT','ADI','PLD','ADSK','T','VZ','A','AAL','AAP','ABT','ACN','ADBE','ADI','ADM','ADP','ADSK','AEE','AEP','AES','AFL','AIG','AIZ','AJG','AKAM','ALB','ALGN','ALK','ALL','ALLE','AMAT','AMCR','AMD','AME','AMGN','AMP','AMT','AMZN','ANET','ANSS','AON','AOS','APA','APD','APH','APTV','ARE','ATO','AVB','AVGO','AVY','AWK','AXP','AZO','BA','BAC','BALL','BAX','BBWI','BBY','BDX','BEN','BIIB','BIO','BK','BKNG','BKR','BLK','BMY','BR','BRO','BSX','BWA','BXP','C','CAG','CAH','CARR','CAT','CB','CBOE','CBRE','CCI','CCL','CDNS','CDW','CE','CEG','CF','CFG','CHD','CHRW','CHTR','CI','CINF','CL','CLX','CMA','CMCSA','CME','CMG','CMI','CMS','CNC','CNP','COF','COO','COP','COST','CPB','CPT','CRL','CRM','CSGP','CSX','CTAS','CTLT','CTRA','CTSH','CTVA','CVS','CVX','D','DAL','DD','DE','DFS','DG','DGX','DHI','DHR','DIS','DLR','DLTR','DOV','DOW','DPZ','DRI','DTE','DUK','DVA','DVN','DXCM','EA','EBAY','ECL','ED','EFX','EIX','EL','ELV','EMN','EMR','ENPH','EOG','EPAM','EQIX','EQR','ES','ESS','ETN','ETR','ETSY','EVRG','EW','EXC','EXPD','EXPE','EXR','F','FANG','FAST','FCX','FDS','FDX','FE','FIS','FISV','FITB','FLT','FMC','FOXA','FOX','FRT','FTNT','FTV','GD','GE','GEHC','GEN','GILD','GIS','GL','GLW','GM','GNRC','GOOGL','GOOG','GPC','GPN','GRMN','GS','GWW','HAL','HAS','HBAN','HCA','HD','HES','HIG','HII','HLT','HOLX','HON','HPE','HPQ','HRL','HSIC','HST','HSY','HUM','HWM','IBM','ICE','IDXX','IEX','IFF','ILMN','INCY','INTC','INTU','INVH','IP','IPG','IQV','IR','IRM','ISRG','IT','ITW','IVZ','JBHT','JCI','JKHY','JNJ','JNPR','JPM','K','KDP','KEY','KEYS','KHC','KIM','KLAC','KMB','KMI','KMX','KO','KR','L','LDOS','LEN','LH','LHX','LIN','LKQ','LLY','LMT','LNC','LNT','LOW','LRCX','LW','LYB','LYV','MA','MAA','MAR','MAS','MCD','MCHP','MCK','MCO','MDLZ','MDT','MET','META','MGM','MHK','MKC','MKTX','MLM','MMC','MMM','MNST','MO','MOH','MOS','MPC','MPWR','MRK','MRNA','MS','MSI','MSFT','MTB','MTCH','MTD','MU','NCLH','NDAQ','NDSN','NEE','NEM','NFLX','NI','NKE','NSC','NTAP','NTRS','NUE','NVDA','NVR','NWL','NWS','NWSA','NXPI','O','ODFL','OGN','OKE','OMC','ON','ORCL','ORLY','OTIS','OXY','PANW','PARA','PAYC','PAYX','PCAR','PCG','PEG','PEP','PFE','PFG','PG','PGR','PH','PHM','PKG','PLD','PLTR','PM','PNC','PNR','PNW','POOL','PPG','PPL','PRU','PSA','PSX','PTC','PVH','PWR','PYPL','QCOM','QRVO','RCL','REG','REGN','RF','RHI','RJF','RL','RMD','ROK','ROL','ROP','ROST','RSG','RTX','RVTY','SBAC','SBUX','SCHW','SEDG','SEE','SHW','SJM','SLB','SNA','SNPS','SO','SPG','SPGI','SRE','STE','STT','STX','STZ','SWK','SWKS','SYF','SYK','SYY','T','TAP','TDG','TDY','TECH','TEL','TER','TFC','TFX','TGT','TJX','TMO','TMUS','TPR','TRGP','TRMB','TROW','TRV','TSCO','TSLA','TSN','TT','TTWO','TXN','TXT','TYL','UAL','UDR','UHS','ULTA','UNH','UNP','UPS','URI','USB','V','VFC','VICI','VLO','VMC','VNO','VRSK','VRSN','VRTX','VTR','VZ','WAB','WAT','WBA','WBD','WDC','WEC','WELL','WFC','WHR','WM','WMB','WMT','WRB','WST','WTW','WY','WYNN','XEL','XOM','XRAY','XYL','YUM','ZBH','ZBRA','ZION','ZTS']
ISRAEL_STOCKS = ['LUMI.TA','POLI.TA','DSCT.TA','FIBI.TA','AZRG.TA','BEZQ.TA','NICE.TA','ICL.TA','ESLT.TA','TEVA.TA','DELEKG.TA','ENOG.TA','ORL.TA','AMOT.TA','MELIS.TA','MTRX.TA','SPNS.TA','HRL.TA','MRLN.TA','AFCON.TA','AVIV.TA','DANE.TA','ARAD.TA','DIMO.TA','OPLN.TA']
COMMODITIES = ['GC=F','CL=F','SI=F','HG=F','NG=F','BTC-USD','ETH-USD','^TA35.TA','^TA125.TA','^GSPC','^IXIC']

ALL_TICKERS = sorted(list(set(USA_STOCKS + ISRAEL_STOCKS + COMMODITIES)))

@app.route('/')
def home(): return "Master Scanner v7 - All Patterns Active"

def send_msg(text):
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=10)
    except: pass

def send_plot(symbol, name, df, caption):
    try:
        plt.figure(figsize=(10, 6))
        prices = df['Close'].tail(120)
        plt.plot(df.index[-120:], prices, label='Price', color='black', linewidth=2)
        plt.plot(df.index[-120:], df['SMA50'].tail(120), label='SMA 50', color='blue', alpha=0.7)
        plt.plot(df.index[-120:], df['SMA200'].tail(120), label='SMA 200', color='red', linewidth=2)
        plt.title(f"{name}")
        plt.legend(); buf = io.BytesIO(); plt.savefig(buf, format='png'); buf.seek(0); plt.close()
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", data={'chat_id': CHAT_ID, 'caption': caption, 'parse_mode': 'Markdown'}, files={'photo': buf}, timeout=20)
    except: pass

def analyze_strategy(symbol, my_price=None, is_auto=False):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="2y")
        if df.empty or len(df) < 200: return None
        
        last_p = float(df['Close'].iloc[-1])
        if is_auto and symbol in sent_alerts:
            if datetime.now() < sent_alerts[symbol] + timedelta(hours=12): return None

        # ממוצעים ותבניות
        df['SMA50'] = df['Close'].rolling(50).mean()
        df['SMA200'] = df['Close'].rolling(200).mean()
        s50, s200 = df['SMA50'].iloc[-1], df['SMA200'].iloc[-1]
        
        # זיהוי Crosses
        is_golden = (df['SMA50'].iloc[-2] <= df['SMA200'].iloc[-2] and s50 > s200)
        is_death = (df['SMA50'].iloc[-2] >= df['SMA200'].iloc[-2] and s50 < s200)

        # תבניות מחיר (Double Bottom, Cup & Handle - זיהוי פשטני למערכת סריקה)
        low_252 = df['Low'].tail(252).min()
        high_252 = df['High'].tail(252).max()
        is_breakout = last_p >= high_252 * 0.99
        
        score = 0
        patterns = []
        
        if s50 > s200: score += 4; patterns.append("מגמה שורית (50>200)")
        if is_golden: score += 3; patterns.append("🌟 צלב הזהב (Golden Cross)")
        if is_death: score -= 5; patterns.append("💀 צלב המוות (Death Cross)")
        if is_breakout: score += 2; patterns.append("🚀 פריצת שיא שנתי")
        if last_p < low_252 * 1.05: score -= 2; patterns.append("📉 סמוך לשפל שנתי")

        if is_auto and not (score >= 9 or score <= 1 or is_golden or is_death): return None
        
        rec = "💎 **קנייה חזקה**" if score >= 8 else "🔴 **מכירה/סיכון**" if score <= 1 else "⚖️ **נייטרלי**"
        
        personal = ""
        if my_price:
            profit = (last_p - my_price) / my_price
            personal = f"\n\n💬 **ייעוץ:** קנית ב-{my_price:.2f} ({profit:+.1%}). "
            personal += "החזק בביטחון." if score >= 7 else "שקול סטופ."

        name = ticker.info.get('longName', symbol)
        p_text = "\n".join([f"• {p}" for p in patterns])
        msg = (f"🎯 **{name} ({symbol}) | ציון: {score}/10**\n"
               f"📢 **מסקנה:** {rec}\n\n"
               f"📊 **תבניות שזוהו:**\n{p_text}\n\n"
               f"💰 מחיר: `{last_p:.2f}` | 📍 ממוצע 50: `{s50:.2f}` | 📍 ממוצע 200: `{s200:.2f}`{personal}")
        
        if is_auto: sent_alerts[symbol] = datetime.now()
        return df, msg, name
    except: return None

def scanner_worker():
    while True:
        send_msg(f"🚀 **סריקת מאסטר החלה על {len(ALL_TICKERS)} ניירות.**")
        found = 0
        for s in ALL_TICKERS:
            res = analyze_strategy(s, is_auto=True)
            if res:
                send_plot(s, res[2], res[0], res[1])
                found += 1; time.sleep(5)
            time.sleep(0.3)
        send_msg(f"✅ סבב מלא הסתיים. נמצאו {found} הזדמנויות.")
        time.sleep(1800)

def listen_worker():
    last_id = 0
    while True:
        try:
            r = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={last_id+1}&timeout=30").json()
            for u in r.get("result", []):
                last_id = u["update_id"]
                if "message" in u and "text" in u["message"]:
                    txt = u["message"]["text"].upper().strip()
                    send_msg(f"🔎 מנתח עבורך את {txt}...")
                    if "BY" in txt:
                        p = txt.split(); res = analyze_strategy(p[1], my_price=float(p[2]))
                    else: res = analyze_strategy(txt)
                    if res: send_plot(txt, res[2], res[0], res[1])
                    else: send_msg(f"❌ לא נמצא מידע.")
        except: time.sleep(1)

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    Thread(target=scanner_worker).start()
    listen_worker()
