from flask import Flask, request, render_template, redirect, url_for, send_from_directory
import sqlite3
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import pytz

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
EXAM_FOLDER = 'exam_pdfs'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['EXAM_FOLDER'] = EXAM_FOLDER
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

DB_FILE = 'college_app.db'

# ==========================
# Database Initialization
# ==========================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Applications table
    c.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fullname TEXT,
            dob TEXT,
            email TEXT,
            phone TEXT,
            board TEXT,
            year INTEGER,
            percentage REAL,
            course TEXT,
            marksheet TEXT,
            submitted_at TEXT
        )
    ''')

    # Exam schedule table
    c.execute('''
        CREATE TABLE IF NOT EXISTS exam_schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            pdf_file TEXT,
            uploaded_at TEXT
        )
    ''')
    # Students table (Corrected with email UNIQUE only)
    c.execute('''
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        roll_no TEXT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT
    )
''')

    conn.commit()
    conn.close()

# ==========================
# Get IST time
# ==========================
def get_ist_time():
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S')

# ==========================
# Allowed File
# ==========================
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ==========================
# HOME PAGE
# ==========================
@app.route('/')
def index():
    return render_template('index.html')

# ==========================
# Apply Form Page
# ==========================
@app.route('/apply')
def apply_form():
    return render_template('apply_form.html')

# ==========================
# Submit Application
# ==========================
@app.route('/submit-application', methods=['POST'])
def submit_application():
    fullname = request.form['fullname']
    dob = request.form['dob']
    email = request.form['email']
    phone = request.form['phone']
    board = request.form['board']
    year = request.form['year']
    percentage = request.form['percentage']
    course = request.form['course']

    marksheet = request.files['marksheet']
    filename = ""

    if marksheet and allowed_file(marksheet.filename):
        filename = secure_filename(marksheet.filename)
        marksheet.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO applications 
        (fullname, dob, email, phone, board, year, percentage, course, marksheet, submitted_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (fullname, dob, email, phone, board, year, percentage, course, filename, get_ist_time()))
    conn.commit()
    conn.close()

    return redirect(url_for('success'))

# ==========================
# Success Page
# ==========================
@app.route('/success')
def success():
    return render_template('success.html')

# ==========================
# File View
# ==========================
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ==========================
# Courses Page
# ==========================
@app.route('/courses')
def courses():
    return render_template('courses.html')

# ==========================
# Faculty Page
# ==========================
@app.route('/faculty')
def faculty():
    return render_template('faculty.html')

# ==========================
# Admin Panel
# ==========================
@app.route('/admin', methods=['GET', 'POST'])
def admin_panel():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    if request.method == 'POST':
        search = request.form.get('search')
        c.execute("""
            SELECT * FROM applications 
            WHERE fullname LIKE ? OR email LIKE ? OR course LIKE ? 
            ORDER BY submitted_at DESC
        """, (f"%{search}%", f"%{search}%", f"%{search}%"))
    else:
        c.execute("SELECT * FROM applications ORDER BY submitted_at DESC")

    data = c.fetchall()
    conn.close()
    return render_template("admin.html", applications=data)

# ==========================
# Delete Application
# ==========================
@app.route('/delete/<int:app_id>')
def delete_application(app_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM applications WHERE id=?", (app_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_panel'))

# ==========================
# Upload Exam PDF
# ==========================
@app.route('/upload-exam', methods=['GET', 'POST'])
def upload_exam():
    if request.method == 'POST':
        title = request.form['title']
        pdf_file = request.files['pdf_file']

        filename = ""
        if pdf_file and pdf_file.filename.endswith(".pdf"):
            filename = secure_filename(pdf_file.filename)
            pdf_file.save(os.path.join(app.config['EXAM_FOLDER'], filename))

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("""
            INSERT INTO exam_schedule (title, pdf_file, uploaded_at) 
            VALUES (?, ?, ?)
        """, (title, filename, get_ist_time()))
        conn.commit()
        conn.close()

        return redirect(url_for('view_exam'))

    return render_template("upload_exam.html")

# ==========================
# View Exam Schedule
# ==========================
@app.route('/exam-schedule')
def view_exam():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM exam_schedule ORDER BY uploaded_at DESC")
    exams = c.fetchall()
    conn.close()
    return render_template("exam_schedule.html", exams=exams)

@app.route('/exam_pdfs/<filename>')
def exam_pdfs(filename):
    return send_from_directory(app.config['EXAM_FOLDER'], filename)

# ==========================
# Student Login
# ==========================
@app.route('/student-login', methods=['GET', 'POST'])
def student_login():
    error = None

    if request.method == 'POST':
        roll_no = request.form['roll_no']
        password = request.form['password']

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT * FROM students WHERE roll_no=? AND password=?", (roll_no, password))
        student = c.fetchone()
        conn.close()

        if student:
            return redirect(url_for('student_dashboard', student_id=student[0]))
        else:
            error = " Invalid Roll No or Password"

    return render_template("student_login.html", error=error)

# ==========================
# Student Dashboard
# ==========================
@app.route('/student/<int:student_id>')
def student_dashboard(student_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM students WHERE id=?", (student_id,))
    student = c.fetchone()
    conn.close()

    if student:
        return render_template("student_dashboard.html", student=student)
    else:
        return "Student not found", 404

# ==========================
# Student Sign-Up (Form)
# ==========================
@app.route('/sign-up')
def sign_up():
    return render_template("sign_up.html")

# ==========================
# Student Sign-Up (Submit)
# ==========================
@app.route('/submit-signup', methods=['POST'])
def submit_signup():
    name = request.form.get('name')
    roll = request.form.get('roll')
    email = request.form.get('email')
    password = request.form.get('password')

    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("""
            INSERT INTO students (roll_no, name, email, password)
            VALUES (?, ?, ?, ?)
        """, (roll, name, email, password))
        conn.commit()
        conn.close()

        return redirect(url_for('student_login'))

    except sqlite3.IntegrityError as e:
        if "email" in str(e):
            error_message = "This Email is already registered."
        else:
            error_message = "Something went wrong."

        return render_template('sign_up.html', error=error_message)
# ==========================
# Run App
# ==========================
if __name__ == "__main__":
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    if not os.path.exists(EXAM_FOLDER):
        os.makedirs(EXAM_FOLDER)
    init_db()
    app.run(debug=True)