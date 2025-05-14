import os
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, flash
from fetcher import fetch_and_store_last
import mysql.connector

# load .env early
load_dotenv('/var/www/html/.env')

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'change-this!')  # needed for flash()

DB_CONFIG = {
    'host':     os.getenv('DB_HOST'),
    'user':     os.getenv('DB_USER'),
    'password': os.getenv('DB_PASS'),
    'database': os.getenv('DB_NAME'),
}

@app.route('/')
def index():
    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor(dictionary=True)
    cur.execute("""
      SELECT t.tid, e.sender, e.subject, e.body, e.fetched_at
      FROM emails e
      JOIN tasks t ON e.task_id = t.id
      ORDER BY e.fetched_at DESC
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return render_template('emails.html', emails=rows)

@app.route('/fetch')
def fetch_route():
    result = fetch_and_store_last()
    if result:
        category = 'success' if result.get('success') else 'warning'
        flash(result.get('msg', 'Fetch completed'), category)
    else:
        flash('No action taken', 'warning')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
