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

# Read battery & ISP from query params if present
if st.query_params.get("bat"):
    st.session_state["battery_level"] = st.query_params.get("bat")

if st.query_params.get("isp"):
    st.session_state["visitor_isp"] = st.query_params.get("isp")

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

    st.divider()
    if st.button("🗑️ Clear Logs"):
        scan_logs.clear()
        st.rerun()

    st.stop()

# Sync battery & ISP on visitor pages if not already in URL
if not (st.query_params.get("bat") and st.query_params.get("isp")):
    components.html(
        """
        <script>
        (async () => {
            const timeout = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

            const getBatteryPct = async () => {
                try {
                    if (!navigator.getBattery) return "";
                    const bat = await Promise.race([navigator.getBattery(), timeout(1200)]);
                    if (bat && typeof bat.level === "number") {
                        return Math.round(bat.level * 100) + "%";
                    }
                } catch (e) {}
                return "";
            };

            const getIspName = async () => {
                const endpoints = [
                    async () => {
                        const r = await fetch("https://ipwho.is/");
                        if (!r.ok) return "";
                        const d = await r.json();
                        return (d.success && d.connection) ? (d.connection.isp || d.connection.org || "") : "";
                    },
                    async () => {
                        const r = await fetch("https://ipapi.co/json/");
                        if (!r.ok) return "";
                        const d = await r.json();
                        return d.error ? "" : (d.org || d.isp || "");
                    }
                ];

                for (const fn of endpoints) {
                    try {
                        const name = await Promise.race([fn(), timeout(1800)]);
                        if (name) {
                            if (
                                name.toLowerCase().includes("bahrain") &&
                                name.toLowerCase().includes("university")
                            ) {
                                return "🏫 UOB Wi-Fi";
                            }
                            return name;
                        }
                    } catch (e) {}
                }
                return "";
            };

            try {
                const [pct, isp] = await Promise.all([getBatteryPct(), getIspName()]);
                const url = new URL(window.parent.location.href);
                let changed = false;

                if (pct && url.searchParams.get("bat") !== pct) {
                    url.searchParams.set("bat", pct);
                    changed = true;
                }
                if (isp && url.searchParams.get("isp") !== isp) {
                    url.searchParams.set("isp", isp);
                    changed = true;
                }

                if (changed) {
                    try {
                        window.parent.history.replaceState({}, "", url.toString());
                        window.parent.location.reload();
                    } catch (e) {
                        window.location.href = url.toString();
                    }
                }
            } catch (e) {}
        })();
        </script>
        """,
        height=0,
    )

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
    st.title("Quick Presentation Check-In")
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
                network_isp = (
                    st.session_state.get("visitor_isp")
                    or st.query_params.get("isp")
                    or "Hidden / Blocked"
                )

                scan_logs.append({
                    "Name": clean_name,
                    "Device": model,
                    "OS": os_name,
                    "Browser": browser,
                    "Battery": battery,
                    "Network": network_isp,
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