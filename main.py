import os
import json
import requests
import pandas as pd
import ccxt
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import jdatetime

# --- تنظیمات ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
TOOBIT_API_KEY = os.environ.get("TOOBIT_API_KEY")
TOOBIT_SECRET = os.environ.get("TOOBIT_SECRET")

SYMBOLS = [
    "BTC-SWAP-USDT", "ETH-SWAP-USDT", "SOL-SWAP-USDT", "XRP-SWAP-USDT",
    "ADA-SWAP-USDT", "DOGE-SWAP-USDT", "BNB-SWAP-USDT", "AVAX-SWAP-USDT",
    "LINK-SWAP-USDT", "DOT-SWAP-USDT", "LTC-SWAP-USDT", "TON-SWAP-USDT",
    "UNI-SWAP-USDT", "AAVE-SWAP-USDT", "NEAR-SWAP-USDT", "SUI-SWAP-USDT",
    "APT-SWAP-USDT", "ARB-SWAP-USDT", "ATOM-SWAP-USDT", "FIL-SWAP-USDT",
    "TIA-SWAP-USDT", "JUP-SWAP-USDT", "ENA-SWAP-USDT", "WIF-SWAP-USDT",
    "INJ-SWAP-USDT"
]

# نام فایل‌ها با پسوند v20 برای جلوگیری از تداخل با ریپازیتوری اصلی
HEARTBEAT_FILE = "server_messages_v20.json" 
SIGNALS_FILE = "last_signals_v20.json" 
MAX_HEARTBEATS = 4
MAX_SIGNALS_PER_CYCLE = 3  # حداکثر تعداد سیگنال در هر چرخه

# --- ابزارهای عمومی ---
def get_iran_time():
    now = datetime.now(ZoneInfo("Asia/Tehran"))
    date_gregorian = now.strftime("%Y-%m-%d")
    now_jalali = jdatetime.datetime.fromgregorian(datetime=now)
    date_jalali = now_jalali.strftime("%Y/%m/%d")
    time_str = now.strftime("%H:%M:%S")
    return date_gregorian, date_jalali, time_str

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={"chat_id": CHAT_ID, "text": message}, timeout=10)
        if r.status_code == 200:
            return r.json().get("result", {}).get("message_id")
    except Exception as e:
        print(f"⚠️ خطا در ارسال تلگرام: {e}")
    return None

def delete_telegram(message_id):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "message_id": message_id}, timeout=10)
    except Exception as e:
        print(f"⚠️ خطا در حذف پیام: {e}")

# --- Heartbeat ---
def load_heartbeat_ids():
    try:
        with open(HEARTBEAT_FILE, "r") as f:
            return json.load(f).get("message_ids", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_heartbeat_ids(ids):
    with open(HEARTBEAT_FILE, "w") as f:
        json.dump({"message_ids": ids}, f)

def send_heartbeat():
    date_gregorian, date_jalali, time_str = get_iran_time()
    msg = f"""🖥️ [V20] سرور آنلاین
━━━━━━━━━━━━━━━━━
📅 تاریخ شمسی: {date_jalali}
📅 تاریخ میلادی: {date_gregorian}
⏰ ساعت: {time_str}
━━━━━━━━━━━━━━━━━"""

    ids = load_heartbeat_ids()
    new_id = send_telegram(msg)

    if new_id:
        ids.append(new_id)
        while len(ids) > MAX_HEARTBEATS:
            old_id = ids.pop(0)
            delete_telegram(old_id)
        save_heartbeat_ids(ids)

# --- مدیریت معاملات باز و بسته ---
def load_signals():
    try:
        with open(SIGNALS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_signals(data):
    with open(SIGNALS_FILE, "w") as f:
        json.dump(data, f)

def update_open_trades(exchange):
    signals = load_signals()
    updated = False
    date_gregorian, date_jalali, time_str = get_iran_time()
    
    for symbol, data in list(signals.items()):
        if data.get("status") == "OPEN":
            try:
                ticker = exchange.fetch_ticker(symbol)
                current_price = ticker['last']
                
                entry = data['entry']
                tp = data['tp']
                sl = data['sl']
                direction = data['direction']
                
                result = None
                
                if direction == "LONG":
                    if current_price >= tp: result = "TP"
                    elif current_price <= sl: result = "SL"
                elif direction == "SHORT":
                    if current_price <= tp: result = "TP"
                    elif current_price >= sl: result = "SL"
                
                if result:
                    signals[symbol]['status'] = "CLOSED"
                    signals[symbol]['result'] = result
                    updated = True
                    
                    emoji = "🎯" if result == "TP" else "🛑"
                    title = "حد سود (TP) لمس شد" if result == "TP" else "حد ضرر (SL) لمس شد"

                    print(f"{emoji} {symbol} {direction} hit {result} at {current_price}")
                    
                    close_msg = f"""{emoji} [V20] بسته شدن معامله
━━━━━━━━━━━━━━━━━
📌 نماد: {symbol}
📊 جهت: {direction}
🏁 نتیجه: {title}
💰 قیمت بسته شدن: {format_number(current_price)}
🚪 قیمت ورود: {format_number(entry)}
━━━━━━━━━━━━━━━━━
📅 تاریخ شمسی: {date_jalali}
📅 تاریخ میلادی: {date_gregorian}
⏰ ساعت: {time_str}
━━━━━━━━━━━━━━━━━"""
                    send_telegram(close_msg)

            except Exception as e:
                print(f"⚠️ خطا در بررسی {symbol}: {e}")
                continue
                
    if updated:
        save_signals(signals)

# --- داده و تحلیل ---
def create_exchange():
    return ccxt.toobit({
        'apiKey': TOOBIT_API_KEY,
        'secret': TOOBIT_SECRET,
        'enableRateLimit': True,
    })

def fetch_ohlcv(exchange, symbol, timeframe, limit=100):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    return df

def calculate_indicators(df):
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()

    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr'] = tr.rolling(window=14).mean()

    return df

def get_btc_1h_trend(exchange):
    """روند بیت‌کوین در تایم 1 ساعته را برمی‌گرداند"""
    try:
        df_btc = fetch_ohlcv(exchange, "BTC-SWAP-USDT", '1h', 100)
        df_btc = calculate_indicators(df_btc)
        last_btc = df_btc.iloc[-1]
        
        if last_btc['ema9'] > last_btc['ema21']:
            return "LONG"
        elif last_btc['ema9'] < last_btc['ema21']:
            return "SHORT"
        else:
            return "NONE"
    except Exception as e:
        print(f"⚠️ خطا در دریافت روند بیت‌کوین: {e}")
        return "UNKNOWN"

def analyze(symbol, exchange):
    # تایم 1 ساعته برای تشخیص کراس و روند
    df_1h = fetch_ohlcv(exchange, symbol, '1h', 100)
    df_1h = calculate_indicators(df_1h)
    last_1h = df_1h.iloc[-1]
    prev_1h = df_1h.iloc[-2]

    # تایم 15 دقیقه برای تایید روند و پیدا کردن نقطه پولبک
    df_15m = fetch_ohlcv(exchange, symbol, '15m', 100)
    df_15m = calculate_indicators(df_15m)
    last_15m = df_15m.iloc[-1]

    current_price = last_15m['close']
    ema9_15m = last_15m['ema9']
    atr = last_15m['atr']

    # شرط کراس در تایم 1 ساعته (لحظه کراس)
    cross_long_1h = (prev_1h['ema9'] <= prev_1h['ema21']) and (last_1h['ema9'] > last_1h['ema21'])
    cross_short_1h = (prev_1h['ema9'] >= prev_1h['ema21']) and (last_1h['ema9'] < last_1h['ema21'])
    
    # تایید روند در تایم 1 ساعته
    trend_long_1h = last_1h['ema9'] > last_1h['ema21']
    trend_short_1h = last_1h['ema9'] < last_1h['ema21']

    # تایید روند در تایم 15 دقیقه
    trend_long_15m = last_15m['ema9'] > last_15m['ema21']
    trend_short_15m = last_15m['ema9'] < last_15m['ema21']

    print(f"  [DEBUG 1H] Cross LONG: {cross_long_1h} | Cross SHORT: {cross_short_1h} | Trend: {'LONG' if trend_long_1h else 'SHORT'}")
    print(f"  [DEBUG 15m] EMA9: {ema9_15m:.4f} | Price: {current_price:.4f} | Trend: {'LONG' if trend_long_15m else 'SHORT'}")

    signal = None
    sl = tp = None
    limit_price = None

    # استراتژی: کراس 1 ساعته + تایید 15 دقیقه + صبر برای پولبک
    if cross_long_1h and trend_long_15m:
        # شرط پولبک: قیمت نباید بیشتر از نیم برابر ATR از EMA9 فاصله گرفته باشد
        if current_price <= ema9_15m + (atr * 0.5):
            signal = "LONG"
            limit_price = ema9_15m
            sl = limit_price - (atr * 1.5)
            tp = limit_price + (atr * 3.0)

    elif cross_short_1h and trend_short_15m:
        if current_price >= ema9_15m - (atr * 0.5):
            signal = "SHORT"
            limit_price = ema9_15m
            sl = limit_price + (atr * 1.5)
            tp = limit_price - (atr * 3.0)

    return signal, current_price, limit_price, sl, tp, atr

def format_number(value):
    if value >= 1000:
        return f"{value:.2f}"
    elif value >= 1:
        return f"{value:.4f}"
    else:
        return f"{value:.6f}"

# --- اجرای اصلی ---
if __name__ == "__main__":
    print("=" * 50)
    print("Starting V20 bot cycle (Pullback Strategy)...")

    send_heartbeat()
    print("✅ V20 Heartbeat sent.")

    exchange = create_exchange()
    date_gregorian, date_jalali, time_str = get_iran_time()

    print("🔍 Checking open trades...")
    update_open_trades(exchange)
    signals_data = load_signals()

    # فیلتر بیت‌کوین 1 ساعته
    btc_trend = get_btc_1h_trend(exchange)
    print(f"🌍 BTC 1H Trend: {btc_trend}")

    signals_sent_this_cycle = 0

    for symbol in SYMBOLS:
        try:
            print(f"--- Checking {symbol} ---")
            
            if symbol in signals_data and signals_data[symbol].get("status") == "OPEN":
                print(f"⏳ {symbol} has an OPEN trade. Skipping.")
                continue

            signal, current_price, limit_price, sl, tp, atr = analyze(symbol, exchange)

            if signal is None:
                print(f"{symbol} | Price: {current_price:.4f} | No valid setup or waiting for pullback.")
                continue

            if btc_trend != "UNKNOWN" and btc_trend != "NONE" and signal != btc_trend:
                print(f"🚫 {symbol} signal {signal} rejected. BTC 1H trend is {btc_trend}.")
                continue

            if signals_sent_this_cycle >= MAX_SIGNALS_PER_CYCLE:
                print(f"🛑 Reached max signals per cycle ({MAX_SIGNALS_PER_CYCLE}). Skipping {symbol}.")
                continue

            if signal == "LONG":
                rr = (tp - limit_price) / (limit_price - sl)
                emoji = "🟢"
            else:
                rr = (limit_price - tp) / (sl - limit_price)
                emoji = "🔴"

            msg = f"""{emoji} [V20] سیگنال {signal} (Pullback)
━━━━━━━━━━━━━━━━━
📌 نماد: {symbol}
💵 قیمت لحظه‌ای: {format_number(current_price)}
🎯 قیمت لیمیت (ورود): {format_number(limit_price)}
🎯 حد سود (TP): {format_number(tp)}
🛑 حد ضرر (SL): {format_number(sl)}
📊 نسبت R:R: 1:{rr:.1f}
📉 ATR: {format_number(atr)}
━━━━━━━━━━━━━━━━━
📅 تاریخ شمسی: {date_jalali}
📅 تاریخ میلادی: {date_gregorian}
⏰ ساعت: {time_str}
━━━━━━━━━━━━━━━━━"""

            send_telegram(msg)
            
            signals_data[symbol] = {
                "direction": signal,
                "entry": limit_price,
                "tp": tp,
                "sl": sl,
                "status": "OPEN",
                "time": datetime.now().isoformat()
            }
            save_signals(signals_data)
            signals_sent_this_cycle += 1
            print(f"✅ {signal} signal for {symbol} sent! Limit: {limit_price} ({signals_sent_this_cycle}/{MAX_SIGNALS_PER_CYCLE})")

        except Exception as e:
            print(f"⚠️ خطا در {symbol}: {e}")
            continue

    print("V20 Analysis complete.")
    print("=" * 50)
