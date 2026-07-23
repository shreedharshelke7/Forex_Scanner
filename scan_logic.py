#======== Libraries ========#
import twelvedata
import pandas as pd
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from time import sleep
from dotenv import load_dotenv
import os
# ─────────────────────────────────────────────
#  Api keys, Client and Token 
# ─────────────────────────────────────────────
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TWELVE_DATA_API_KEY = os.getenv("Twelvedata_API_Key")
client = twelvedata.TDClient(TWELVE_DATA_API_KEY)
# ─────────────────────────────────────────────
#  Pairs & Time frame 
# ─────────────────────────────────────────────

PAIRS = ["EUR/USD","GBP/USD" ,"AUD/USD" ,"NZD/USD" ,"USD/CAD" ,"USD/JPY" ,"USD/CHF" ,"XAU/USD"]
# ─────────────────────────────────────────────
#  Fetch data from twelve data
# ─────────────────────────────────────────────
def fetch_data(pair_sym,interval,period):
    sleep(8)
    data = client.time_series(
        symbol=pair_sym,
        interval=interval,
        outputsize=period
    )
    df=data.as_pandas()
    if df is not None:
        df.index = pd.to_datetime(df.index)
        df= df.sort_index()
        df= df[df.index.dayofweek < 5]
        df= df.astype(float)
        print(df.head(4))
        return df
    return pd.DataFrame()


def scan(df):
    c1=df.iloc[-3]
    c2=df.iloc[-2]
    c1_l=c1["low"]
    c1_h=c1["high"]
    c1_o=c1["open"]
    c1_c=c1["close"]
    c2_l=c2["low"]
    c2_h=c2["high"]
    c2_o=c2["open"]
    c2_c=c2["close"]

    if c1_h<c2_h and c2_c < c1_h:
        return (True,"| Bearish--C2 |")
    if c1_l > c2_l and c2_c > c1_l:
        return (True , "| Bullish--C2 |")
    return (False,None)

def process_create():
    shorlisted_pair={}
    for pair in PAIRS:
        df=fetch_data(pair,"1day","60")
        sleep(20)
        result,msg=scan(df)
        if result:
            shorlisted_pair[pair]=msg
    return shorlisted_pair

def Bullish_2LQ_check(df):
    candel_lows=df['low'].iloc[:-2]
    _2LQ_candel_low=df['low'].iloc[-2]
    list_low_not_taken=[]
    counter=0
    
    for low in candel_lows:

        if not list_low_not_taken:
            list_low_not_taken.append(low)
            continue

        #remove all low which are taken by another low    
        for i in list_low_not_taken:
            if i > low:
                list_low_not_taken.remove(i)
                continue
        list_low_not_taken.append(low)
    
    #check 2LQ
    for i in list_low_not_taken:
        if i > _2LQ_candel_low:
            counter+=1
    if counter>=1:
        return True
    else:
        return False

def Bearish_2LQ_check(df):
    candel_highs=df['high'].iloc[:-2]
    _2LQ_candel_high=df['high'].iloc[-2]
    list_highs_not_taken=[]
    counter=0

    for high in candel_highs:
     
        if not list_highs_not_taken:
            list_highs_not_taken.append(high)
            continue
    
    # remove all high which are taken by another high
        for i in list_highs_not_taken:
            if i < high:
                list_highs_not_taken.remove(i)        
        list_highs_not_taken.append(high)

    # check  2LQ        
    for i in list_highs_not_taken:
        if i < _2LQ_candel_high:
            counter+=1
    if counter>=1:
        return True
    else:
        return False

def _2LQ_(shorlisted_pair):
    _2LQ_pairs_dict={}
    for pair,direction in shorlisted_pair.items():
        data = client.time_series(symbol=pair,interval="1day",outputsize="30")
        sleep(10)
        df=data.as_pandas()
        if df is not None:
            df.index = pd.to_datetime(df.index)
            df= df.sort_index()
            df= df[df.index.dayofweek < 5]
            df= df.astype(float)
            if direction =="| Bullish--C2 |":
                result = Bullish_2LQ_check(df)
                if result:
                    _2LQ_pairs_dict[pair]=direction
            if direction =="| Bearish--C2 |":
                result = Bearish_2LQ_check(df)
                if result:
                    _2LQ_pairs_dict[pair]=direction
    return _2LQ_pairs_dict

       


def message(swing_point_pairs,_2LQ_pairs) -> str:
    Est_time = datetime.now(ZoneInfo("America/New_York")).strftime("%d / %m / %Y - %H : %M EST")
    SP_lines = ""
    _2LQ_lines=""
    for pair, direction in swing_point_pairs.items():
        SP_lines += f"📌 {pair}  —  {direction}\n"
    for pair, direction in _2LQ_pairs.items():
        _2LQ_lines += f"📌 {pair}  —  {direction}\n"
    msg = (
        f"<b>⚡ SWING POINT SCANNER</b>\n"
        f"⏰ {Est_time}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"=======Swing point========\n"
        f"{SP_lines}"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"=======2LQ========\n"
        f"{_2LQ_lines}"
        f"━━━━━━━━━━━━━━━━━━\n"
    )
    return msg


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



def main():
    dict1=process_create()
    dict2=_2LQ_(dict1)
    _2LQ_pairs = dict(dict1.items() & dict2.items())
    swing_point_pairs = dict(dict1.items() - dict2.items())
    Est_time = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d %H:%M EST")
    if not swing_point_pairs and not _2LQ_pairs:
        send_telegram(f"{Est_time} : No Swing Point Found ")
        return
    
    msg=message(swing_point_pairs,_2LQ_pairs)
    send_telegram(msg)


main()