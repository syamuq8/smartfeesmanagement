from flask import (Flask, render_template, request, redirect,
                   url_for, session, flash, send_file, jsonify)
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from bson import ObjectId
from bson.errors import InvalidId
from pymongo.errors import DuplicateKeyError
import pandas as pd
import os
from functools import wraps
from datetime import datetime

from utils.db import get_students, get_payments, get_admins, setup_indexes
from utils.pdf_generator import generate_receipt
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
mail = Mail(app)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ── startup ──────────────────────────────────────────────────────────────────
with app.app_context():
    setup_indexes()

# ── helpers ───────────────────────────────────────────────────────────────────
def oid(id_str):
    """Safely convert string to ObjectId."""
    try:
        return ObjectId(id_str)
    except (InvalidId, TypeError):
        return None

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'admin_logged_in' not in session:
            flash('Please login first.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ── auth ──────────────────────────────────────────────────────────────────────
@app.route('/', methods=['GET', 'POST'])
def login():
    if 'admin_logged_in' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        admin = get_admins().find_one({'username': username})
        if admin and check_password_hash(admin['password_hash'], password):
            session['admin_logged_in'] = True
            session['admin_name'] = admin['full_name']
            flash(f"Welcome back, {admin['full_name']}!", 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

# ── dashboard ────────────────────────────────────────────────────────────────
@app.route('/dashboard')
@login_required
def dashboard():
    students_col = get_students()
    payments_col = get_payments()

    total_students   = students_col.count_documents({})
    fully_paid       = students_col.count_documents({'balance': 0})
    total_pending    = list(students_col.aggregate([
        {'$group': {'_id': None, 'total': {'$sum': '$balance'}}}
    ]))
    total_pending    = total_pending[0]['total'] if total_pending else 0

    now = datetime.now()
    month_pipeline = [
        {'$match': {
            'paid_at': {
                '$gte': datetime(now.year, now.month, 1),
                '$lt':  datetime(now.year, now.month+1, 1) if now.month < 12
                        else datetime(now.year+1, 1, 1)
            }
        }},
        {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
    ]
    month_result     = list(payments_col.aggregate(month_pipeline))
    month_collection = month_result[0]['total'] if month_result else 0

    # Recent payments — join student info manually
    recent_raw = list(payments_col.find().sort('paid_at', -1).limit(8))
    recent_payments = []
    for p in recent_raw:
        s = students_col.find_one({'_id': p['student_id']})
        if s:
            p['student_name']  = s['name']
            p['roll_number']   = s['roll_number']
            p['_id_str']       = str(p['_id'])
            recent_payments.append(p)

    # Monthly chart data
    monthly_pipeline = [
        {'$match': {'paid_at': {'$gte': datetime(now.year, 1, 1)}}},
        {'$group': {
            '_id':   {'$month': '$paid_at'},
            'total': {'$sum': '$amount'}
        }},
        {'$sort': {'_id': 1}}
    ]
    month_names = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    monthly_raw = list(payments_col.aggregate(monthly_pipeline))
    monthly_data = [
        {'month': month_names[r['_id']-1], 'total': r['total']}
        for r in monthly_raw
    ]

    return render_template('admin/dashboard.html',
        total_students=total_students,
        fully_paid=fully_paid,
        month_collection=month_collection,
        total_pending=total_pending,
        recent_payments=recent_payments,
        monthly_data=monthly_data,
        admin_name=session.get('admin_name', 'Admin')
    )

# ── students ──────────────────────────────────────────────────────────────────
@app.route('/students')
@login_required
def students():
    search = request.args.get('search', '').strip()
    col = get_students()
    if search:
        query = {'$or': [
            {'name':        {'$regex': search, '$options': 'i'}},
            {'roll_number': {'$regex': search, '$options': 'i'}},
            {'email':       {'$regex': search, '$options': 'i'}},
        ]}
    else:
        query = {}
    student_list = list(col.find(query).sort('name', 1))
    for s in student_list:
        s['_id_str'] = str(s['_id'])
    return render_template('admin/students.html', students=student_list, search=search)

@app.route('/students/add', methods=['GET', 'POST'])
@login_required
def add_student():
    if request.method == 'POST':
        total_fee   = float(request.form.get('total_fee', 0))
        paid_amount = float(request.form.get('paid_amount', 0))
        doc = {
            'name':         request.form.get('name', '').strip(),
            'roll_number':  request.form.get('roll_number', '').strip().upper(),
            'branch':       request.form.get('branch', '').strip(),
            'year':         int(request.form.get('year', 1)),
            'email':        request.form.get('email', '').strip().lower(),
            'parent_email': request.form.get('parent_email', '').strip().lower(),
            'phone':        request.form.get('phone', '').strip(),
            'total_fee':    total_fee,
            'paid_amount':  paid_amount,
            'balance':      total_fee - paid_amount,
            'created_at':   datetime.now(),
        }
        try:
            get_students().insert_one(doc)
            flash(f"Student '{doc['name']}' added successfully.", 'success')
            return redirect(url_for('students'))
        except DuplicateKeyError:
            flash('Roll number or email already exists.', 'danger')
    return render_template('admin/add_student.html')

@app.route('/students/edit/<student_id>', methods=['GET', 'POST'])
@login_required
def edit_student(student_id):
    col = get_students()
    sid = oid(student_id)
    if not sid:
        flash('Invalid student ID.', 'danger')
        return redirect(url_for('students'))

    student = col.find_one({'_id': sid})
    if not student:
        flash('Student not found.', 'danger')
        return redirect(url_for('students'))

    if request.method == 'POST':
        total_fee = float(request.form.get('total_fee', 0))
        update = {
            'name':         request.form.get('name', '').strip(),
            'roll_number':  request.form.get('roll_number', '').strip().upper(),
            'branch':       request.form.get('branch', '').strip(),
            'year':         int(request.form.get('year', 1)),
            'email':        request.form.get('email', '').strip().lower(),
            'parent_email': request.form.get('parent_email', '').strip().lower(),
            'phone':        request.form.get('phone', '').strip(),
            'total_fee':    total_fee,
            'balance':      total_fee - float(student['paid_amount']),
            'updated_at':   datetime.now(),
        }
        try:
            col.update_one({'_id': sid}, {'$set': update})
            flash('Student updated successfully.', 'success')
            return redirect(url_for('students'))
        except DuplicateKeyError:
            flash('Roll number or email already used by another student.', 'danger')

    student['_id_str'] = str(student['_id'])
    return render_template('admin/edit_student.html', student=student)

@app.route('/students/delete/<student_id>', methods=['POST'])
@login_required
def delete_student(student_id):
    sid = oid(student_id)
    if sid:
        get_students().delete_one({'_id': sid})
        get_payments().delete_many({'student_id': sid})
    flash('Student deleted.', 'success')
    return redirect(url_for('students'))

@app.route('/students/import', methods=['GET', 'POST'])
@login_required
def import_students():
    if request.method == 'POST':
        file = request.files.get('excel_file')
        if not file or not file.filename.endswith(('.xlsx', '.xls')):
            flash('Please upload a valid Excel file (.xlsx or .xls)', 'danger')
            return redirect(request.url)

        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        try:
            df = pd.read_excel(filepath)
            required = ['name', 'roll_number', 'branch', 'year',
                        'email', 'parent_email', 'phone', 'total_fee']
            for col in required:
                if col not in df.columns:
                    flash(f"Missing column: '{col}'", 'danger')
                    return redirect(request.url)

            df['paid_amount'] = df.get('paid_amount', pd.Series([0]*len(df))).fillna(0)
            df['balance']     = df['total_fee'] - df['paid_amount']

            success = skipped = 0
            docs = []
            for _, row in df.iterrows():
                doc = {
                    'name':         str(row['name']).strip(),
                    'roll_number':  str(row['roll_number']).strip().upper(),
                    'branch':       str(row['branch']).strip(),
                    'year':         int(row['year']),
                    'email':        str(row['email']).strip().lower(),
                    'parent_email': str(row['parent_email']).strip().lower(),
                    'phone':        str(row['phone']).strip(),
                    'total_fee':    float(row['total_fee']),
                    'paid_amount':  float(row['paid_amount']),
                    'balance':      float(row['balance']),
                    'created_at':   datetime.now(),
                }
                existing = get_students().find_one({
                    '$or': [{'roll_number': doc['roll_number']}, {'email': doc['email']}]
                })
                if existing:
                    skipped += 1
                else:
                    docs.append(doc)
                    success += 1

            if docs:
                get_students().insert_many(docs)
            flash(f"Import done: {success} added, {skipped} skipped (duplicates).", 'success')

        except Exception as e:
            flash(f"Error processing file: {str(e)}", 'danger')
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)
        return redirect(url_for('students'))

    return render_template('admin/import_students.html')

# ── fee collection ────────────────────────────────────────────────────────────
@app.route('/fees/collect', methods=['GET', 'POST'])
@login_required
def collect_fee():
    if request.method == 'POST':
        student_id   = request.form.get('student_id')
        amount       = float(request.form.get('amount', 0))
        payment_mode = request.form.get('payment_mode', 'Cash')
        remarks      = request.form.get('remarks', '').strip()

        sid = oid(student_id)
        student = get_students().find_one({'_id': sid})

        if not student:
            flash('Student not found.', 'danger')
            return redirect(request.url)
        if amount <= 0:
            flash('Amount must be greater than zero.', 'danger')
            return redirect(request.url)
        if amount > student['balance']:
            flash(f"Amount exceeds pending balance of ₹{student['balance']:.2f}", 'danger')
            return redirect(request.url)

        # Insert payment record
        payment_doc = {
            'student_id':   sid,
            'amount':       amount,
            'payment_mode': payment_mode,
            'remarks':      remarks,
            'paid_at':      datetime.now(),
        }
        result = get_payments().insert_one(payment_doc)
        payment_id = result.inserted_id

        # Update student balance
        get_students().update_one(
            {'_id': sid},
            {'$inc': {'paid_amount': amount, 'balance': -amount}}
        )

        # Fetch updated student for PDF
        updated_student = get_students().find_one({'_id': sid})
        payment_doc['_id'] = payment_id

        pdf_buffer = generate_receipt(updated_student, payment_doc, str(payment_id)[:8].upper())

        try:
            send_receipt_email(updated_student, pdf_buffer, str(payment_id)[:8].upper(), amount)
            email_msg = "Receipt emailed to parent."
        except Exception as e:
            email_msg = f"Email could not be sent: {str(e)}"

        flash(f"Payment of ₹{amount:.2f} collected. {email_msg}", 'success')
        return redirect(url_for('download_receipt', payment_id=str(payment_id)))

    search = request.args.get('search', '')
    found_students = []
    if search:
        query = {
            '$and': [
                {'balance': {'$gt': 0}},
                {'$or': [
                    {'name':        {'$regex': search, '$options': 'i'}},
                    {'roll_number': {'$regex': search, '$options': 'i'}},
                ]}
            ]
        }
        found_students = list(get_students().find(query))
        for s in found_students:
            s['_id_str'] = str(s['_id'])

    return render_template('admin/collect_fee.html',
                           students=found_students, search=search)

@app.route('/fees/receipt/<payment_id>')
@login_required
def download_receipt(payment_id):
    pid = oid(payment_id)
    if not pid:
        flash('Invalid receipt ID.', 'danger')
        return redirect(url_for('dashboard'))

    payment = get_payments().find_one({'_id': pid})
    if not payment:
        flash('Receipt not found.', 'danger')
        return redirect(url_for('dashboard'))

    student = get_students().find_one({'_id': payment['student_id']})
    pdf_buffer = generate_receipt(student, payment, str(pid)[:8].upper())
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=f"receipt_{str(pid)[:8]}.pdf",
        mimetype='application/pdf'
    )

@app.route('/fees/history')
@login_required
def payment_history():
    search = request.args.get('search', '').strip()
    payments_col = get_payments()
    students_col = get_students()

    raw = list(payments_col.find().sort('paid_at', -1).limit(300))
    payments = []
    for p in raw:
        s = students_col.find_one({'_id': p['student_id']})
        if not s:
            continue
        if search:
            name_match = search.lower() in s['name'].lower()
            roll_match = search.lower() in s['roll_number'].lower()
            if not (name_match or roll_match):
                continue
        p['student_name'] = s['name']
        p['roll_number']  = s['roll_number']
        p['branch']       = s.get('branch', '')
        p['_id_str']      = str(p['_id'])
        payments.append(p)

    return render_template('admin/payment_history.html',
                           payments=payments, search=search)

# ── email helper ──────────────────────────────────────────────────────────────
def send_receipt_email(student, pdf_buffer, receipt_num, amount):
    msg = Message(
        subject=f"Fee Receipt #{receipt_num} — {student['name']}",
        sender=app.config['MAIL_DEFAULT_SENDER'],
        recipients=[student['parent_email']]
    )
    msg.body = f"""Dear Parent/Guardian of {student['name']},

A fee payment of ₹{amount:.2f} has been received.

Receipt No : {receipt_num}
Student    : {student['name']}
Roll No    : {student['roll_number']}
Branch     : {student['branch']}
Paid       : ₹{amount:.2f}
Balance    : ₹{student['balance']:.2f}

Please find the PDF receipt attached.

Regards,
College Fee Office
{Config.COLLEGE_NAME}
"""
    pdf_buffer.seek(0)
    msg.attach(
        filename=f"receipt_{receipt_num}.pdf",
        content_type='application/pdf',
        data=pdf_buffer.read()
    )
    mail.send(msg)

# ── API: student search autocomplete ─────────────────────────────────────────
@app.route('/api/students/search')
@login_required
def api_student_search():
    q = request.args.get('q', '')
    results = list(get_students().find({
        '$or': [
            {'name':        {'$regex': q, '$options': 'i'}},
            {'roll_number': {'$regex': q, '$options': 'i'}},
        ]
    }, {'name':1,'roll_number':1,'branch':1,'balance':1}).limit(10))
    for r in results:
        r['id'] = str(r.pop('_id'))
    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True)
