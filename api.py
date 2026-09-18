import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

# Import existing logic from our modules
from auth_utils import get_gmail_service
from mail_utils import fetch_emails, delete_spam_emails, get_unread_count
from predict import predict_spam, explain_prediction
from database import get_history, clear_history

app = FastAPI(title="AI Spam Guard API")

# Get the absolute path for local model fallback
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, 'spam_model')

# Data models for API requests/responses
class ScanRequest(BaseModel):
    user_email: str

class ScanResult(BaseModel):
    id: str
    subject: str
    verdict: str
    full_text: str

class DeleteRequest(BaseModel):
    email_ids: List[str]

# Global service cache
service_cache = {}

def get_service(user_email: str):
    if user_email not in service_cache:
        try:
            service = get_gmail_service()
            service_cache[user_email] = service
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Authentication failed: {e}")
    return service_cache[user_email]

@app.get("/")
async def root():
    return {"message": "AI Spam Guard API is running!"}

@app.get("/auth/status")
async def auth_status():
    """Check if the server is authenticated with Google."""
    try:
        get_gmail_service()
        return {"status": "authenticated"}
    except Exception as e:
        return {"status": "unauthenticated", "error": str(e)}

@app.get("/scan")
async def scan_inbox(email: str):
    """Fetch unread emails and predict spam/ham."""
    try:
        if email == "demo@example.com":
            return {"emails": [
                {"id": "1", "subject": "Win a Free iPhone!", "verdict": "Spam", "full_text": "Congratulations! You've won a free iPhone. Click here to claim your prize now!"},
                {"id": "2", "subject": "Meeting Agenda for Monday", "verdict": "Ham", "full_text": "Hi Team, please find the agenda for our weekly sync on Monday at 10am."},
                {"id": "3", "subject": "URGENT: Account Suspended", "verdict": "Spam", "full_text": "Your account has been suspended. Please login immediately to verify your identity or your funds will be lost."},
                {"id": "4", "subject": "Lunch tomorrow?", "verdict": "Ham", "full_text": "Hey, do you want to grab some tacos tomorrow around 1pm?"},
                {"id": "5", "subject": "Get Rich Quick Scheme", "verdict": "Spam", "full_text": "Make $5000 a day from home! No experience needed. Join our exclusive club today!"},
            ]}

        service = get_service(email)
        emails = list(fetch_emails(service, email))
        return {"emails": emails}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/unread-count")
async def unread_count(email: str):
    """Get count of unread emails."""
    try:
        if email == "demo@example.com":
            return {"count": 5}

        service = get_service(email)
        count = get_unread_count(service)
        return {"count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/delete")
async def delete_emails(req: DeleteRequest):
    """Delete specific emails from the inbox."""
    try:
        service = get_gmail_service()
        delete_spam_emails(service, req.email_ids)
        return {"message": f"Successfully deleted {len(req.email_ids)} emails."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history")
async def fetch_history():
    """Retrieve scan history from SQLite."""
    try:
        df = get_history()
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/clear-history")
async def clear_history_db():
    """Clear all scan history."""
    try:
        clear_history()
        return {"message": "History cleared successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/explain")
async def explain(text: str):
    """Explain a specific prediction."""
    try:
        explanation = explain_prediction(text)
        if isinstance(explanation, str):
            raise HTTPException(status_code=500, detail=explanation)
        return {"explanation": explanation}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
