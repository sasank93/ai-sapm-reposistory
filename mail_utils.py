import base64
from email.header import decode_header
from predict import predict_spam
from database import init_db, save_scan_result

# Initialize database on module load
init_db()

def get_unread_count(service):
    result = service.users().messages().list(userId='me', q='is:unread').execute()
    messages = result.get('messages', [])
    return len(messages)

def fetch_emails(service, user_email="Unknown"):
    result = service.users().messages().list(userId='me', q='is:unread').execute()
    messages = result.get('messages', [])

    # Limit to 50 for performance, consistent with previous version
    for msg in messages[:50]:
        msg_id = msg['id']
        message = service.users().messages().get(userId='me', id=msg_id, format='full').execute()

        payload = message.get('payload', {})
        headers = payload.get('headers', [])

        subject = "No Subject"
        for header in headers:
            if header['name'] == 'Subject':
                raw_subject = header['value']
                decoded_subject, encoding = decode_header(raw_subject)[0]
                if isinstance(decoded_subject, bytes):
                    subject = decoded_subject.decode(encoding if encoding else 'utf-8')
                else:
                    subject = decoded_subject
                break

        # Extract Body
        body = ""
        parts = payload.get('parts', [])
        if not parts:
            # Single part message
            data = payload.get('body', {}).get('data', '')
            if data:
                body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        else:
            # Multipart message
            for part in parts:
                if part.get('mimeType') == 'text/plain':
                    data = part.get('body', {}).get('data', '')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                    break

        full_text = f"{subject} {body}"
        verdict = predict_spam(full_text)

        # Save result to database
        save_scan_result(msg_id, subject, verdict, user_email)

        yield {
            'id': msg_id,
            'subject': subject,
            'verdict': verdict,
            'full_text': full_text
        }

def delete_spam_emails(service, message_ids):
    # Gmail API: Move to trash
    batch = service.new_batch_http_request()
    for msg_id in message_ids:
        batch.add(service.users().messages().trash(userId='me', id=msg_id))
    batch.execute()
    return True
