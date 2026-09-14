import streamlit as st
import pandas as pd
from datetime import date, timedelta
from growwapi import GrowwAPI


def get_groww_client():
    token = st.secrets.get("GROWW_ACCESS_TOKEN")

    if not token:
        raise Exception("GROWW_ACCESS_TOKEN Streamlit Secrets में नहीं मिला।")

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

    # Groww profile / permission test
try:
    profile = groww.get_user_profile()

    if isinstance(profile, dict):
        segments = profile.get("active_segments")

        if segments is not None:
            st.write(f"📌 Active Segments: {segments}")

        if profile.get("client_id"):
            st.write("✅ Groww account profile connected")

except Exception as e:
    st.warning(f"⚠️ Groww Profile Check: {e}")
    # Option Chain
    try:

        response = groww.get_option_chain(
            exchange=groww.EXCHANGE_NSE,
            underlying="NIFTY",
            expiry_date=expiry_date
        )

    except Exception as e:

        st.error(f"❌ Groww Option Chain API Error: {e}")

        return pd.DataFrame(), None

    spot = None

    if isinstance(response, dict):

        data = response.get("option_chain")

        if data is None:
            data = response.get("data")

        spot = (
            response.get("underlying_ltp")
            or response.get("spot_price")
            or response.get("underlying_price")
        )

        if data is None:
            data = response

    else:

        data = response

    if isinstance(data, list):

        df = pd.DataFrame(data)

    elif isinstance(data, dict):

        rows = []

        for strike, value in data.items():

            if isinstance(value, dict):

                row = value.copy()
                row["strike_price"] = strike
                rows.append(row)

        df = pd.DataFrame(rows)

    else:

        df = pd.DataFrame()

    # Find spot price
    if spot is None and not df.empty:

        for col in [
            "underlying_ltp",
            "spot_price",
            "underlying_price",
            "underlying_ltp_price"
        ]:

            if col in df.columns:

                values = pd.to_numeric(
                    df[col],
                    errors="coerce"
                ).dropna()

                if not values.empty:

                    spot = float(values.iloc[0])

                    break

    if df.empty:

        st.warning(
            "⚠️ Groww ने Option Chain data खाली भेजा।"
        )

    else:

        st.success(
            f"✅ Groww Option Chain मिला — {len(df)} rows"
        )

    return df, spot


def get_atm_option_chain(
    option_data,
    option_spot,
    strikes_each_side=4
):

    if option_data.empty or option_spot is None:
        return pd.DataFrame()

    df = option_data.copy()

    strike_col = next(
        (
            c for c in [
                "strike_price",
                "strike",
                "strikePrice"
            ]
            if c in df.columns
        ),
        None
    )

    if strike_col is None:
        return pd.DataFrame()

    df[strike_col] = pd.to_numeric(
        df[strike_col],
        errors="coerce"
    )

    df = df.dropna(
        subset=[strike_col]
    )

    atm = round(float(option_spot) / 50) * 50

    low = atm - strikes_each_side * 50
    high = atm + strikes_each_side * 50

    return df[
        (df[strike_col] >= low)
        &
        (df[strike_col] <= high)
    ].copy()


def calculate_pcr(atm_data):

    if atm_data.empty:
        return None

    oi_col = next(
        (
            c for c in [
                "open_interest",
                "openInterest",
                "oi"
            ]
            if c in atm_data.columns
        ),
        None
    )

    type_col = next(
        (
            c for c in [
                "option_type",
                "optionType",
                "type"
            ]
            if c in atm_data.columns
        ),
        None
    )

    if oi_col is None or type_col is None:
        return None

    df = atm_data.copy()

    df[oi_col] = pd.to_numeric(
        df[oi_col],
        errors="coerce"
    ).fillna(0)

    typ = df[type_col].astype(str).str.upper()

    call_oi = df.loc[
        typ.isin(["CE", "CALL"]),
        oi_col
    ].sum()

    put_oi = df.loc[
        typ.isin(["PE", "PUT"]),
        oi_col
    ].sum()

    if call_oi == 0:
        return None

    return round(
        put_oi / call_oi,
        2
    )


def option_sentiment(atm_data):

    pcr = calculate_pcr(atm_data)

    if pcr is None:
        return "NO DATA", 50

    if pcr >= 1.20:
        return "BULLISH", 70

    if pcr <= 0.80:
        return "BEARISH", 30

    return "NEUTRAL", 50


def get_option_support_resistance(atm_data):

    if atm_data.empty:
        return None, None

    strike_col = next(
        (
            c for c in [
                "strike_price",
                "strike",
                "strikePrice"
            ]
            if c in atm_data.columns
        ),
        None
    )

    oi_col = next(
        (
            c for c in [
                "open_interest",
                "openInterest",
                "oi"
            ]
            if c in atm_data.columns
        ),
        None
    )

    type_col = next(
        (
            c for c in [
                "option_type",
                "optionType",
                "type"
            ]
            if c in atm_data.columns
        ),
        None
    )

    if (
        strike_col is None
        or oi_col is None
        or type_col is None
    ):
        return None, None

    df = atm_data.copy()

    df[oi_col] = pd.to_numeric(
        df[oi_col],
        errors="coerce"
    ).fillna(0)

    typ = df[type_col].astype(str).str.upper()

    calls = df[
        typ.isin(["CE", "CALL"])
    ]

    puts = df[
        typ.isin(["PE", "PUT"])
    ]

    resistance = None
    support = None

    if not calls.empty:

        resistance = calls.loc[
            calls[oi_col].idxmax(),
            strike_col
        ]

    if not puts.empty:

        support = puts.loc[
            puts[oi_col].idxmax(),
            strike_col
        ]

    return support, resistance
