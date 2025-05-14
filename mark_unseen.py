# mark_unseen.py
import os
import imaplib
from dotenv import load_dotenv

# load your .env so we get IMAP_HOST/USER/PASS
load_dotenv('/var/www/html/.env')

IMAP_HOST = os.getenv('IMAP_HOST')
IMAP_USER = os.getenv('IMAP_USER')
IMAP_PASS = os.getenv('IMAP_PASS')

# connect and clear the Seen flag on every message
m = imaplib.IMAP4_SSL(IMAP_HOST)
m.login(IMAP_USER, IMAP_PASS)
m.select('INBOX')
typ, data = m.search(None, 'ALL')
for num in data[0].split():
    m.store(num, '-FLAGS', '\\Seen')
m.logout()

print("✅ Cleared \\Seen on all messages in INBOX")
