import os, sys
from dotenv import load_dotenv

# 1) load your .env so os.environ[...] is populated
load_dotenv('/var/www/html/.env')

# 2) add your app to PYTHONPATH
sys.path.insert(0, '/var/www/html')

# 3) expose the Flask app as “application”
from app import app as application
