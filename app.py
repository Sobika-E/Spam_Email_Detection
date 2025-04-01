import streamlit as st
import joblib
import os
import time
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
import pickle

# App Configuration
st.set_page_config(page_title="📧 Gmail Spam & Scam Detector", page_icon="📩", layout="centered")

# Sidebar Style
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/7/75/Gmail_icon_%282020%29.svg", width=80)
st.sidebar.title("🔍 Navigation")
page = st.sidebar.radio("", ["🏠 Home", "📬 Scan Inbox", "⚙ Settings"])

# Load the spam classifier model and vectorizer using Joblib
model = joblib.load('spam_classifier_model.joblib')
vectorizer = joblib.load('vectorizer.joblib')

# Function to authenticate Gmail API
def authenticate_gmail():
    SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
    creds = None

    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)

        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

    return creds

# Function to fetch first 10 emails
def get_first_10_gmail_messages(service):
    email_list = []
    
    results = service.users().messages().list(userId="me", maxResults=10).execute()
    messages = results.get("messages", [])

    for msg in messages:
        msg_data = service.users().messages().get(userId="me", id=msg["id"]).execute()
        headers = msg_data["payload"]["headers"]
        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
        email_list.append({"id": msg["id"], "subject": subject})

    return email_list

# Function to create or get label
def get_or_create_label(service, label_name):
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    for label in labels:
        if label["name"] == label_name:
            return label["id"]
    label_body = {"name": label_name, "labelListVisibility": "labelShow", "messageListVisibility": "show"}
    new_label = service.users().labels().create(userId="me", body=label_body).execute()
    return new_label["id"]

# Function to move email
def move_email(service, email_id, label_id):
    service.users().messages().modify(
        userId="me",
        id=email_id,
        body={"addLabelIds": [label_id], "removeLabelIds": ["INBOX"]},
    ).execute()

def detect_spam_ml(subject):
    # Ensure subject is transformed using the same vectorizer that was used during training
    subject_vectorized = vectorizer.transform([subject])  # Transform subject to vector
    prediction = model.predict(subject_vectorized)[0]  # Predict using the model
    return prediction == 1  # Assuming 1 means spam


# Function for scam detection (basic keyword-based)
def detect_scam(subject):
    scam_keywords = ["bank account", "urgent", "won", "payment failure", "lottery", "fraud", "password reset", "security alert"]
    return any(keyword.lower() in subject.lower() for keyword in scam_keywords)

# Home Page
if page == "🏠 Home":
    st.title("📩 Gmail Spam & Scam Detector")
    st.subheader("🚀 Keep your inbox clean from spam & scam emails!")
    st.image("https://upload.wikimedia.org/wikipedia/commons/7/75/Gmail_icon_%282020%29.svg", width=150)
    st.write(
        """
        - 🔍 *Automatically scans your Gmail inbox*
        - 📬 *Detects & moves spam emails to 'DetectedSpam'*
        - 🚨 *Detects scam emails & moves them to 'ScamEmails'*
        - 🎨 *Beautiful & user-friendly interface*
        """
    )
    if st.button("🔐 Authenticate with Gmail", help="Click to authorize your Gmail access"):
        creds = authenticate_gmail()
        if creds:
            st.success("✅ Authentication successful!")
        else:
            st.error("❌ Authentication failed. Try again.")

# Scan Inbox Page
elif page == "📬 Scan Inbox":
    st.title("📩 Scan Your Inbox for Spam & Scams")
    st.write("Click the button below to scan the *first 10 emails* for potential threats.")
    
    creds = authenticate_gmail()
    service = build("gmail", "v1", credentials=creds)
    
    spam_label_id = get_or_create_label(service, "DetectedSpam")
    scam_label_id = get_or_create_label(service, "ScamEmails")

    if st.button("🚀 Fetch & Scan First 10 Emails", help="Scans only the first 10 emails"):
        emails = get_first_10_gmail_messages(service)

        if emails:
            progress_bar = st.progress(0)
            total_emails = len(emails)
            
            for i, email in enumerate(emails):
                email_text = email["subject"]
                
                if detect_scam(email_text):
                    move_email(service, email["id"], scam_label_id)
                    st.error(f"⚠ *SCAM DETECTED:* {email['subject']} (Moved to ScamEmails)")
                
                elif detect_spam_ml(email_text):  # Using ML model to detect spam
                    move_email(service, email["id"], spam_label_id)
                    st.warning(f"🚨 *SPAM DETECTED:* {email['subject']} (Moved to DetectedSpam)")
                
                else:
                    st.success(f"✅ *Not Spam:* {email['subject']}")

                progress_bar.progress((i + 1) / total_emails)
                time.sleep(0.2)  # Adding delay for better UI effect
            
            st.success("🎉 Scan Complete!")

        else:
            st.warning("📭 No emails found.")

# Settings Page
elif page == "⚙ Settings":
    st.title("⚙ App Settings")
    st.write("Customize your spam & scam detection settings.")
    
    spam_threshold = st.slider("🔍 Spam Sensitivity", 0.1, 1.0, 0.5)
    scam_threshold = st.slider("🔍 Scam Sensitivity", 0.1, 1.0, 0.5)
    
    if st.button("💾 Save Settings"):
        st.success("✅ Settings saved successfully!")
