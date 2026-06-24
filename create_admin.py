"""
Run ONCE after setup:
  python create_admin.py
"""
from werkzeug.security import generate_password_hash
from utils.db import get_admins
from datetime import datetime

username  = "admin"
password  = "Admin@123"    # change before deployment
full_name = "Fee Admin"

col = get_admins()
existing = col.find_one({'username': username})
hashed = generate_password_hash(password)

if existing:
    col.update_one({'username': username}, {'$set': {'password_hash': hashed}})
    print(f"Admin '{username}' password updated.")
else:
    col.insert_one({
        'username':      username,
        'password_hash': hashed,
        'full_name':     full_name,
        'created_at':    datetime.now()
    })
    print(f"Admin '{username}' created. Login password: {password}")
