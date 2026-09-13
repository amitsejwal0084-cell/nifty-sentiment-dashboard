import streamlit as st
import pandas as pd
from datetime import date, timedelta
from growwapi import GrowwAPI


# ---------------------------------------------------------
# GROWW CONNECTION
# ---------------------------------------------------------
def get_groww_client():
    token = st.secrets.get("GROWW_ACCESS_TOKEN")

    if not token:
        raise Exception("GROWW_ACCESS_TOKEN Streamlit Secrets में नहीं मिला।")

    return GrowwAPI(token)


# ---------------------------------------------------------
# USER PROFILE / PERMISSION TEST
# ---------------------------------------------------------
def check_groww_permissions():
    try:
        groww = get_groww_client()

        profile = groww.get_user_profile()

        return profile

    except Exception as e:
        return {
            "error": str(e)
        }


# ---------------------------------------------------------
# NEXT NIFTY EXPIRY
# NIFTY WEEKLY EXPIRY = TUESDAY
# ---------------------------------------------------------
def get_nearest_expiry():
    today = date.today()

    # Monday = 0 ... Tuesday = 1
    days_until_tuesday = (1 - today.weekday()) % 7

    # अगर आज Tuesday है तो अगला Tuesday
    if days_until_tuesday == 0:
        days_until_tuesday = 7

    expiry = today + timedelta(days=days_until_tuesday)

    return expiry.strftime("%Y-%m-%d")


# ---------------------------------------------------------
# NIFTY OPTION CHAIN
# ---------------------------------------------------------
def get_nifty_option_chain():

    groww = get_groww_client()

    expiry_date = get_nearest_expiry()

    # Expiry display
    st.info(f"📅 NIFTY Expiry: {expiry_date}")

    # -----------------------------------------------------
    # FIRST: USER PERMISSION CHECK
    # -----------------------------------------------------
    try:
        profile = groww.get_user_profile()

        st.write("🔎 Groww API Profile Check")

        # पूरा profile कभी भी token नहीं दिखाता,
        # इसलिए केवल useful fields दिखाने की कोशिश करेंगे
        if isinstance(profile, dict):

            active_segments = profile.get("active_segments")

            if active_segments is not None:
                st.write(
                    f"📌 Active Segments: {active_segments}"
                )

            client_id = profile.get("client_id")

            if client_id:
                st.write("✅ Groww account profile accessible")

        else:
            st.write("📌 Profile response received")

    except Exception as e:

        st.error(
            f"❌ Groww User Profile API Error: {e}"
        )


    # -----------------------------------------------------
    # OPTION CHAIN API
    # -----------------------------------------------------
    try:

        data = groww.get_option_chain(
            exchange=groww.EXCHANGE_NSE,
            underlying="NIFTY",
            expiry_date=expiry_date
        )

        # -------------------------------------------------
        # HANDLE RESPONSE
        # -------------------------------------------------
        if isinstance(data, dict):

            option_chain = data.get("option_chain")

            spot = (
                data.get("underlying_ltp")
                or data.get("spot_price")
                or data.get("underlying_price")
            )

            if option_chain is None:
                option_chain = data.get("data")

            if option_chain is None:
                option_chain = data

        else:
            option_chain = data
            spot = None


        # -------------------------------------------------
        # DATAFRAME
        # -------------------------------------------------
        if isinstance(option_chain, list):

            df = pd.DataFrame(option_chain)

        elif isinstance(option_chain, dict):

            # अगर strikes dictionary format में आए
            rows = []

            for strike, value in option_chain.items():

                if isinstance(value, dict):

                    row = value.copy()
                    row["strike_price"] = strike
                    rows.append(row)

            df = pd.DataFrame(rows)

        else:

            df = pd.DataFrame()


        # -------------------------------------------------
        # SPOT PRICE
        # -------------------------------------------------
        if spot is None and not df.empty:

            for col in [
                "underlying_ltp",
                "spot_price",
                "underlying_price",
                "underlying_ltp_price"
            ]:

                if col in df.columns:

                    try:
                        spot = float(
                            df[col].dropna().iloc[0]
                        )
                        break
                    except Exception:
                        pass


        if not df.empty:

            st.success(
                f"✅ Groww Option Chain मिला — {len(df)} rows"
            )

            return df, spot


        st.warning(
            "⚠️ Groww ने Option Chain response दिया लेकिन data खाली है।"
        )

        return pd.DataFrame(), spot


    except Exception as e:

        st.error(
            f"❌ Groww Option Chain API Error: {e}"
        )

        return pd.DataFrame(), None


# ---------------------------------------------------------
# ATM ± STRIKES
# ---------------------------------------------------------
def get_atm_option_chain(
    option_data,
    option_spot,
    strikes_each_side=4
):

    if option_data.empty or option_spot is None:
        return pd.DataFrame()

    df = option_data.copy()

    # Strike column खोजें
    strike_col = None

    for col in [
        "strike_price",
        "strike",
        "strikePrice"
    ]:

        if col in df.columns:
            strike_col = col
            break

    if strike_col is None:
        return pd.DataFrame()

    df[strike_col] = pd.to_numeric(
        df[strike_col],
        errors="coerce"
    )

    df = df.dropna(
        subset=[strike_col]
    )

    # NIFTY strike usually 50 points
    atm_strike = round(option_spot / 50) * 50

    min_strike = atm_strike - (
        strikes_each_side * 50
    )

    max_strike = atm_strike + (
        strikes_each_side * 50
    )

    result = df[
        (df[strike_col] >= min_strike)
        &
        (df[strike_col] <= max_strike)
    ].copy()

    return result


# ---------------------------------------------------------
# PCR
# ---------------------------------------------------------
def calculate_pcr(atm_data):

    if atm_data.empty:
        return None

    df = atm_data.copy()

    # Try common column names
    oi_col = None

    for col in [
        "open_interest",
        "openInterest",
        "oi"
   
