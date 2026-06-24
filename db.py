from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure
from config import Config

_client = None

def get_db():
    global _client
    if _client is None:
        _client = MongoClient(Config.MONGO_URI)
    return _client.get_default_database()

def get_students():
    return get_db()['students']

def get_payments():
    return get_db()['payments']

def get_admins():
    return get_db()['admins']

def setup_indexes():
    """Run once on startup to create indexes."""
    db = get_db()
    db['students'].create_index('roll_number', unique=True)
    db['students'].create_index('email', unique=True)
    db['students'].create_index([('name', ASCENDING)])
    db['payments'].create_index([('paid_at', DESCENDING)])
    db['payments'].create_index('student_id')
    db['admins'].create_index('username', unique=True)
    print("MongoDB indexes ready.")
