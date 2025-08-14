import os
import os
import json
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, send_from_directory
)
from flask_login import (
    LoginManager, login_user, logout_user, login_required, UserMixin, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import func
from flask_sqlalchemy import SQLAlchemy

# -------------------- App Setup --------------------
app = Flask(__name__, instance_relative_config=True)
app.config['SECRET_KEY'] = 'change-this-secret-key'
os.makedirs(app.instance_path, exist_ok=True)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "database.db")

# Uploads
UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_LOGO_EXTS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'admin_login'

# -------------------- Models --------------------
class AdminUser(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)


class Meta(db.Model):
    """Simple key-value store for app state (e.g., last seen member id)"""
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)

    @staticmethod
    def get(key, default=None):
        rec = Meta.query.filter_by(key=key).first()
        return rec.value if rec else default

    @staticmethod
    def set(key, value):
        rec = Meta.query.filter_by(key=key).first()
        if rec:
            rec.value = value
        else:
            rec = Meta(key=key, value=value)
            db.session.add(rec)
        db.session.commit()


class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Bio Data
    name = db.Column(db.String(120), nullable=False)
    other_name = db.Column(db.String(120))
    location = db.Column(db.String(120))
    home_location = db.Column(db.String(120))
    phone = db.Column(db.String(50))
    religion = db.Column(db.String(120))
    church_name = db.Column(db.String(120))

    # Professional Details
    profession = db.Column(db.String(120))
    skills = db.Column(db.Text)      # comma-separated
    gifts = db.Column(db.Text)       # comma-separated
    experience = db.Column(db.Text)

    # Departments (multi-select stored as CSV)
    departments = db.Column(db.Text)

    # Referees (JSON list of dicts: [{name, location, phone}, ...])
    referees_json = db.Column(db.Text)

    approved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# -------------------- Auth --------------------
@login_manager.user_loader
def load_user(user_id):
    return AdminUser.query.get(int(user_id))


# -------------------- Helpers --------------------
def init_db():
    db.create_all()
    # Seed default admin if not exists
    if not AdminUser.query.first():
        admin = AdminUser(username='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
    # Seed last_seen_member_id if not exists
    if Meta.get('last_seen_member_id') is None:
        Meta.set('last_seen_member_id', '0')

def allowed_logo(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_LOGO_EXTS']

def get_logo_url():
    # If there's a custom logo saved in meta, use it; else fallback to default if exists
    logo_meta = Meta.get('logo_path')
    if logo_meta and os.path.exists(logo_meta):
        return '/' + logo_meta.replace('\\', '/')
    fallback = os.path.join(app.config['UPLOAD_FOLDER'], 'logo.png')
    if os.path.exists(fallback):
        return '/' + fallback.replace('\\', '/')
    return None

def pending_count():
    return db.session.scalar(db.select(func.count()).select_from(Member).where(Member.approved == False))

def new_since_last_seen_count():
    last_seen_id = int(Meta.get('last_seen_member_id', '0') or '0')
    return db.session.scalar(db.select(func.count()).select_from(Member).where(Member.id > last_seen_id))


# -------------------- Routes (Public) --------------------
@app.route('/')
def home():
    return redirect(url_for('register'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    logo_url = get_logo_url()
    if request.method == 'POST':
        # Collect fields
        name = request.form.get('name', '').strip()
        if not name:
            flash('Name is required', 'danger')
            return redirect(url_for('register'))

        member = Member(
            name=name,
            other_name=request.form.get('other_name', '').strip(),
            location=request.form.get('location', '').strip(),
            home_location=request.form.get('home_location', '').strip(),
            phone=request.form.get('phone', '').strip(),
            religion=request.form.get('religion', '').strip(),
            church_name=request.form.get('church_name', '').strip(),
            profession=request.form.get('profession', '').strip(),
            skills=request.form.get('skills', '').strip(),
            gifts=request.form.get('gifts', '').strip(),
            experience=request.form.get('experience', '').strip(),
            departments=",".join(request.form.getlist('departments')) if request.form.getlist('departments') else "",
            referees_json=json.dumps([
                {
                    'name': request.form.get('ref1_name', '').strip(),
                    'location': request.form.get('ref1_location', '').strip(),
                    'phone': request.form.get('ref1_phone', '').strip(),
                },
                {
                    'name': request.form.get('ref2_name', '').strip(),
                    'location': request.form.get('ref2_location', '').strip(),
                    'phone': request.form.get('ref2_phone', '').strip(),
                }
            ])
        )
        db.session.add(member)
        db.session.commit()
        flash('Registration submitted! Await admin approval.', 'success')
        return redirect(url_for('register'))

    return render_template('register.html', logo_url=logo_url)


# -------------------- Routes (Admin) --------------------
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        user = AdminUser.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Welcome back!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template('admin_login.html')

@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    flash('Logged out.', 'info')
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    logo_url = get_logo_url()
    total = db.session.scalar(db.select(func.count()).select_from(Member))
    total_approved = db.session.scalar(db.select(func.count()).select_from(Member).where(Member.approved == True))
    total_pending = pending_count()
    new_count = new_since_last_seen_count()
    # latest 5 pending
    latest_pending = Member.query.filter_by(approved=False).order_by(Member.created_at.desc()).limit(5).all()
    return render_template(
        'admin_dashboard.html',
        logo_url=logo_url,
        total=total, total_approved=total_approved, total_pending=total_pending,
        new_count=new_count, latest_pending=latest_pending
    )

@app.route('/admin/members')
@login_required
def admin_members():
    status = request.args.get('status', 'all')
    q = Member.query.order_by(Member.created_at.desc())
    if status == 'approved':
        q = q.filter_by(approved=True)
    elif status == 'pending':
        q = q.filter_by(approved=False)
    members = q.all()

    # Mark notifications seen: set last_seen_member_id to current max id
    max_id = db.session.scalar(db.select(func.max(Member.id)))
    if max_id:
        Meta.set('last_seen_member_id', str(max_id))

    return render_template('admin_members.html', members=members)

@app.route('/admin/approve/<int:member_id>', methods=['POST'])
@login_required
def admin_approve(member_id):
    m = Member.query.get_or_404(member_id)
    m.approved = True
    db.session.commit()
    flash(f'{m.name} approved.', 'success')
    return redirect(request.referrer or url_for('admin_members'))

@app.route('/admin/delete/<int:member_id>', methods=['POST'])
@login_required
def admin_delete(member_id):
    m = Member.query.get_or_404(member_id)
    db.session.delete(m)
    db.session.commit()
    flash('Member deleted.', 'warning')
    return redirect(request.referrer or url_for('admin_members'))

@app.route('/admin/print/<int:member_id>')
@login_required
def admin_print(member_id):
    m = Member.query.get_or_404(member_id)
    return render_template('print_member.html', m=m, referees=json.loads(m.referees_json or '[]'))

@app.route('/admin/settings', methods=['GET', 'POST'])
@login_required
def admin_settings():
    msg = None
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'logo':
            file = request.files.get('logo')
            if file and allowed_logo(file.filename):
                filename = secure_filename(file.filename)
                save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(save_path)
                Meta.set('logo_path', save_path)
                flash('Logo uploaded successfully.', 'success')
            else:
                flash('Invalid logo file.', 'danger')

        elif action == 'creds':
            new_user = request.form.get('username', '').strip()
            new_pass = request.form.get('password', '').strip()
            if new_user and new_pass:
                u = AdminUser.query.first()
                if not u:
                    u = AdminUser(username=new_user)
                    db.session.add(u)
                else:
                    u.username = new_user
                u.set_password(new_pass)
                db.session.commit()
                flash('Admin credentials updated.', 'success')
            else:
                flash('Username and Password are required.', 'danger')

    logo_url = get_logo_url()
    current_admin = AdminUser.query.first()
    return render_template('admin_settings.html', logo_url=logo_url, admin=current_admin)

# -------------------- Static for favicon (optional) --------------------
@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static', 'favicon.ico', mimetype='image/vnd.microsoft.icon')

# -------------------- Main --------------------
if __name__ == "__main__":
    app.run()
