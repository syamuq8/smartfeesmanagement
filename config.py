import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'change-this-in-production-abc123')

    # MongoDB — default local connection
    MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/college_fees')
    # For MongoDB Atlas (cloud), replace with:
    # MONGO_URI = 'mongodb+srv://<user>:<password>@cluster.mongodb.net/college_fees'

    # Flask-Mail (Gmail)
    MAIL_SERVER         = 'smtp.gmail.com'
    MAIL_PORT           = 587
    MAIL_USE_TLS        = True
    MAIL_USERNAME       = os.environ.get('MAIL_USERNAME', 'syampisini387@gmail.com')
    MAIL_PASSWORD       = os.environ.get('MAIL_PASSWORD', 'syamusri8')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_USERNAME', 'syampisini387@gmail.com')

    # College branding (used in PDF receipts)
    COLLEGE_NAME    = 'Raghu Engineering College'
    COLLEGE_ADDRESS = 'Dakamarri, Bheemunipatnam, Visakhapatnam - 531162'
    COLLEGE_PHONE   = '+91 891 000 0000'
    COLLEGE_EMAIL   = 'syampisini387@gmail.com'
