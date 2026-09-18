import streamlit as st
import pandas as pd
import plotly.express as px
import os
from mail_utils import fetch_emails, delete_spam_emails, get_unread_count
from auth_utils import get_gmail_service
from predict import predict_spam, explain_prediction, classifier as model_pipeline

st.set_page_config(page_title="AI Spam Guard", page_icon="🛡️", layout="wide")

# --- AI MODEL CACHING ---
# We cache the model so it doesn't reload on every interaction
@st.cache_resource
def load_ai_model():
    # predict.py already initializes the classifier
    return model_pipeline

ai_model = load_ai_model()

st.title("🛡️ AI Spam Guard Dashboard")
st.markdown("Clean your inbox using Artificial Intelligence.")

# --- SIDEBAR & AUTHENTICATION ---
st.sidebar.header("Account Settings")

# Demo Mode Toggle
demo_mode = st.sidebar.checkbox("🌟 Use Demo Mode (No Login Required)")

if demo_mode:
    user_email = "demo@example.com"
    st.sidebar.info("Demo Mode Active: Using sample data to showcase AI capabilities.")
else:
    user_email = st.sidebar.text_input("Your Email Address", placeholder="your_email@gmail.com")

    # In Streamlit Cloud, we use the app's session state for the service
    if 'gmail_service' not in st.session_state:
        st.session_state.gmail_service = None

    if st.sidebar.button("🔐 Sign in with Google"):
        try:
            with st.spinner("Opening browser for authentication..."):
                service = get_gmail_service()
                st.session_state.gmail_service = service
                st.sidebar.success("Successfully authenticated!")
        except Exception as e:
            st.sidebar.error(f"Authentication failed: {e}")

    if st.session_state.gmail_service:
        if st.sidebar.button("Logout"):
            st.session_state.gmail_service = None
            st.session_state.emails = []
            st.rerun()

# --- MAIN APP STATE ---
if 'emails' not in st.session_state:
    st.session_state.emails = []

# --- TABS ---
tab_analysis, tab_history = st.tabs(["🔍 Real-time Analysis", "📊 Scan History"])

with tab_analysis:
    if st.button("🔍 Scan Inbox for Spam"):
        if not user_email:
            st.error("Please enter your email address in the sidebar.")
        else:
            try:
                if demo_mode:
                    # MOCK DATA FOR DEMO MODE
                    st.session_state.emails = [
                        {"id": "1", "subject": "Win a Free iPhone!", "verdict": "Spam", "full_text": "Congratulations! You've won a free iPhone. Click here to claim your prize now!"},
                        {"id": "2", "subject": "Meeting Agenda for Monday", "verdict": "Ham", "full_text": "Hi Team, please find the agenda for our weekly sync on Monday at 10am."},
                        {"id": "3", "subject": "URGENT: Account Suspended", "verdict": "Spam", "full_text": "Your account has been suspended. Please login immediately to verify your identity or your funds will be lost."},
                        {"id": "4", "subject": "Lunch tomorrow?", "verdict": "Ham", "full_text": "Hey, do you want to grab some tacos tomorrow around 1pm?"},
                        {"id": "5", "subject": "Get Rich Quick Scheme", "verdict": "Spam", "full_text": "Make $5000 a day from home! No experience needed. Join our exclusive club today!"},
                    ]
                    st.success("Demo data loaded successfully!")
                else:
                    if not st.session_state.gmail_service:
                        st.error("Please sign in with Google in the sidebar first.")
                    else:
                        service = st.session_state.gmail_service
                        with st.spinner("Connecting to Gmail API..."):
                            total_unread = get_unread_count(service)

                        if total_unread == 0:
                            st.info("No unread emails found.")
                        else:
                            emails = []
                            fetch_limit = 50
                            actual_to_fetch = min(total_unread, fetch_limit)

                            progress_bar = st.progress(0)
                            status_text = st.empty()

                            for i, email in enumerate(fetch_emails(service, user_email), 1):
                                emails.append(email)
                                progress = i / actual_to_fetch
                                progress_bar.progress(min(progress, 1.0))
                                status_text.text(f"Processed {i}/{actual_to_fetch} emails...")

                            progress_bar.empty()
                            status_text.empty()
                            st.session_state.emails = emails
                            st.success(f"Successfully scanned {len(emails)} emails!")
            except Exception as e:
                st.error(f"Error: {e}")

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
                            explanation = explain_prediction(email['full_text'])
                            if isinstance(explanation, list):
                                st.write("### Word Influence (SHAP)")
                                st.write("Positive values push towards 'Spam', negative towards 'Ham'.")
                                sorted_exp = sorted(explanation, key=lambda x: abs(x[1]), reverse=True)[:10]
                                for token, score in sorted_exp:
                                    color = "red" if score > 0 else "blue"
                                    st.markdown(f"**{token}**: :{color}[{score:.4f}]")
                            else:
                                st.error(explanation)

        if spam_count > 0:
            st.divider()
            if st.button("🗑️ Delete All Identified Spam"):
                if not st.session_state.gmail_service:
                    st.error("Authentication lost. Please sign in again.")
                else:
                    with st.spinner("Deleting spam emails..."):
                        try:
                            service = st.session_state.gmail_service
                            spam_ids = df[df['verdict'] == 'Spam']['id'].tolist()
                            delete_spam_emails(service, spam_ids)
                            st.success(f"Successfully deleted {spam_count} spam emails!")
                            st.session_state.emails = []
                            st.rerun()
                        except Exception as e:
                            st.error(f"Deletion failed: {e}")
    else:
        if not demo_mode and not user_email:
            st.info("Please enter your email in the sidebar to start.")
        elif not demo_mode and not st.session_state.gmail_service:
            st.info("Please sign in with Google in the sidebar to start.")
        else:
            st.info("Click 'Scan Inbox' to start.")

with tab_history:
    st.subheader("Historical Analysis")
    from database import get_history, clear_history

    if st.button("🧹 Clear History"):
        try:
            clear_history()
            st.success("History cleared!")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    try:
        history_df = get_history()
        if not history_df.empty:
            st.write("### Spam Trend Over Time")
            history_df['timestamp'] = pd.to_datetime(history_df['timestamp'])
            trend_df = history_df.groupby([history_df['timestamp'].dt.date, 'verdict']).size().reset_index(name='count')
            fig = px.line(trend_df, x='timestamp', y='count', color='verdict',
                         title="Spam vs Ham Trend", labels={'timestamp': 'Date', 'count': 'Emails'})
            st.plotly_chart(fig, use_container_width=True)
            st.write("### Detailed Log")
            st.dataframe(history_df[['timestamp', 'subject', 'verdict', 'user_email']], use_container_width=True)

        else:
            st.info("No history found. Start scanning emails to see trends!")
    except Exception as e:
        st.error(f"Error: {e}")
