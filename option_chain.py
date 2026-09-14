import streamlit as st
import pandas as pd
from datetime import date, timedelta
from growwapi import GrowwAPI


def get_groww_client():
    token = st.secrets.get("GROWW_ACCESS_TOKEN")

    if not token:
        raise Exception(
            "GROWW_ACCESS_TOKEN Streamlit Secrets में नहीं मिला।"
        )

    return GrowwAPI(token)


def check_groww_permissions():
    try:
        groww = get_groww_client()
        return groww.get_user_profile()
    except Exception as e:
        return {"error": str(e)}


def get_nearest_expiry():
    today = date.today()

    days = (1 - today.weekday()) % 7

    if days == 0:
        days = 7

    expiry = today + timedelta(days=days)

    return expiry.strftime("%Y-%m-%d")


def get_nifty_option_chain():
    groww = get_groww_client()

    expiry_date = get_nearest_expiry()

    st.info(f"📅 NIFTY Expiry: {expiry_date}")

    try:
        profile = groww.get_user_profile()

        if isinstance(profile, dict):
            segments = profile.get("active_segments")

            if segments is not None:
                st.write(
                    f"📌 Active Segments: {segments}"
                )

    except Exception as e:
        st.warning(
            f"⚠️ Groww Profile Check: {e}"
        )

    try:
        response = groww.get_option_chain(
            exchange=groww.EXCHANGE_NSE,
            underlying="NIFTY",
            expiry_date=expiry_date
        )

    except Exception as e:
        st.error(
            f"❌ Groww Option Chain API Error: {e}"
        )
        return pd.DataFrame(), None

    if not isinstance(response, dict):
        st.warning(
            "⚠️ Groww response का format सही नहीं है।"
        )
        return pd.DataFrame(), None

    spot = response.get("underlying_ltp")

    strikes = response.get("strikes", {})

    rows = []

    if isinstance(strikes, dict):

        for strike, sides in strikes.items():

            if not isinstance(sides, dict):
                continue

            for option_type in ("CE", "PE"):

                contract = sides.get(option_type)

                if not isinstance(contract, dict):
                    continue

                greeks = contract.get("greeks") or {}

                rows.append(
                    {
                        "strike_price": float(strike),
                        "option_type": option_type,
                        "trading_symbol": contract.get(
                            "trading_symbol"
                        ),
                        "ltp": contract.get("ltp"),
                        "open_interest": contract.get(
                            "open_interest", 0
                        ),
                        "volume": contract.get(
                            "volume", 0
                        ),
                        "iv": greeks.get("iv"),
                        "delta": greeks.get("delta"),
                        "gamma": greeks.get("gamma"),
                        "theta": greeks.get("theta"),
                        "vega": greeks.get("vega"),
                        "rho": greeks.get("rho"),
                    }
                )

    df = pd.DataFrame(rows)

    if df.empty:

        st.warning(
            "⚠️ Groww ने Option Chain data खाली भेजा।"
        )

        return df, spot

    st.success(
        f"✅ Groww Option Chain मिला — "
        f"{len(df)} contracts"
    )

    if spot is not None:
        spot = float(spot)

    return df, spot


def get_atm_option_chain(
    option_data,
    option_spot,
    strikes_each_side=4
):

    if option_data.empty or option_spot is None:
        return pd.DataFrame()

    df = option_data.copy()

    df["strike_price"] = pd.to_numeric(
        df["strike_price"],
        errors="coerce"
    )

    df = df.dropna(
        subset=["strike_price"]
    )

    atm = round(
        float(option_spot) / 50
    ) * 50

    low = atm - strikes_each_side * 50

    high = atm + strikes_each_side * 50

    return df[
        (df["strike_price"] >= low)
        &
        (df["strike_price"] <= high)
    ].copy()


def calculate_pcr(atm_data):

    if atm_data.empty:
        return None

    df = atm_data.copy()

    df["open_interest"] = pd.to_numeric(
        df["open_interest"],
        errors="coerce"
    ).fillna(0)

    option_type = (
        df["option_type"]
        .astype(str)
        .str.upper()
    )

    call_oi = df.loc[
        option_type == "CE",
        "open_interest"
    ].sum()

    put_oi = df.loc[
        option_type == "PE",
        "open_interest"
    ].sum()

    if call_oi == 0:
        return None

    pcr = put_oi / call_oi

    return round(float(pcr), 2)


def option_sentiment(atm_data):

    pcr = calculate_pcr(atm_data)

    if pcr is None:
        return "NO DATA", 50

    if pcr >= 1.20:
        return "BULLISH", 70

    if pcr <= 0.80:
        return "BEARISH", 30

    return "NEUTRAL", 50


def calculate_support_resistance(atm_data):

    if atm_data.empty:
        return None, None

    df = atm_data.copy()

    df["open_interest"] = pd.to_numeric(
        df["open_interest"],
        errors="coerce"
    ).fillna(0)

    option_type = (
        df["option_type"]
        .astype(str)
        .str.upper()
    )

    calls = df[
        option_type == "CE"
    ].copy()

    puts = df[
        option_type == "PE"
    ].copy()

    resistance = None
    support = None

    if not calls.empty:
        resistance = calls.loc[
            calls["open_interest"].idxmax(),
            "strike_price"
        ]

    if not puts.empty:
        support = puts.loc[
            puts["open_interest"].idxmax(),
            "strike_price"
        ]

    return support, resistance
