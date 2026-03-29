import os
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import db, User, PregnancyData, BabyData, HealthLog, Reminder, HealthReport, DoctorProfile, PharmacyItem, GovScheme, JobOpportunity, MentalHealthLog

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
app.config['SECRET_KEY'] = 'smarter_maternal_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///maternal.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Routes ---

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        email_or_phone = request.form.get('email_or_phone')
        password = request.form.get('password')
        
        # Check by email or phone
        user = User.query.filter((User.email == email_or_phone) | (User.phone == email_or_phone)).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid login credentials. Please try again.', 'error')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        role = request.form.get('role', 'Mother')
        
        user_exists = User.query.filter((User.email == email) & (email != '') | (User.phone == phone) & (phone != '')).first()
        if user_exists:
            flash('Email or Phone already exists.', 'error')
            return redirect(url_for('register'))
            
        new_user = User(
            name=name,
            email=email if email else None,
            phone=phone if phone else None,
            password_hash=generate_password_hash(password, method='pbkdf2:sha256'),
            role=role
        )
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)

@app.route('/pre-maternal')
@login_required
def pre_maternal():
    return render_template('pre_maternal.html', user=current_user)

@app.route('/pregnancy-tracker')
@login_required
def pregnancy_tracker():
    pregnancy = PregnancyData.query.filter_by(user_id=current_user.id).first()
    return render_template('pregnancy_tracker.html', user=current_user, pregnancy=pregnancy)

@app.route('/post-maternal')
@login_required
def post_maternal():
    return render_template('post_maternal.html', user=current_user)

@app.route('/baby-care')
@login_required
def baby_care():
    baby = BabyData.query.filter_by(user_id=current_user.id).first()
    return render_template('baby_care.html', user=current_user, baby=baby)

@app.route('/ai-assistant', methods=['GET', 'POST'])
@login_required
def ai_assistant():
    if request.method == 'POST':
        user_msg = request.form.get('message', '').lower()
        response = "I'm here to support you. Could you share more details?"
        
        if 'anxiety' in user_msg or 'stress' in user_msg or 'insomnia' in user_msg:
            response = "🌿 Natural Remedy: Try deep breathing exercises or drinking warm chamomile tea. ⚕️ Medical Guidance: If this persists for more days, please consult your doctor immediately."
        elif 'constipation' in user_msg or 'bloating' in user_msg:
            response = "🌿 Natural Remedy: Increase your fiber intake (fruits, vegetables) and drink plenty of water. ⚕️ Medical Guidance: Avoid laxatives unless prescribed by your doctor."
        elif 'headache' in user_msg or 'dizziness' in user_msg:
            response = "🌿 Natural Remedy: Rest in a dark, quiet room and stay hydrated. ⚕️ Medical Guidance: Severe headaches can be a sign of high blood pressure. Alert your doctor."
        elif 'back pain' in user_msg or 'cramps' in user_msg:
            response = "🌿 Natural Remedy: Use a warm compress and practice gentle prenatal stretching. ⚕️ Medical Guidance: If cramps are severe or accompanied by bleeding, seek emergency medical help immediately."
        return {'bot_response': response}
    return render_template('ai_assistant.html', user=current_user)

@app.route('/risk-assessment')
@login_required
def risk_assessment():
    logs = HealthLog.query.filter_by(user_id=current_user.id).order_by(HealthLog.date.desc()).all()
    risk_profile = {
        'anemia': 'Low Risk',
        'gestational_diabetes': 'Low Risk',
        'hypertension': 'Low Risk',
        'warnings': []
    }
    for log in logs:
        if log.blood_pressure:
            parts = log.blood_pressure.split('/')
            if len(parts) == 2 and parts[0].isdigit() and int(parts[0]) > 130:
                risk_profile['hypertension'] = 'High Risk 🚨'
                risk_profile['warnings'].append("High systolic blood pressure detected.")
        if log.symptoms:
            syms = log.symptoms.lower()
            if 'fatigue' in syms or 'pale' in syms:
                risk_profile['anemia'] = 'Moderate Risk ⚠️'
                risk_profile['warnings'].append("Symptoms suggest possible Anemia.")
            if 'excessive thirst' in syms or 'frequent urination' in syms:
                risk_profile['gestational_diabetes'] = 'Moderate Risk ⚠️'
                risk_profile['warnings'].append("Symptoms suggest possible Gestational Diabetes.")
    
    return render_template('risk_assessment.html', user=current_user, risks=risk_profile)

@app.route('/scheduler', methods=['GET', 'POST'])
@login_required
def scheduler():
    if request.method == 'POST':
        title = request.form.get('title')
        time_sche = request.form.get('time')
        rtype = request.form.get('type')
        rem = Reminder(user_id=current_user.id, title=title, time_scheduled=time_sche, type=rtype)
        db.session.add(rem)
        db.session.commit()
        return redirect(url_for('scheduler'))
        
    reminders = Reminder.query.filter_by(user_id=current_user.id).all()
    return render_template('scheduler.html', user=current_user, reminders=reminders)

@app.route('/emergency')
@login_required
def emergency():
    return render_template('emergency.html', user=current_user)

@app.route('/reports', methods=['GET', 'POST'])
@login_required
def reports():
    if request.method == 'POST':
        if 'report_file' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)
        file = request.files['report_file']
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)
        if file:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            title = request.form.get('title', 'Medical Report')
            r = HealthReport(user_id=current_user.id, title=title, file_path=filename)
            db.session.add(r)
            db.session.commit()
            return redirect(url_for('reports'))
            
    all_reports = HealthReport.query.filter_by(user_id=current_user.id).all()
    return render_template('reports.html', user=current_user, reports=all_reports)

@app.route('/safe-route')
@login_required
def safe_route():
    return render_template('safe_route.html', user=current_user)

@app.route('/doctors')
@login_required
def doctors():
    docs = DoctorProfile.query.all()
    return render_template('doctors.html', user=current_user, doctors=docs)

@app.route('/pharmacy')
@login_required
def pharmacy():
    items = PharmacyItem.query.all()
    return render_template('pharmacy.html', user=current_user, items=items)

@app.route('/schemes')
@login_required
def schemes():
    all_schemes = GovScheme.query.all()
    return render_template('schemes.html', user=current_user, schemes=all_schemes)

@app.route('/mental-health', methods=['GET', 'POST'])
@login_required
def mental_health():
    if request.method == 'POST':
        mood = request.form.get('mood')
        if mood:
            log = MentalHealthLog(user_id=current_user.id, mood=mood)
            db.session.add(log)
            db.session.commit()
            flash('Mood logged successfully!', 'success')
            return redirect(url_for('mental_health'))
    logs = MentalHealthLog.query.filter_by(user_id=current_user.id).order_by(MentalHealthLog.date.desc()).all()
    return render_template('mental_health.html', user=current_user, logs=logs)

@app.route('/empowerment')
@login_required
def empowerment():
    jobs = JobOpportunity.query.all()
    return render_template('empowerment.html', user=current_user, jobs=jobs)

with app.app_context():
    db.create_all()
    if not DoctorProfile.query.first():
        docs = [
            DoctorProfile(name='Dr. Kamini A. Rao', specialty='Obstetrician & Gynaecologist', hospital='Milann Fertility Center', rating=4.9, fee=1500),
            DoctorProfile(name='Dr. Prathima Radhakrishnan', specialty='Fetal Medicine Specialist', hospital='Bangalore Fetal Medicine Centre', rating=4.8, fee=2000),
            DoctorProfile(name='Dr. Ritu Sethi', specialty='Gynaecologist', hospital='Cloudnine Hospital', rating=4.7, fee=1000)
        ]
        db.session.add_all(docs)
        db.session.commit()
    if not PharmacyItem.query.first():
        meds = [
            PharmacyItem(name='Folvite 5mg Tablet', category='Folic Acid / Vitamins', price=65),
            PharmacyItem(name='Shelcal 500 Tablet', category='Calcium Supplements', price=110),
            PharmacyItem(name='Dexorange Syrup 200ml', category='Iron / Hemoglobin', price=145),
            PharmacyItem(name='DHA Forte Capsule', category='Omega 3 / Brain Development', price=250),
            PharmacyItem(name='Omez 20mg Capsule', category='Antacid', price=55)
        ]
        db.session.add_all(meds)
        db.session.commit()
    if not GovScheme.query.first():
        scheme_list = [
            GovScheme(name='Pradhan Mantri Matru Vandana Yojana (PMMVY)', description='Maternity benefit program providing conditional cash transfer.', eligibility='Pregnant women aged 19 and above for the first living child.', benefit='₹5000 in three installments'),
            GovScheme(name='Janani Suraksha Yojana (JSY)', description='Safe motherhood intervention designed to reduce maternal and neonatal mortality.', eligibility='BPL pregnant women, prioritizing institutional delivery.', benefit='₹1400 (Rural) / ₹1000 (Urban) cash assistance')
        ]
        db.session.add_all(scheme_list)
        db.session.commit()
    if not JobOpportunity.query.first():
        j = [
            JobOpportunity(title='Remote Customer Support', company='Amazon India', job_type='Remote Part-Time', salary='₹15,000/month'),
            JobOpportunity(title='Handicraft Artisan Partner', company='FabIndia', job_type='Flexible Freelance', salary='Per Piece Commission'),
            JobOpportunity(title='Virtual Data Entry Operator', company='Tech Mahindra', job_type='Remote Full-Time', salary='₹20,000/month')
        ]
        db.session.add_all(j)
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
