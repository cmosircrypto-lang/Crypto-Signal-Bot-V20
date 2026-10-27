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
    # --- Core Majors (Top Liquidity) ---
    "BTC-SWAP-USDT", "ETH-SWAP-USDT", "SOL-SWAP-USDT", "XRP-SWAP-USDT", 
    "BNB-SWAP-USDT", "DOGE-SWAP-USDT", "ADA-SWAP-USDT", "TRX-SWAP-USDT",
    "AVAX-SWAP-USDT", "LINK-SWAP-USDT", "DOT-SWAP-USDT", "LTC-SWAP-USDT",
    "BCH-SWAP-USDT", "TON-SWAP-USDT", "SUI-SWAP-USDT", "NEAR-SWAP-USDT",
    "APT-SWAP-USDT", "ARB-SWAP-USDT", "OP-SWAP-USDT", "ATOM-SWAP-USDT",
    
    # --- High Volume / Popular Altcoins ---
    "UNI-SWAP-USDT", "AAVE-SWAP-USDT", "FIL-SWAP-USDT", "INJ-SWAP-USDT",
    "TIA-SWAP-USDT", "JUP-SWAP-USDT", "ENA-SWAP-USDT", "WIF-SWAP-USDT",
    "1000PEPE-SWAP-USDT", "1000SHIB-SWAP-USDT", "WLD-SWAP-USDT", "SEI-SWAP-USDT",
    "RUNE-SWAP-USDT", "LDO-SWAP-USDT", "STX-SWAP-USDT", "IMX-SWAP-USDT",
    "HBAR-SWAP-USDT", "ICP-SWAP-USDT", "ETC-SWAP-USDT", "XLM-SWAP-USDT",
    
    # --- DeFi & Layer 2 ---
    "CRV-SWAP-USDT", "SNX-SWAP-USDT",
    "COMP-SWAP-USDT", "SUSHI-SWAP-USDT", "1INCH-SWAP-USDT", "GRT-SWAP-USDT",
    "DYDX-SWAP-USDT", "GMX-SWAP-USDT", "PENDLE-SWAP-USDT", "ONDO-SWAP-USDT",
    "JTO-SWAP-USDT", "PYTH-SWAP-USDT", "STRK-SWAP-USDT", "MANTA-SWAP-USDT",
    
    # --- Meme & Community Coins ---
    "1000BONK-SWAP-USDT", "1000FLOKI-SWAP-USDT", "MEME-SWAP-USDT", "ORDI-SWAP-USDT",
    "1000SATS-SWAP-USDT", "1000RATS-SWAP-USDT", "POPCAT-SWAP-USDT",
    "BRETT-SWAP-USDT", "TURBO-SWAP-USDT", "1000000MOG-SWAP-USDT", "DOGS-SWAP-USDT",
    
    # --- AI, Gaming & Metaverse ---
    "FET-SWAP-USDT", "TAO-SWAP-USDT",
    "AKT-SWAP-USDT", "ILV-SWAP-USDT",
    "AXS-SWAP-USDT", "SAND-SWAP-USDT", "MANA-SWAP-USDT", "GALA-SWAP-USDT",
    
    # --- Infrastructure & Others ---
    "ALGO-SWAP-USDT", "VET-SWAP-USDT", "EGLD-SWAP-USDT", "FLOW-SWAP-USDT",
    "KAVA-SWAP-USDT", "ROSE-SWAP-USDT", "KAS-SWAP-USDT",
    "THETA-SWAP-USDT", "CHZ-SWAP-USDT", "ENJ-SWAP-USDT", "ZIL-SWAP-USDT",
    "ONE-SWAP-USDT", "QTUM-SWAP-USDT", "IOTA-SWAP-USDT", "NEO-SWAP-USDT"
]

HEARTBEAT_FILE = "server_messages_v20.json" 
SIGNALS_FILE = "last_signals_v20.json" 
MAX_HEARTBEATS = 4
MAX_SIGNALS_PER_CYCLE = 3

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
    msg = f"""🖥️ [V20] سرور آنلاین (Price Action)
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

# --- مدیریت معاملات ---
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
    if updated: save_signals(signals)

# --- داده و تحلیل ---
def create_exchange():
    return ccxt.toobit({'apiKey': TOOBIT_API_KEY, 'secret': TOOBIT_SECRET, 'enableRateLimit': True})

def fetch_ohlcv(exchange, symbol, timeframe, limit=100):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    return pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

def calculate_atr(df):
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr'] = tr.rolling(window=14).mean()
    return df

def get_btc_trend(exchange):
    try:
        df_4h = fetch_ohlcv(exchange, "BTC-SWAP-USDT", '4h', 100)
        df_4h['ema9'] = df_4h['close'].ewm(span=9, adjust=False).mean()
        df_4h['ema21'] = df_4h['close'].ewm(span=21, adjust=False).mean()
        last_4h = df_4h.iloc[-1]
        
        df_1h = fetch_ohlcv(exchange, "BTC-SWAP-USDT", '1h', 100)
        df_1h['ema9'] = df_1h['close'].ewm(span=9, adjust=False).mean()
        df_1h['ema21'] = df_1h['close'].ewm(span=21, adjust=False).mean()
        last_1h = df_1h.iloc[-1]

        trend_4h = "LONG" if last_4h['ema9'] > last_4h['ema21'] else "SHORT" if last_4h['ema9'] < last_4h['ema21'] else "NONE"
        trend_1h = "LONG" if last_1h['ema9'] > last_1h['ema21'] else "SHORT" if last_1h['ema9'] < last_1h['ema21'] else "NONE"
        
        return trend_4h, trend_1h
    except Exception as e:
        print(f"⚠️ خطا در دریافت روند بیت‌کوین: {e}")
        return "UNKNOWN", "UNKNOWN"

def analyze(symbol, exchange):
    df_4h = fetch_ohlcv(exchange, symbol, '4h', 100)
    df_4h['ema9'] = df_4h['close'].ewm(span=9, adjust=False).mean()
    df_4h['ema21'] = df_4h['close'].ewm(span=21, adjust=False).mean()
    last_4h = df_4h.iloc[-1]

    df_15m = fetch_ohlcv(exchange, symbol, '15m', 100)
    df_15m = calculate_atr(df_15m)
    
    last = df_15m.iloc[-1]
    prev = df_15m.iloc[-2]
    
    entry_price = last['close']
    atr = last['atr']

    # فیلتر حجم
    avg_volume = df_15m['volume'].rolling(window=20).mean().iloc[-1]
    current_volume = df_15m['volume'].iloc[-1]
    volume_condition = current_volume > avg_volume

    # تشخیص روند 4 ساعته (برای تاییدیه)
    trend_long_4h = last_4h['ema9'] > last_4h['ema21']
    trend_short_4h = last_4h['ema9'] < last_4h['ema21']

    # محاسبه اندازه بدنه و سایه‌ها
    body_size = abs(last['close'] - last['open'])
    upper_wick = last['high'] - max(last['close'], last['open'])
    lower_wick = min(last['close'], last['open']) - last['low']
    
    # 1. الگوهای کندلی
    is_strong_bullish = (last['close'] > last['open']) and (body_size > (upper_wick + lower_wick) * 1.5)
    is_strong_bearish = (last['close'] < last['open']) and (body_size > (upper_wick + lower_wick) * 1.5)
    
    bullish_engulfing = (prev['close'] < prev['open']) and (last['close'] > last['open']) and (last['close'] > prev['open']) and (last['open'] < prev['close'])
    bearish_engulfing = (prev['close'] > prev['open']) and (last['close'] < last['open']) and (last['close'] < prev['open']) and (last['open'] > prev['close'])
    
    hammer = (lower_wick > body_size * 2) and (upper_wick < body_size * 0.5)
    shooting_star = (upper_wick > body_size * 2) and (lower_wick < body_size * 0.5)

    print(f"  [DEBUG 4H] Trend: {'LONG' if trend_long_4h else 'SHORT'}")
    print(f"  [DEBUG 15m] BullEngulf: {bullish_engulfing} | BearEngulf: {bearish_engulfing} | Hammer: {hammer} | ShootingStar: {shooting_star}")
    print(f"  [DEBUG Vol] Current: {current_volume:.2f} | Avg: {avg_volume:.2f} | VolOK: {volume_condition}")

    signal = None
    sl = tp = None

    # شرط LONG: روند 4 ساعته صعودی + الگوی بولیش + حجم کافی
    if trend_long_4h:
        if (bullish_engulfing or is_strong_bullish or hammer) and volume_condition:
            signal = "LONG"
            sl = entry_price - (atr * 1.5)
            tp = entry_price + (atr * 3.0)

    # شرط SHORT: روند 4 ساعته نزولی + الگوی بیریش + حجم کافی
    elif trend_short_4h:
        if (bearish_engulfing or is_strong_bearish or shooting_star) and volume_condition:
            signal = "SHORT"
            sl = entry_price + (atr * 1.5)
            tp = entry_price - (atr * 3.0)

    return signal, entry_price, sl, tp, atr, volume_condition

def format_number(value):
    if value >= 1000: return f"{value:.2f}"
    elif value >= 1: return f"{value:.4f}"
    else: return f"{value:.6f}"

# --- اجرای اصلی ---
if __name__ == "__main__":
    print("=" * 50)
    print("Starting V20 bot cycle (Price Action + Volume)...")

    send_heartbeat()
    print("✅ V20 Heartbeat sent.")

    exchange = create_exchange()
    date_gregorian, date_jalali, time_str = get_iran_time()

    print("🔍 Checking open trades...")
    update_open_trades(exchange)
    signals_data = load_signals()

    btc_trend_4h, btc_trend_1h = get_btc_trend(exchange)
    print(f"🌍 BTC 4H Trend: {btc_trend_4h} | BTC 1H Trend: {btc_trend_1h}")

    signals_sent_this_cycle = 0

    for symbol in SYMBOLS:
        try:
            print(f"--- Checking {symbol} ---")
            
            if symbol in signals_data and signals_data[symbol].get("status") == "OPEN":
                print(f"⏳ {symbol} has an OPEN trade. Skipping.")
                continue

            signal, entry, sl, tp, atr, vol_ok = analyze(symbol, exchange)

            if signal is None:
                print(f"{symbol} | Price: {entry} | No valid setup (or volume low).")
                continue

            # فیلتر بیت‌کوین
            if btc_trend_4h != "UNKNOWN" and btc_trend_4h != "NONE" and signal != btc_trend_4h:
                print(f"🚫 {symbol} signal {signal} rejected. BTC 4H trend is {btc_trend_4h}.")
                continue
            if btc_trend_1h != "UNKNOWN" and btc_trend_1h != "NONE" and signal != btc_trend_1h:
                print(f"🚫 {symbol} signal {signal} rejected. BTC 1H trend is {btc_trend_1h}.")
                continue

            if signals_sent_this_cycle >= MAX_SIGNALS_PER_CYCLE:
                print(f"🛑 Reached max signals per cycle ({MAX_SIGNALS_PER_CYCLE}). Skipping {symbol}.")
                continue

            if signal == "LONG":
                rr = (tp - entry) / (entry - sl)
                emoji = "🟢"
            else:
                rr = (entry - tp) / (sl - entry)
                emoji = "🔴"

            msg = f"""{emoji} [V20] سیگنال {signal} (Price Action)
━━━━━━━━━━━━━━━━━
📌 نماد: {symbol}
💰 قیمت ورود: {format_number(entry)}
🎯 حد سود (TP): {format_number(tp)}
🛑 حد ضرر (SL): {format_number(sl)}
📊 نسبت R:R: 1:{rr:.1f}
📉 ATR: {format_number(atr)}
📊 Volume: {current_volume:.2f} (Avg: {avg_volume:.2f})
━━━━━━━━━━━━━━━━━
📅 تاریخ شمسی: {date_jalali}
📅 تاریخ میلادی: {date_gregorian}
⏰ ساعت: {time_str}
━━━━━━━━━━━━━━━━━"""

            send_telegram(msg)
            
            signals_data[symbol] = {
                "direction": signal,
                "entry": entry,
                "tp": tp,
                "sl": sl,
                "status": "OPEN",
                "time": datetime.now().isoformat()
            }
            save_signals(signals_data)
            signals_sent_this_cycle += 1
            print(f"✅ {signal} signal for {symbol} sent! ({signals_sent_this_cycle}/{MAX_SIGNALS_PER_CYCLE})")

        except Exception as e:
            print(f"⚠️ خطا در {symbol}: {e}")
            continue

    print("V20 Analysis complete.")
    print("=" * 50)