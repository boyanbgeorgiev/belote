import os
import re
import imaplib
import email
from email.header import decode_header, make_header
import mysql.connector
from datetime import datetime
from dotenv import load_dotenv

load_dotenv('/var/www/html/.env')

IMAP_HOST = os.getenv('IMAP_HOST')
IMAP_USER = os.getenv('IMAP_USER')
IMAP_PASS = os.getenv('IMAP_PASS')

DB_CONFIG = {
    'host':     os.getenv('DB_HOST'),
    'user':     os.getenv('DB_USER'),
    'password': os.getenv('DB_PASS'),
    'database': os.getenv('DB_NAME'),
}

TID_RE = re.compile(r'\[TID[:\s]?(\d+)\]', re.IGNORECASE)

def fetch_and_store_last():
    try:
        m = imaplib.IMAP4_SSL(IMAP_HOST)
        m.login(IMAP_USER, IMAP_PASS)
        m.select('INBOX')

        # 1) fetch only unseen
        typ, data = m.search(None, 'UNSEEN')
        if typ != 'OK':
            m.logout()
            return {"success": False, "msg": "IMAP search failed."}

        ids = data[0].split()
        if not ids:
            m.logout()
            return {"success": False, "msg": "No new messages."}

        # 2) limit to the last 10 unseen
        last_ids = ids[-10:]

        msg     = None
        used_id = None

        # 3) scan newest→oldest within those ten
        for mid in reversed(last_ids):
            _, msg_data = m.fetch(mid, '(RFC822)')
            candidate = email.message_from_bytes(msg_data[0][1])

            # decode the subject
            raw_subj = candidate.get('Subject', '')
            try:
                subj = str(make_header(decode_header(raw_subj)))
            except Exception:
                subj = raw_subj

            # if it carries a TID, pick it and stop
            if TID_RE.search(subj) or TID_RE.search(candidate.as_string()):
                msg     = candidate
                used_id = mid
                break

        # 4) if we found none, mark all ten seen & bail
        if not msg:
            for mid in last_ids:
                m.store(mid, '+FLAGS', '\\Seen')
            m.logout()
            return {
                "success": False,
                "msg": "No TID-tagged messages in the last 10 new emails."
            }

        # 5) mark our chosen one seen
        m.store(used_id, '+FLAGS', '\\Seen')
        m.logout()

    except Exception as e:
        return {"success": False, "msg": f"IMAP error: {e}"}

    # --- parse & store exactly like before ---
    sender = email.utils.parseaddr(msg.get('From'))[1]
    raw_subj = msg.get('Subject', '')
    try:
        subject = str(make_header(decode_header(raw_subj)))
    except Exception:
        subject = raw_subj

    tm = TID_RE.search(subject) or TID_RE.search(msg.as_string())
    tid = int(tm.group(1)) if tm else None
    if not tid:
        return {"success": False, "msg": "Selected message has no TID."}

    # extract the plain‐text body
    if msg.is_multipart():
        body = ''
        for part in msg.walk():
            if part.get_content_type() == 'text/plain':
                body = part.get_payload(decode=True).decode(errors='ignore')
                break
    else:
        body = msg.get_payload(decode=True).decode(errors='ignore')

    fetched_at = datetime.now()

    try:
        conn = mysql.connector.connect(charset='utf8mb4', use_unicode=True, **DB_CONFIG)
        cur = conn.cursor()
        cur.execute("INSERT IGNORE INTO tasks (tid) VALUES (%s)", (tid,))
        conn.commit()
        cur.execute("SELECT id FROM tasks WHERE tid = %s", (tid,))
        task_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO emails (task_id, sender, subject, body, fetched_at) "
            "VALUES (%s, %s, %s, %s, %s)",
            (task_id, sender, subject, body, fetched_at)
        )
        conn.commit()
        cur.close()
        conn.close()
        return {"success": True, "msg": f"Fetched TID {tid} from {sender}"}
    except mysql.connector.Error as err:
        return {"success": False, "msg": f"Database error: {err}"}
