import requests
import pandas as pd
from datetime import datetime


NSE_URL = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"


def get_nifty_option_chain():
    """
    NSE से NIFTY Option Chain प्राप्त करता है।
    Returns:
        DataFrame, spot_price
    """

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 10; K) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/130.0 Mobile Safari/537.36"
        ),
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/option-chain",
    }

    session = requests.Session()

    try:
        # NSE homepage से cookies लेना
        session.get(
            "https://www.nseindia.com",
            headers=headers,
            timeout=15
        )

        response = session.get(
            NSE_URL,
            headers=headers,
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

        records = data["records"]
        spot_price = float(records["underlyingValue"])

        rows = []

        for item in records["data"]:

            strike = item.get("strikePrice")

            ce = item.get("CE", {})
            pe = item.get("PE", {})

            rows.append({
                "Strike": strike,

                "CE_OI": ce.get("openInterest", 0),
                "CE_Delta_OI": ce.get("changeinOpenInterest", 0),
                "CE_Volume": ce.get("totalTradedVolume", 0),
                "CE_IV": ce.get("impliedVolatility", 0),

                "PE_OI": pe.get("openInterest", 0),
                "PE_Delta_OI": pe.get("changeinOpenInterest", 0),
                "PE_Volume": pe.get("totalTradedVolume", 0),
                "PE_IV": pe.get("impliedVolatility", 0),
            })

        df = pd.DataFrame(rows)

        df = df.dropna(subset=["Strike"])

        df = df.sort_values("Strike").reset_index(drop=True)

        return df, spot_price

    except Exception as e:

        print("NSE Option Chain Error:", e)

        return pd.DataFrame(), None


def get_atm_option_chain(df, spot_price, strikes_each_side=4):
    """
    ATM के आसपास ±4 strikes निकालता है।
    """

    if df.empty or spot_price is None:
        return pd.DataFrame()

    strikes = df["Strike"].tolist()

    atm_strike = min(
        strikes,
        key=lambda x: abs(x - spot_price)
    )

    strike_index = strikes.index(atm_strike)

    start = max(0, strike_index - strikes_each_side)
    end = min(
        len(strikes),
        strike_index + strikes_each_side + 1
    )

    result = df.iloc[start:end].copy()

    return result


def calculate_pcr(df):
    """
    Total PE OI / Total CE OI
    """

    if df.empty:
        return None

    ce_oi = df["CE_OI"].sum()
    pe_oi = df["PE_OI"].sum()

    if ce_oi == 0:
        return None

    return pe_oi / ce_oi


def option_sentiment(df):
    """
    Simple option-chain sentiment.
    """

    if df.empty:
        return "NO DATA", 50

    ce_oi_change = df["CE_Delta_OI"].sum()
    pe_oi_change = df["PE_Delta_OI"].sum()

    score = 50

    # Put OI addition = support
    if pe_oi_change > ce_oi_change:
        score += 15
    else:
        score -= 15

    # PCR
    pcr = calculate_pcr(df)

    if pcr is not None:

        if pcr >= 1.10:
            score += 15

        elif pcr <= 0.90:
            score -= 15

    score = max(0, min(100, score))

    if score >= 65:
        sentiment = "BULLISH"

    elif score <= 35:
        sentiment = "BEARISH"

    else:
        sentiment = "NEUTRAL"

    return sentiment, score


if __name__ == "__main__":

    df, spot = get_nifty_option_chain()

    if df.empty:

        print("❌ Option Chain Data नहीं मिला।")

    else:

        atm_data = get_atm_option_chain(
            df,
            spot,
            strikes_each_side=4
        )

        pcr = calculate_pcr(atm_data)

        sentiment, score = option_sentiment(atm_data)

        print("\nNIFTY OPTION CHAIN")
        print("--------------------------")

        print("Spot:", spot)

        print(
            "PCR:",
            round(pcr, 2) if pcr else "N/A"
        )

        print(
            "Option Sentiment:",
            sentiment
        )

        print(
            "Option Score:",
            score,
            "/ 100"
        )

        print("\nATM ±4 STRIKES\n")

        print(
            atm_data.to_string(index=False)
        )
