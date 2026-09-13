import streamlit as st
import pandas as pd
from datetime import date, timedelta
from growwapi import GrowwAPI


# =========================================================
# GROWW CLIENT
# =========================================================

def get_groww_client():

    try:
        if "GROWW_ACCESS_TOKEN" not in st.secrets:
            st.error("❌ GROWW_ACCESS_TOKEN Streamlit Secrets में नहीं मिला।")
            return None

        token = st.secrets["GROWW_ACCESS_TOKEN"]

        if not token:
            st.error("❌ GROWW_ACCESS_TOKEN खाली है।")
            return None

        return GrowwAPI(token)

    except Exception as e:
        st.error(f"❌ Groww Client Error: {e}")
        return None


# =========================================================
# FIND NEXT NIFTY EXPIRY
# =========================================================

def get_nearest_expiry():

    today = date.today()

    # NIFTY weekly expiry = Tuesday
    days_until_tuesday = (1 - today.weekday()) % 7

    # अगर आज Tuesday है तो अगली Tuesday लें
    if days_until_tuesday == 0:
        days_until_tuesday = 7

    expiry = today + timedelta(
        days=days_until_tuesday
    )

    return expiry.strftime("%Y-%m-%d")


# =========================================================
# GET NIFTY OPTION CHAIN
# =========================================================

def get_nifty_option_chain(expiry_date=None):

    try:

        groww = get_groww_client()

        if groww is None:
            return pd.DataFrame(), None

        # Expiry API को bypass किया गया है
        if expiry_date is None:
            expiry_date = get_nearest_expiry()

        st.caption(
            f"📅 NIFTY Expiry: {expiry_date}"
        )

        # Direct Option Chain API
        data = groww.get_option_chain(
            exchange=groww.EXCHANGE_NSE,
            underlying="NIFTY",
            expiry_date=expiry_date
        )

        if not isinstance(data, dict):

            st.error(
                "❌ Groww ने invalid Option Chain response दिया।"
            )

            return pd.DataFrame(), None

        # Payload निकालें
        if (
            "payload" in data
            and isinstance(data["payload"], dict)
        ):
            data = data["payload"]

        strikes = data.get(
            "strikes",
            {}
        )

        if not strikes:

            st.warning(
                "⚠️ Groww से NIFTY Option Chain में strikes नहीं मिले।"
            )

            return pd.DataFrame(), None

        spot = data.get(
            "underlying_ltp"
        )

        rows = []

        for strike, strike_data in strikes.items():

            try:
                strike_price = float(strike)
            except Exception:
                continue

            if not isinstance(strike_data, dict):
                continue

            ce = strike_data.get("CE", {}) or {}
            pe = strike_data.get("PE", {}) or {}

            ce_greeks = ce.get(
                "greeks",
                {}
            ) or {}

            pe_greeks = pe.get(
                "greeks",
                {}
            ) or {}

            rows.append({

                "Strike": strike_price,

                "CE_LTP": ce.get(
                    "ltp",
                    0
                ),

                "CE_OI": ce.get(
                    "open_interest",
                    0
                ),

                "CE_Volume": ce.get(
                    "volume",
                    0
                ),

                "CE_IV": ce_greeks.get(
                    "iv",
                    0
                ),

                "CE_Delta": ce_greeks.get(
                    "delta",
                    0
                ),

                "PE_LTP": pe.get(
                    "ltp",
                    0
                ),

                "PE_OI": pe.get(
                    "open_interest",
                    0
                ),

                "PE_Volume": pe.get(
                    "volume",
                    0
                ),

                "PE_IV": pe_greeks.get(
                    "iv",
                    0
                ),

                "PE_Delta": pe_greeks.get(
                    "delta",
                    0
                )
            })

        option_df = pd.DataFrame(rows)

        if option_df.empty:

            st.warning(
                "⚠️ Option Chain DataFrame खाली है।"
            )

            return pd.DataFrame(), spot

        option_df = option_df.sort_values(
            "Strike"
        ).reset_index(
            drop=True
        )

        return option_df, spot

    except Exception as e:

        st.error(
            f"❌ Groww Option Chain API Error: {e}"
        )

        return pd.DataFrame(), None


# =========================================================
# ATM ±4 STRIKES
# =========================================================

def get_atm_option_chain(
    option_data,
    option_spot,
    strikes_each_side=4
):

    try:

        if option_data is None:
            return pd.DataFrame()

        if not isinstance(
            option_data,
            pd.DataFrame
        ):
            return pd.DataFrame()

        if option_data.empty:
            return pd.DataFrame()

        if option_spot is None:

            return option_data.head(
                (strikes_each_side * 2) + 1
            ).copy()

        spot = float(
            option_spot
        )

        atm_index = (
            option_data["Strike"] - spot
        ).abs().idxmin()

        position = option_data.index.get_loc(
            atm_index
        )

        start = max(
            0,
            position - strikes_each_side
        )

        end = min(
            len(option_data),
            position + strikes_each_side + 1
        )

        atm_data = option_data.iloc[
            start:end
        ].copy()

        atm_data["ATM"] = ""

        atm_strike = option_data.loc[
            atm_index,
            "Strike"
        ]

        atm_data.loc[
            atm_data["Strike"] == atm_strike,
            "ATM"
        ] = "ATM"

        return atm_data

    except Exception as e:

        st.error(
            f"❌ ATM Option Chain Error: {e}"
        )

        return pd.DataFrame()


# =========================================================
# PCR
# =========================================================

def calculate_pcr(atm_data):

    try:

        if atm_data is None:
            return None

        if not isinstance(
            atm_data,
            pd.DataFrame
        ):
            return None

        if atm_data.empty:
            return None

        ce_oi = pd.to_numeric(
            atm_data["CE_OI"],
            errors="coerce"
        ).fillna(0).sum()

        pe_oi = pd.to_numeric(
            atm_data["PE_OI"],
            errors="coerce"
        ).fillna(0).sum()

        if ce_oi <= 0:
            return None

        pcr = pe_oi / ce_oi

        return round(
            float(pcr),
            2
        )

    except Exception as e:

        st.error(
            f"❌ PCR Calculation Error: {e}"
        )

        return None


# =========================================================
# OPTION SENTIMENT
# =========================================================

def option_sentiment(atm_data):

    try:

        if atm_data is None:
            return "NO DATA", 50

        if not isinstance(
            atm_data,
            pd.DataFrame
        ):
            return "NO DATA", 50

        if atm_data.empty:
            return "NO DATA", 50

        score = 50

        ce_oi = pd.to_numeric(
            atm_data["CE_OI"],
            errors="coerce"
        ).fillna(0).sum()

        pe_oi = pd.to_numeric(
            atm_data["PE_OI"],
            errors="coerce"
        ).fillna(0).sum()

        ce_volume = pd.to_numeric(
            atm_data["CE_Volume"],
            errors="coerce"
        ).fillna(0).sum()

        pe_volume = pd.to_numeric(
            atm_data["PE_Volume"],
            errors="coerce"
        ).fillna(0).sum()

        if ce_oi > 0:

            pcr = pe_oi / ce_oi

            if pcr >= 1.20:
                score += 15

            elif pcr >= 1.05:
                score += 8

            elif pcr <= 0.80:
                score -= 15

            elif pcr <= 0.95:
                score -= 8

        if ce_oi > 0:

            if pe_oi > ce_oi * 1.15:
                score += 10

            elif ce_oi > pe_oi * 1.15:
                score -= 10

        if pe_volume > ce_volume * 1.10:
            score += 5

        elif ce_volume > pe_volume * 1.10:
            score -= 5

        score = max(
            0,
            min(
                100,
                score
            )
        )

        if score >= 65:
            bias = "BULLISH"

        elif score <= 35:
            bias = "BEARISH"

        else:
            bias = "NEUTRAL"

        return bias, int(score)

    except Exception as e:

        st.error(
            f"❌ Option Sentiment Error: {e}"
        )

        return "NO DATA", 50


# =========================================================
# SUPPORT / RESISTANCE
# =========================================================

def get_oi_support_resistance(
    option_data
):

    try:

        if option_data is None:
            return None, None

        if not isinstance(
            option_data,
            pd.DataFrame
        ):
            return None, None

        if option_data.empty:
            return None, None

        support_row = option_data.loc[
            option_data["PE_OI"].idxmax()
        ]

        resistance_row = option_data.loc[
            option_data["CE_OI"].idxmax()
        ]

        support = float(
            support_row["Strike"]
        )

        resistance = float(
            resistance_row["Strike"]
        )

        return support, resistance

    except Exception:

        return None, None
