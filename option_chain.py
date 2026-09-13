import streamlit as st
import pandas as pd
from datetime import date, datetime
from growwapi import GrowwAPI


# =========================================================
# GROWW CLIENT
# =========================================================

def get_groww_client():
    try:
        token = st.secrets["GROWW_ACCESS_TOKEN"]

        if not token:
            return None

        return GrowwAPI(token)

    except Exception:
        return None


# =========================================================
# FIND NEAREST NIFTY EXPIRY
# =========================================================

def get_nearest_expiry(groww):

    today = date.today()

    try:
        # Current month
        response = groww.get_expiries(
            exchange=groww.EXCHANGE_NSE,
            underlying_symbol="NIFTY",
            year=today.year,
            month=today.month
        )

        expiries = response.get("expiries", [])

        future_expiries = [
            x for x in expiries
            if datetime.strptime(x, "%Y-%m-%d").date() >= today
        ]

        if future_expiries:
            return sorted(future_expiries)[0]

        # Next month
        if today.month == 12:
            next_year = today.year + 1
            next_month = 1
        else:
            next_year = today.year
            next_month = today.month + 1

        response = groww.get_expiries(
            exchange=groww.EXCHANGE_NSE,
            underlying_symbol="NIFTY",
            year=next_year,
            month=next_month
        )

        expiries = response.get("expiries", [])

        future_expiries = [
            x for x in expiries
            if datetime.strptime(x, "%Y-%m-%d").date() >= today
        ]

        if future_expiries:
            return sorted(future_expiries)[0]

    except Exception:
        return None

    return None


# =========================================================
# GET NIFTY OPTION CHAIN
# =========================================================

@st.cache_data(ttl=30)
def get_nifty_option_chain(expiry_date=None):

    try:

        groww = get_groww_client()

        if groww is None:
            return None

        # Automatically find nearest expiry
        if expiry_date is None:
            expiry_date = get_nearest_expiry(groww)

        if not expiry_date:
            return None

        data = groww.get_option_chain(
            exchange=groww.EXCHANGE_NSE,
            underlying="NIFTY",
            expiry_date=expiry_date
        )

        # Some API responses may contain payload
        if isinstance(data, dict):

            if "payload" in data and isinstance(data["payload"], dict):
                data = data["payload"]

        if not isinstance(data, dict):
            return None

        if "strikes" not in data:
            return None

        return data

    except Exception:
        return None


# =========================================================
# CONVERT OPTION CHAIN TO DATAFRAME
# =========================================================

def option_chain_to_dataframe(option_data):

    if not option_data:
        return pd.DataFrame()

    strikes = option_data.get("strikes", {})

    rows = []

    for strike, data in strikes.items():

        try:
            strike_price = float(strike)
        except Exception:
            continue

        ce = data.get("CE", {}) or {}
        pe = data.get("PE", {}) or {}

        ce_greeks = ce.get("greeks", {}) or {}
        pe_greeks = pe.get("greeks", {}) or {}

        rows.append({

            "Strike": strike_price,

            "CE_LTP": ce.get("ltp", 0),
            "CE_OI": ce.get("open_interest", 0),
            "CE_Volume": ce.get("volume", 0),
            "CE_IV": ce_greeks.get("iv", 0),
            "CE_Delta": ce_greeks.get("delta", 0),

            "PE_LTP": pe.get("ltp", 0),
            "PE_OI": pe.get("open_interest", 0),
            "PE_Volume": pe.get("volume", 0),
            "PE_IV": pe_greeks.get("iv", 0),
            "PE_Delta": pe_greeks.get("delta", 0),
        })

    df = pd.DataFrame(rows)

    if not df.empty:
        df = df.sort_values("Strike").reset_index(drop=True)

    return df


# =========================================================
# ATM ±4 STRIKES
# =========================================================

def get_atm_option_chain(option_data, window=4):

    df = option_chain_to_dataframe(option_data)

    if df.empty:
        return df

    underlying_ltp = option_data.get("underlying_ltp")

    if underlying_ltp is None:
        return df.head(9)

    # Find nearest ATM strike
    atm_index = (
        (df["Strike"] - float(underlying_ltp))
        .abs()
        .idxmin()
    )

    position = df.index.get_loc(atm_index)

    start = max(0, position - window)
    end = min(len(df), position + window + 1)

    atm_df = df.iloc[start:end].copy()

    atm_df["ATM"] = ""

    atm_df.loc[
        atm_df["Strike"] == df.loc[atm_index, "Strike"],
        "ATM"
    ] = "ATM"

    return atm_df


# =========================================================
# PCR CALCULATION
# =========================================================

def calculate_pcr(option_data):

    df = option_chain_to_dataframe(option_data)

    if df.empty:
        return None

    ce_oi = pd.to_numeric(
        df["CE_OI"],
        errors="coerce"
    ).fillna(0).sum()

    pe_oi = pd.to_numeric(
        df["PE_OI"],
        errors="coerce"
    ).fillna(0).sum()

    if ce_oi <= 0:
        return None

    return round(pe_oi / ce_oi, 2)


# =========================================================
# ATM PCR
# =========================================================

def calculate_atm_pcr(option_data, window=4):

    df = get_atm_option_chain(
        option_data,
        window
    )

    if df.empty:
        return None

    ce_oi = pd.to_numeric(
        df["CE_OI"],
        errors="coerce"
    ).fillna(0).sum()

    pe_oi = pd.to_numeric(
        df["PE_OI"],
        errors="coerce"
    ).fillna(0).sum()

    if ce_oi <= 0:
        return None

    return round(pe_oi / ce_oi, 2)


# =========================================================
# OPTION SENTIMENT SCORE
# =========================================================

def option_sentiment(option_data):

    df = get_atm_option_chain(
        option_data,
        window=4
    )

    if df.empty:
        return 50

    score = 50

    # -----------------------------------------
    # PCR SIGNAL
    # -----------------------------------------

    pcr = calculate_pcr(option_data)

    if pcr is not None:

        if pcr >= 1.20:
            score += 15

        elif pcr >= 1.05:
            score += 8

        elif pcr <= 0.80:
            score -= 15

        elif pcr <= 0.95:
            score -= 8

    # -----------------------------------------
    # OI SIGNAL
    # -----------------------------------------

    ce_oi = pd.to_numeric(
        df["CE_OI"],
        errors="coerce"
    ).fillna(0).sum()

    pe_oi = pd.to_numeric(
        df["PE_OI"],
        errors="coerce"
    ).fillna(0).sum()

    if ce_oi > 0:

        oi_ratio = pe_oi / ce_oi

        if oi_ratio > 1.15:
            score += 10

        elif oi_ratio < 0.85:
            score -= 10

    # -----------------------------------------
    # VOLUME SIGNAL
    # -----------------------------------------

    ce_volume = pd.to_numeric(
        df["CE_Volume"],
        errors="coerce"
    ).fillna(0).sum()

    pe_volume = pd.to_numeric(
        df["PE_Volume"],
        errors="coerce"
    ).fillna(0).sum()

    if ce_volume > 0 or pe_volume > 0:

        if pe_volume > ce_volume * 1.10:
            score += 5

        elif ce_volume > pe_volume * 1.10:
            score -= 5

    # -----------------------------------------
    # LIMIT SCORE
    # -----------------------------------------

    score = max(0, min(100, score))

    return int(score)


# =========================================================
# OPTION SENTIMENT LABEL
# =========================================================

def option_sentiment_label(score):

    if score >= 65:
        return "Bullish"

    elif score <= 35:
        return "Bearish"

    return "Neutral"


# =========================================================
# SUPPORT / RESISTANCE FROM OI
# =========================================================

def get_oi_support_resistance(option_data):

    df = option_chain_to_dataframe(option_data)

    if df.empty:
        return None, None

    try:

        # Highest Put OI = possible support
        support_row = df.loc[
            df["PE_OI"].idxmax()
        ]

        # Highest Call OI = possible resistance
        resistance_row = df.loc[
            df["CE_OI"].idxmax()
        ]

        support = support_row["Strike"]
        resistance = resistance_row["Strike"]

        return support, resistance

    except Exception:
        return None, None
