from flask import Flask, render_template, request, redirect, session
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# 定义数据库模型
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    math = db.Column(db.Integer)
    science = db.Column(db.Integer)
    leaves = db.relationship('Leave', backref='student', lazy=True)

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)

class Grade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    subject = db.Column(db.String(20), nullable=False)
    score = db.Column(db.Integer)

class Leave(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    reason = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='pending')

# 创建数据库表格
with app.app_context():
    db.create_all()

# 首页
@app.route('/')
def index():
    return render_template('index.html')

# 登录
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    # 学生登录
    student = Student.query.filter_by(username=username).first()
    if student and bcrypt.check_password_hash(student.password, password):
        session['username'] = username
        session['role'] = 'student'
        return redirect('/dashboard_student')
    # 管理员登录
    admin = Admin.query.filter_by(username=username).first()
    if admin and bcrypt.check_password_hash(admin.password, password):
        session['username'] = username
        session['role'] = 'admin'
        return redirect('/dashboard_admin')
    return render_template('index.html', error="Invalid username or password")

# 学生仪表板
@app.route('/dashboard_student')
def dashboard_student():
    if 'username' in session and session.get('role') == 'student':
        student = Student.query.filter_by(username=session['username']).first()
        if student:
            student_grades = Grade.query.filter_by(student_id=student.id).all()
            return render_template('dashboard_student.html', username=session['username'], grades=student_grades, student=student)
    return redirect('/')

# 管理员仪表板
@app.route('/dashboard_admin')
def dashboard_admin():
    if 'username' in session and session.get('role') == 'admin':
        admin = Admin.query.filter_by(username=session['username']).first()
        if admin:
            students = Student.query.all()
            return render_template('dashboard_admin.html', username=session['username'], students=students)
    return redirect('/')

# 登出
@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    return redirect('/')

# 学生注册
@app.route('/register_student_page')
def register_student_page():
    return render_template('register_student_page.html')

@app.route('/register_student', methods=['POST'])
def register_student():
    username = request.form['username']
    password = request.form['password']
    if not Student.query.filter_by(username=username).first():
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_student = Student(username=username, password=hashed_password)
        db.session.add(new_student)
        db.session.commit()
        session['username'] = username
        session['role'] = 'student'
        return redirect('/dashboard_student')
    else:
        return "Student account already exists"

# 管理员注册
@app.route('/register_admin_page')
def register_admin_page():
    return render_template('register_admin_page.html')

@app.route('/register_admin', methods=['POST'])
def register_admin():
    username = request.form['username']
    password = request.form['password']
    if not Admin.query.filter_by(username=username).first():
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_admin = Admin(username=username, password=hashed_password)
        db.session.add(new_admin)
        db.session.commit()
        session['username'] = username
        session['role'] = 'admin'
        return redirect('/dashboard_admin')
    else:
        return "Admin account already exists"

# 请假
@app.route('/submit_leave', methods=['POST'])
def submit_leave():
    if 'username' in session and session.get('role') == 'student':
        student = Student.query.filter_by(username=session['username']).first()
        if student:
            leave_date = request.form['leave_date']
            leave_reason = request.form['leave_reason']
            new_leave = Leave(date=leave_date, reason=leave_reason, student_id=student.id)
            db.session.add(new_leave)
            db.session.commit()
    return redirect('/dashboard_student')

@app.route('/leave_approval')
def leave_approval():
    if 'username' in session and session.get('role') == 'admin':
        pending_leaves = Leave.query.filter_by(status='pending').all()
        approved_leaves = Leave.query.filter_by(status='approved').all()
        return render_template('leave_approval.html', pending_leaves=pending_leaves, approved_leaves=approved_leaves)
    return redirect('/')


# 核准请假
@app.route('/approve_leave', methods=['POST'])
def approve_leave():
    if 'username' in session and session.get('role') == 'admin':
        leave_id = request.form['leave_id']
        leave = Leave.query.get(leave_id)
        if leave:
            leave.status = 'approved'
            db.session.commit()
    return redirect('/leave_approval')

@app.route('/input_grades', methods=['GET', 'POST'])
def input_grades():
    if 'username' in session and session.get('role') == 'admin':
        admin = Admin.query.filter_by(username=session['username']).first()
        if admin:
            if request.method == 'POST':
                for student in Student.query.all():
                    math_score = request.form.get(f"{student.id}_math")
                    science_score = request.form.get(f"{student.id}_science")
                    
                    if math_score:
                        # 檢查是否已經存在該學生的數學成績記錄，如果存在，則更新；否則，創建新記錄
                        existing_math_grade = Grade.query.filter_by(student_id=student.id, subject='Math').first()
                        if existing_math_grade:
                            existing_math_grade.score = int(math_score)
                        else:
                            new_grade_math = Grade(student_id=student.id, subject='Math', score=int(math_score))
                            db.session.add(new_grade_math)
                    
                    if science_score:
                        # 檢查是否已經存在該學生的科學成績記錄，如果存在，則更新；否則，創建新記錄
                        existing_science_grade = Grade.query.filter_by(student_id=student.id, subject='Science').first()
                        if existing_science_grade:
                            existing_science_grade.score = int(science_score)
                        else:
                            new_grade_science = Grade(student_id=student.id, subject='Science', score=int(science_score))
                            db.session.add(new_grade_science)
                
                db.session.commit()
                return redirect('/dashboard_admin')
            
            # GET 請求時顯示輸入成績的表單
            return render_template('input_grades.html', students=Student.query.all())
    
    return redirect('/dashboard_admin')


# 注册学生列表
@app.route('/registered_students')
def registered_students():
    if 'username' in session and session.get('role') == 'admin':
        admin = Admin.query.filter_by(username=session['username']).first()
        if admin:
            return render_template('registered_students.html', students=Student.query.all())
    return redirect('/dashboard_admin')

# 添加科目
@app.route('/add_subject', methods=['POST'])
def add_subject():
    if 'username' in session and session.get('role') == 'admin':
        admin = Admin.query.filter_by(username=session['username']).first()
        if admin:
            subject_name = request.form['subject_name']
            if not Grade.query.filter_by(subject=subject_name).first():
                for student in Student.query.all():
                    new_grade = Grade(student_id=student.id, subject=subject_name)
                    db.session.add(new_grade)
                db.session.commit()
                return redirect('/dashboard_admin')
            return "Subject already exists"
    return redirect('/dashboard_admin')

# 添加学生账号密码
@app.route('/add_student_account', methods=['POST'])
def add_student_account():
    if 'username' in session and session.get('role') == 'admin':
        admin = Admin.query.filter_by(username=session['username']).first()
        if admin:
            username = request.form['username']
            password = request.form['password']
            if not Student.query.filter_by(username=username).first():
                hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
                new_student = Student(username=username, password=hashed_password)
                db.session.add(new_student)
                db.session.commit()
                return redirect('/dashboard_admin')
            return "Student account already exists"
    return redirect('/dashboard_admin')

# 新增学生页面
@app.route('/add_student_page')
def add_student_page():
    if 'username' in session and session.get('role') == 'admin':
        admin = Admin.query.filter_by(username=session['username']).first()
        if admin:
            return render_template('add_student_page.html')
    return redirect('/dashboard_admin')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=4000)
