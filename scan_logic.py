#======== Libraries ========#
import yfinance as yf
import pandas as pd
import requests
import schedule
import time
from datetime import datetime
import pytz

# ─────────────────────────────────────────────
#  Telegram 
# ─────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = "8744230282:AAGuj83flyCiomP73eBC4J_Cxgtf0Ce1kxo"
TELEGRAM_CHAT_ID   = "7228855934"

# ─────────────────────────────────────────────
#  Pairs & Time frame 
# ─────────────────────────────────────────────

PAIRS = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "USDJPY=X",
    "XAU/USD": "GC=F",
    "USD/CAD": "USDCAD=X",
    "AUD/USD": "AUDUSD=X",
    "YM!":    "^DJI",
    "SNP":   "^GSPC",
    "NQ":  "^IXIC"}

TIMEFRAMES = {"Daily": ("1d",  "60d")}   # interval, period


# ─────────────────────────────────────────────
#  TELEGRAM
# ─────────────────────────────────────────────
def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
    except Exception as e:
        print(f"[Telegram Error] {e}")



# ─────────────────────────────────────────────
#  Fetch Daily Candel 
# ─────────────────────────────────────────────

def fetch_candel(pair_sys, tf, Period):
    df = yf.download(pair_sys, interval=tf, period=Period, auto_adjust=True) # type: ignore
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)  # ← ADD THIS
    today = datetime.now(pytz.utc).date()
    df.index = pd.to_datetime(df.index)
    df = df[df.index.date < today]
    return df

# ─────────────────────────────────────────────
#  Swing Point Logic 
# ─────────────────────────────────────────────

def swing_point(df : pd.DataFrame):
    c1 = df.iloc[-3]
    c2 = df.iloc[-2]
    c1_o, c1_h, c1_l, c1_c = float(c1["Open"]), float(c1["High"]), float(c1["Low"]), float(c1["Close"])
    c2_o, c2_h, c2_l, c2_c = float(c2["Open"]), float(c2["High"]), float(c2["Low"]), float(c2["Close"])
    #== Bullish scenario ==# 
    if c2_c >c1_l and c2_l<c1_l:
        if c2_c>c2_o:
            return (True,"Bullish──C2")
    #== Bearish scenario ==#
    elif c2_h > c1_h and c2_c < c1_h:
        if c2_c<c2_o:
            return (True,"Bearish──C2")
    return False,None

# ─────────────────────────────────────────────
#   run Scan
# ─────────────────────────────────────────────

def scan():
    now = datetime.now(pytz.utc).strftime("%Y-%m-%d %H:%M UTC")
    pair_dict={}
    for pair_label,pair_sys in PAIRS.items():
        for tf_label ,(interval , period ) in TIMEFRAMES.items():
            df=fetch_candel(pair_sys,interval,period)
             #=== If data Frame is empty===# 
            if df.empty or len(df) < 3:
                continue
            #=== Guards It===#
            result,direction=swing_point(df)
            if result:
                pair_dict[pair_label]=direction
    return pair_dict

# ─────────────────────────────────────────────
#   Create Message for Telegram
# ─────────────────────────────────────────────


def message(pair_details_dict) -> str:
    now = datetime.now(pytz.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = ""
    for pair, direction in pair_details_dict.items():
        lines += f"📌 {pair}  —  {direction}\n"
    msg = (
        f"<b>⚡ SWING POINT SCANNER</b>\n"
        f"⏰ {now}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{lines}"
        f"━━━━━━━━━━━━━━━━━━\n"
    )
    return msg

# ─────────────────────────────────────────────
#   Main function To execute All
# ─────────────────────────────────────────────
def main():
    pair_details_dict=scan()
    #=======If dictionary is empty==========#
    if not pair_details_dict:
        send_telegram("🔍 Scan Complete — No setups found today.")
        return
    #=======guards it==========#
    msg=message(pair_details_dict)
    send_telegram(msg)

main()