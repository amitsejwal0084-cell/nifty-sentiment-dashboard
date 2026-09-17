# ============================================================================
# संगम — मल्टी-इंडिकेटर कॉन्फ्लुएंस पैनल
# ============================================================================
# इसे अपने app.py में यहां पेस्ट करें:
#   "Market Setup" सेक्शन के आख़िर में जो लाइन है —
#     st.caption("यह केवल market-data analysis है; कोई automatic order execute नहीं होता।")
#   — ठीक उसके बाद, और "OPTION CHAIN" वाले st.divider() से पहले।
#
# यह आपके मौजूदा `kite`, `nifty_token`, और `get_historical_data()` को
# सीधे इस्तेमाल करता है — कोई नया backend, कोई नया login, कोई CORS सेटअप नहीं चाहिए।
# ============================================================================

st.divider()
st.subheader("🔱 संगम — मल्टी-इंडिकेटर कॉन्फ्लुएंस सिग्नल")

def calculate_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def calculate_macd(series):
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    return macd_line, signal_line

def calculate_bollinger(series, period=20, mult=2):
    mid = series.rolling(period).mean()
    sd = series.rolling(period).std()
    return mid, mid + mult * sd, mid - mult * sd

def calculate_supertrend(df, period=10, mult=3):
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1
    ).max(axis=1)
    atr = tr.ewm(alpha=1 / period, adjust=False).mean()
    hl2 = (high + low) / 2
    basic_upper = hl2 + mult * atr
    basic_lower = hl2 - mult * atr
    final_upper = basic_upper.copy()
    final_lower = basic_lower.copy()
    for i in range(1, len(df)):
        if basic_upper.iloc[i] < final_upper.iloc[i - 1] or close.iloc[i - 1] > final_upper.iloc[i - 1]:
            final_upper.iloc[i] = basic_upper.iloc[i]
        else:
            final_upper.iloc[i] = final_upper.iloc[i - 1]
        if basic_lower.iloc[i] > final_lower.iloc[i - 1] or close.iloc[i - 1] < final_lower.iloc[i - 1]:
            final_lower.iloc[i] = basic_lower.iloc[i]
        else:
            final_lower.iloc[i] = final_lower.iloc[i - 1]
    trend = pd.Series(index=df.index, dtype=int)
    trend.iloc[0] = 1 if close.iloc[0] > final_upper.iloc[0] else -1
    for i in range(1, len(df)):
        if trend.iloc[i - 1] == 1:
            trend.iloc[i] = -1 if close.iloc[i] < final_lower.iloc[i] else 1
        else:
            trend.iloc[i] = 1 if close.iloc[i] > final_upper.iloc[i] else -1
    return trend

if nifty_token is None:
    st.warning("NIFTY instrument token नहीं मिला — संगम पैनल नहीं दिखाया जा सकता।")
else:
    # स्विंग-स्टाइल indicators (EMA50, Supertrend) के लिए daily candles चाहिए,
    # इसलिए ऊपर के 5-मिनट वाले technical_df से अलग, रोज़ाना डेटा अलग से लाया जा रहा है
    daily_df = get_historical_data(nifty_token, interval="day", days=200)

    if daily_df.empty or len(daily_df) < 55:
        st.warning("संगम पैनल के लिए कम से कम ~60 दिनों का daily candle डेटा चाहिए, जो अभी उपलब्ध नहीं है।")
    else:
        daily_df["close"] = pd.to_numeric(daily_df["close"], errors="coerce")
        daily_df["high"] = pd.to_numeric(daily_df["high"], errors="coerce")
        daily_df["low"] = pd.to_numeric(daily_df["low"], errors="coerce")
        daily_df["volume"] = pd.to_numeric(daily_df["volume"], errors="coerce")

        close = daily_df["close"]
        ema20 = calculate_ema(close, 20)
        ema50 = calculate_ema(close, 50)
        rsi14 = calculate_rsi(close, 14)  # आपके app.py में पहले से मौजूद फंक्शन दोबारा इस्तेमाल हो रहा है
        macd_line, signal_line = calculate_macd(close)
        bb_mid, bb_upper, bb_lower = calculate_bollinger(close, 20, 2)
        st_trend = calculate_supertrend(daily_df, 10, 3)

        last_close = close.iloc[-1]
        indicators = []

        # EMA क्रॉसओवर
        vote = 0
        if last_close > ema20.iloc[-1] > ema50.iloc[-1]:
            vote = 1
        elif last_close < ema20.iloc[-1] < ema50.iloc[-1]:
            vote = -1
        indicators.append(("EMA 20/50", f"₹{ema20.iloc[-1]:,.1f} / ₹{ema50.iloc[-1]:,.1f}", vote))

        # RSI
        vote = 0
        r = rsi14.iloc[-1]
        if pd.notna(r):
            if r < 30:
                vote = 1
            elif r > 70:
                vote = -1
        indicators.append(("RSI (14)", f"{r:.1f}" if pd.notna(r) else "—", vote))

        # MACD
        vote = 0
        m, s = macd_line.iloc[-1], signal_line.iloc[-1]
        if pd.notna(m) and pd.notna(s):
            vote = 1 if m > s else (-1 if m < s else 0)
        indicators.append(("MACD", f"{m:.2f} vs {s:.2f}" if pd.notna(m) else "—", vote))

        # Bollinger
        vote = 0
        if pd.notna(bb_upper.iloc[-1]):
            if last_close <= bb_lower.iloc[-1]:
                vote = 1
            elif last_close >= bb_upper.iloc[-1]:
                vote = -1
        indicators.append(("Bollinger Bands", f"₹{bb_lower.iloc[-1]:,.1f} – ₹{bb_upper.iloc[-1]:,.1f}" if pd.notna(bb_upper.iloc[-1]) else "—", vote))

        # Supertrend
        t = st_trend.iloc[-1]
        vote = 1 if t == 1 else -1
        indicators.append(("Supertrend", "तेजी रुझान" if t == 1 else "मंदी रुझान", vote))

        # वॉल्यूम पुष्टि
        vote = 0
        vol_note = "—"
        avg_vol20 = daily_df["volume"].rolling(20).mean().iloc[-1]
        last_vol = daily_df["volume"].iloc[-1]
        price_chg5 = close.iloc[-1] - close.iloc[-6]
        if pd.notna(avg_vol20) and avg_vol20 > 0:
            ratio = last_vol / avg_vol20 * 100
            vol_note = f"{ratio:.0f}% औसत वॉल्यूम"
            if last_vol > avg_vol20 * 1.2:
                vote = 1 if price_chg5 > 0 else (-1 if price_chg5 < 0 else 0)
        indicators.append(("वॉल्यूम पुष्टि", vol_note, vote))

        score = sum(v for _, _, v in indicators)
        confidence = abs(score) / 6 * 100

        cols = st.columns(6)
        for col, (name, value_str, vote) in zip(cols, indicators):
            with col:
                badge = "🟢 तेजी" if vote > 0 else ("🔴 मंदी" if vote < 0 else "⚪ न्यूट्रल")
                st.metric(name, value_str, badge)

        st.progress(min(100, int(confidence)))

        if score >= 2:
            st.success(f"🟢 बुलिश बायस — स्कोर {score:+d}/6 · {confidence:.0f}% इंडिकेटर सहमत")
        elif score <= -2:
            st.error(f"🔴 बेयरिश बायस — स्कोर {score:+d}/6 · {confidence:.0f}% इंडिकेटर सहमत")
        else:
            st.info(f"⚪ न्यूट्रल / मिश्रित संकेत — स्कोर {score:+d}/6 · {confidence:.0f}% इंडिकेटर सहमत")

        st.caption(
            "⚠️ यह किसी भी अन्य इंडिकेटर सिस्टम की तरह 100% सटीक नहीं है — यह सिर्फ छह लोकप्रिय "
            "indicators की आपसी सहमति (confluence) दिखाता है, गारंटीशुदा सिग्नल नहीं। "
            "निवेश सलाह नहीं है; अपने जोखिम पर ट्रेड करें।"
        )
        
