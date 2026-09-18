import streamlit as st
import pandas as pd
import plotly.express as px
import requests

st.set_page_config(page_title="AI Spam Guard", page_icon="🛡️", layout="wide")

# API Configuration
API_BASE_URL = "http://localhost:8000"

st.title("🛡️ AI Spam Guard Dashboard")
st.markdown("Clean your inbox using Artificial Intelligence.")

# Sidebar for Account Settings
st.sidebar.header("Account Settings")

demo_mode = st.sidebar.checkbox("🌟 Use Demo Mode (No Login Required)")

if demo_mode:
    user_email = "demo@example.com"
    st.sidebar.info("Demo Mode Active: Using sample data to showcase AI capabilities.")
else:
    user_email = st.sidebar.text_input("Your Email Address", placeholder="your_email@gmail.com")
    if st.sidebar.button("🔐 Check Connection"):
        try:
            response = requests.get(f"{API_BASE_URL}/auth/status")
            if response.status_code == 200 and response.json().get("status") == "authenticated":
                st.sidebar.success("Connected to AI Backend!")
            else:
                st.sidebar.error("Backend not authenticated. Please check credentials.json.")
        except Exception as e:
            st.sidebar.error(f"Backend unreachable: {e}")

# Main App State
if 'emails' not in st.session_state:
    st.session_state.emails = []

# Tabs for Organization
tab_analysis, tab_history = st.tabs(["🔍 Real-time Analysis", "📊 Scan History"])

with tab_analysis:
    if st.button("🔍 Scan Inbox for Spam"):
        if not user_email:
            st.error("Please enter your email address in the sidebar.")
        else:
            try:
                # 1. Get unread count first
                with st.spinner("Connecting to AI Backend..."):
                    count_resp = requests.get(f"{API_BASE_URL}/unread-count", params={"email": user_email})
                    if count_resp.status_code != 200:
                        raise Exception(count_resp.json().get("detail", "Unknown error"))

                    total_unread = count_resp.json().get("count", 0)

                if total_unread == 0:
                    st.info("No unread emails found.")
                else:
                    # 2. Fetch and predict emails
                    with st.spinner(f"Analyzing {total_unread} emails..."):
                        scan_resp = requests.get(f"{API_BASE_URL}/scan", params={"email": user_email})
                        if scan_resp.status_code != 200:
                            raise Exception(scan_resp.json().get("detail", "Unknown error"))

                        emails = scan_resp.json().get("emails", [])
                        st.session_state.emails = emails
                        st.success(f"Successfully scanned {len(emails)} emails!")
            except Exception as e:
                st.error(f"API Error: {e}")

    # Display Stats and Results
    if st.session_state.emails:
        df = pd.DataFrame(st.session_state.emails)

        total_emails = len(df)
        spam_count = len(df[df['verdict'] == 'Spam'])
        ham_count = len(df[df['verdict'] == 'Ham'])

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Scanned", total_emails)
        col2.metric("Spam Detected", spam_count, delta=spam_count, delta_color="inverse")
        col3.metric("Normal (Ham)", ham_count)

        st.subheader("Email Analysis")

        for idx, email in enumerate(st.session_state.emails):
            with st.expander(f"{'🔴' if email['verdict'] == 'Spam' else '🟢'} {email['subject']}"):
                st.write(f"**Verdict:** {email['verdict']}")

                if email['verdict'] == 'Spam':
                    if st.button(f"🔍 Explain AI Logic", key=f"exp_{idx}"):
                        with st.spinner("Calculating importance scores..."):
                            # Call the /explain endpoint
                            exp_resp = requests.get(f"{API_BASE_URL}/explain", params={"text": email['full_text']})
                            if exp_resp.status_code == 200:
                                explanation = exp_resp.json().get("explanation")
                                st.write("### Word Influence (SHAP)")
                                st.write("Positive values push towards 'Spam', negative towards 'Ham'.")

                                sorted_exp = sorted(explanation, key=lambda x: abs(x[1]), reverse=True)[:10]
                                for token, score in sorted_exp:
                                    color = "red" if score > 0 else "blue"
                                    st.markdown(f"**{token}**: :{color}[{score:.4f}]")
                            else:
                                st.error("Could not get explanation.")

        if spam_count > 0:
            st.divider()
            if st.button("🗑️ Delete All Identified Spam"):
                with st.spinner("Deleting spam emails..."):
                    try:
                        spam_ids = df[df['verdict'] == 'Spam']['id'].tolist()
                        del_resp = requests.post(f"{API_BASE_URL}/delete", json={"email_ids": spam_ids})
                        if del_resp.status_code == 200:
                            st.success(f"Successfully deleted {spam_count} spam emails!")
                            st.session_state.emails = []
                            st.rerun()
                        else:
                            st.error(del_resp.json().get("detail", "Deletion failed"))
                    except Exception as e:
                        st.error(f"API Error: {e}")
    else:
        if not user_email:
            st.info("Please enter your email in the sidebar to start.")
        else:
            st.info("Click 'Scan Inbox' to start.")

with tab_history:
    st.subheader("Historical Analysis")

    if st.button("🧹 Clear History"):
        try:
            resp = requests.post(f"{API_BASE_URL}/clear-history")
            if resp.status_code == 200:
                st.success("History cleared!")
                st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    try:
        history_resp = requests.get(f"{API_BASE_URL}/history")
        if history_resp.status_code == 200:
            history_df = pd.DataFrame(history_resp.json())
            if not history_df.empty:
                # Plotly Time Series
                st.write("### Spam Trend Over Time")
                history_df['timestamp'] = pd.to_datetime(history_df['timestamp'])

                # Group by date and verdict
                trend_df = history_df.groupby([history_df['timestamp'].dt.date, 'verdict']).size().reset_index(name='count')

                fig = px.line(trend_df, x='timestamp', y='count', color='verdict',
                             title="Spam vs Ham Trend", labels={'timestamp': 'Date', 'count': 'Emails'})
                st.plotly_chart(fig, use_container_width=True)

                # Historical Log Table
                st.write("### Detailed Log")
                st.dataframe(history_df[['timestamp', 'subject', 'verdict', 'user_email']], use_container_width=True)
            else:
                st.info("No history found. Start scanning emails to see trends!")
        else:
            st.error("Could not fetch history.")
    except Exception as e:
        st.error(f"Error: {e}")
