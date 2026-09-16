import streamlit as st
from kiteconnect import KiteConnect

st.set_page_config(
    page_title="NIFTY Professional Trading Dashboard",
    page_icon="📈",
    layout="wide"
)

st.title("📈 NIFTY PROFESSIONAL TRADING DASHBOARD")

# -------------------------------------------------
# KITE CREDENTIALS
# -------------------------------------------------

API_KEY = st.secrets.get("KITE_API_KEY")
API_SECRET = st.secrets.get("KITE_API_SECRET")

if not API_KEY or not API_SECRET:
    st.error("Kite API credentials Streamlit Secrets में नहीं मिले.")
    st.stop()

kite = KiteConnect(api_key=API_KEY)

# -------------------------------------------------
# LOGIN
# -------------------------------------------------

st.subheader("🔐 Kite Connection")

login_url = kite.login_url()

st.link_button(
    "🔑 Login with Kite",
    login_url
)

st.info(
    "Login करने के बाद Kite आपको आपके Redirect URL पर वापस भेजेगा."
)

# -------------------------------------------------
# REQUEST TOKEN
# -------------------------------------------------

query_params = st.query_params

request_token = query_params.get("request_token")

if request_token:

    try:

        session_data = kite.generate_session(
            request_token,
            api_secret=API_SECRET
        )

        access_token = session_data["access_token"]

        st.session_state["access_token"] = access_token

        kite.set_access_token(access_token)

        st.success("✅ Kite authentication successful!")

    except Exception as e:

        st.error(
            f"❌ Kite authentication failed: {e}"
        )

# -------------------------------------------------
# CHECK ACCESS TOKEN
# -------------------------------------------------

access_token = st.session_state.get(
    "access_token"
)

if not access_token:

    st.warning(
        "पहले ऊपर दिए गए 'Login with Kite' button से Kite login करें."
    )

    st.stop()

kite.set_access_token(access_token)

# -------------------------------------------------
# PROFILE TEST
# -------------------------------------------------

try:

    profile = kite.profile()

    st.success(
        f"Connected: {profile.get('user_name', 'Kite User')}"
    )

except Exception as e:

    st.error(
        f"Kite connection error: {e}"
    )

    st.stop()

# -------------------------------------------------
# MARKET DATA
# -------------------------------------------------

st.divider()

st.subheader("📊 Live Market")

try:

    instruments = kite.ltp([
        "NSE:NIFTY 50",
        "NSE:NIFTY BANK",
        "NSE:INDIA VIX"
    ])

except Exception as e:

    st.error(
        f"❌ Market data error: {e}"
    )

    st.stop()

# -------------------------------------------------
# DISPLAY
# -------------------------------------------------

c1, c2, c3 = st.columns(3)

nifty = instruments.get("NSE:NIFTY 50", {})
banknifty = instruments.get("NSE:NIFTY BANK", {})
vix = instruments.get("NSE:INDIA VIX", {})

with c1:

    st.metric(
        "NIFTY 50",
        f"{nifty.get('last_price', 0):,.2f}"
    )

with c2:

    st.metric(
        "BANK NIFTY",
        f"{banknifty.get('last_price', 0):,.2f}"
    )

with c3:

    st.metric(
        "INDIA VIX",
        f"{vix.get('last_price', 0):,.2f}"
    )

# -------------------------------------------------
# STATUS
# -------------------------------------------------

st.divider()

st.success(
    "🟢 Kite API connected. Live market-data connection is working."
)

st.caption(
    "यह version केवल Kite authentication और live LTP connection test करता है."
)
