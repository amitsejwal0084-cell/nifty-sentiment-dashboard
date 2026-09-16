import streamlit as st
import pandas as pd


def get_live_option_chain(spot_price, strikes_each_side=10):

    return pd.DataFrame()


def calculate_pcr(option_data):

    if option_data is None or option_data.empty:
        return None

    ce_oi = option_data[
        option_data["type"] == "CE"
    ]["oi"].fillna(0).sum()

    pe_oi = option_data[
        option_data["type"] == "PE"
    ]["oi"].fillna(0).sum()

    if ce_oi == 0:
        return None

    return round(pe_oi / ce_oi, 2)


def calculate_support_resistance(option_data):

    if option_data is None or option_data.empty:
        return None, None

    calls = option_data[
        option_data["type"] == "CE"
    ]

    puts = option_data[
        option_data["type"] == "PE"
    ]

    support = None
    resistance = None

    if not puts.empty:
        support = puts.loc[
            puts["oi"].idxmax(),
            "strike"
        ]

    if not calls.empty:
        resistance = calls.loc[
            calls["oi"].idxmax(),
            "strike"
        ]

    return support, resistance


def calculate_max_pain(option_data):

    if option_data is None or option_data.empty:
        return None

    strikes = sorted(
        option_data["strike"].dropna().unique()
    )

    if not strikes:
        return None

    calls = option_data[
        option_data["type"] == "CE"
    ]

    puts = option_data[
        option_data["type"] == "PE"
    ]

    pain = {}

    for test_strike in strikes:

        call_pain = (
            (test_strike - calls["strike"])
            .clip(lower=0)
            * calls["oi"].fillna(0)
        ).sum()

        put_pain = (
            (puts["strike"] - test_strike)
            .clip(lower=0)
            * puts["oi"].fillna(0)
        ).sum()

        pain[test_strike] = (
            call_pain + put_pain
        )

    return min(pain, key=pain.get)


def calculate_snapshot_oi_change(option_data):

    if option_data is None or option_data.empty:
        return option_data

    previous = st.session_state.get(
        "previous_option_oi",
        {}
    )

    data = option_data.copy()

    data["oi_change"] = data.apply(
        lambda row:
        row["oi"] -
        previous.get(
            row["symbol"],
            row["oi"]
        ),
        axis=1
    )

    st.session_state[
        "previous_option_oi"
    ] = dict(
        zip(
            data["symbol"],
            data["oi"].fillna(0)
        )
    )

    return data


def calculate_buildup(option_data):

    if option_data is None or option_data.empty:
        return option_data

    data = option_data.copy()

    data["buildup"] = "NEUTRAL"

    if "oi_change" in data.columns:

        data.loc[
            data["oi_change"] > 0,
            "buildup"
        ] = "OI BUILDUP"

        data.loc[
            data["oi_change"] < 0,
            "buildup"
        ] = "OI UNWINDING"

    return data


def option_sentiment(option_data):

    pcr = calculate_pcr(option_data)

    if pcr is None:
        return "NO DATA", 50

    if pcr >= 1.20:
        return "BULLISH", 70

    if pcr <= 0.80:
        return "BEARISH", 30

    return "NEUTRAL", 50
