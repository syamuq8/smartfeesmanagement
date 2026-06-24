# smartfeesmanagement
# Smart College Fee Management System — MongoDB Version

Flask + MongoDB + Bootstrap 5 · PDF Receipts · Email Notifications

---

## Tech Stack

| Layer    | Technology                        |
|----------|-----------------------------------|
| Backend  | Python 3.10+, Flask 3.0           |
| Database | MongoDB (local or Atlas)          |
| ODM      | pymongo 4.7                       |
| Frontend | Jinja2, Bootstrap 5.3, Chart.js 4 |
| PDF      | ReportLab 4.2                     |
| Email    | Flask-Mail (Gmail SMTP)           |
| Excel    | pandas + openpyxl                 |

---

## Setup (5 steps)

### 1. Install packages
```bash
pip install -r requirements.txt
```

### 2. Make sure MongoDB is running
```bash
# Windows (if installed as service, already running)
# Or start manually:
mongod

# Check it's running:
mongo --eval "db.runCommand({ connectionStatus: 1 })"
```

### 3. Edit config.py
```python
MONGO_URI    = 'mongodb://localhost:27017/college_fees'  # local (default)
# OR for Atlas:
MONGO_URI    = 'mongodb+srv://user:pass@cluster.mongodb.net/college_fees'

MAIL_USERNAME = 'youremail@gmail.com'
MAIL_PASSWORD = 'your_16_char_app_password'
```

### 4. Create admin
```bash
python create_admin.py
```

### 5. Run
```bash
python app.py
```
Open: http://localhost:5000
Login: admin / Admin@123

---

## MongoDB Collections

| Collection | Purpose                                   |
|------------|-------------------------------------------|
| admins     | Admin login credentials                   |
| students   | Student profiles + fee balance            |
| payments   | Payment history (references student _id)  |

No schema file needed — MongoDB creates collections automatically on first insert.

---

## Key Differences from MySQL Version

- No `schema.sql` file — MongoDB is schema-less
- Student IDs are MongoDB `ObjectId` strings (24-char hex), not integers
- Queries use `find()`, `update_one()`, `aggregate()` instead of SQL
- Indexes are created automatically on startup via `setup_indexes()`
- Receipt numbers use first 8 chars of MongoDB ObjectId

---

## Excel Import Template

| name | roll_number | branch | year | email | parent_email | phone | total_fee | paid_amount |
|------|-------------|--------|------|-------|--------------|-------|-----------|-------------|
| Ravi Kumar | 21MH1A0501 | CSE | 2 | ravi@mail.com | parent@mail.com | 9876543210 | 85000 | 40000 |
