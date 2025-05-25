from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
import os
from werkzeug.utils import secure_filename
from tinydb import TinyDB, Query
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

UPLOAD_FOLDER = 'static/slike'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.secret_key = 'skrivnost'

csrf = CSRFProtect(app)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# FIRST configure the app ⬇️
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///izleti.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# THEN create database instance ⬇️
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


izlet_participants = db.Table('izlet_participants',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('izlet_id', db.Integer, db.ForeignKey('izlet.id'))
)

# ------------------ Model ------------------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    ime = db.Column(db.String(100))
    priimek = db.Column(db.String(100))
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    starost = db.Column(db.Integer)
    kraj = db.Column(db.String(100))
    vodic = db.Column(db.Boolean, default=False)
    drustvo = db.Column(db.Boolean, default=False)
    opis = db.Column(db.Text)
    slika = db.Column(db.String(200))  # ime datoteke slike


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ------------------ Registracija ------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        ime = request.form['ime']
        priimek = request.form['priimek']
        username = request.form['username']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        starost = int(request.form['starost'])
        kraj = request.form['kraj']
        vodic = 'vodic' in request.form
        drustvo = 'drustvo' in request.form
        opis = request.form['opis']

        file = request.files.get('slika')
        filename = None

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
        else:
            flash("Napaka pri nalaganju slike.")
            return redirect(request.url)

        # Preveri, če uporabnik že obstaja
        if User.query.filter_by(username=username).first():
            flash('Uporabniško ime je že zasedeno!')
            return redirect(url_for('register'))

        # Shrani novega uporabnika
        user = User(
            ime=ime,
            priimek=priimek,
            username=username,
            password=password,
            starost=starost,
            kraj=kraj,
            vodic=vodic,
            drustvo=drustvo,
            opis=opis,
            slika=filename
        )
        db.session.add(user)
        db.session.commit()
        flash('Registracija uspešna! Prijavi se.')

        return redirect(url_for('login'))
    return render_template('register.html')

# ------------------ Prijava ------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('profil'))
        flash('Napačno uporabniško ime ali geslo.')
    return render_template('login.html')


@app.route("/dashboard")
def dashboard():
    if "username" in session:
        return f"Welcome, {session['username']}! <a href='/logout'>Logout</a>"
    return redirect(url_for("login"))

# ------------------ Profil ------------------
@app.route('/profil')
@login_required
def profil():
    return render_template('profil.html', user=current_user)

# ------------------ Odjava ------------------
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Odjavljen si.')
    return redirect(url_for('login'))


class Izlet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ciljna_tocka = db.Column(db.String(100), nullable=False)
    datum = db.Column(db.Date, nullable=False)
    tip_vrha = db.Column(db.String(50))
    tezavnost = db.Column(db.String(20))
    ferata = db.Column(db.String(20))
    cas_hoje = db.Column(db.Float)
    iskane_osebe = db.Column(db.Integer)



@app.route('/')
def index():
    today = datetime.today().date()
    valid_izleti = Izlet.query.filter(Izlet.datum >= today).order_by(Izlet.datum).all()
    return render_template("izleti.html", izleti=valid_izleti)

@app.route('/dodaj_izlet', methods=['POST'])
def dodaj_izlet():
    try:
        new_izlet = Izlet(
            ciljna_tocka=request.form['ciljna_tocka'],
            datum=datetime.strptime(request.form['datum'], '%Y-%m-%d').date(),
            tip_vrha=request.form.get('tip_vrha', ''),
            tezavnost=request.form.get('tezavnost', 'Srednja'),
            ferata=request.form.get('ferata', 'Ne'),
            cas_hoje=float(request.form.get('cas_hoje', 0)),
            iskane_osebe=int(request.form.get('iskane_osebe', 1))
        )
        
        db.session.add(new_izlet)
        db.session.commit()
        
        # Return success with new izlet data
        return jsonify({
            'success': True,
            'message': 'Izlet uspešno dodan!',
            'izlet': {
                'id': new_izlet.id,
                'ciljna_tocka': new_izlet.ciljna_tocka,
                'datum': new_izlet.datum.strftime('%Y-%m-%d'),
                'tip_vrha': new_izlet.tip_vrha,
                'tezavnost': new_izlet.tezavnost,
                'ferata': new_izlet.ferata,
                'cas_hoje': new_izlet.cas_hoje,
                'iskane_osebe': new_izlet.iskane_osebe
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

def create_tables():
    with app.app_context():
        db.create_all()

class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    izlet_id = db.Column(db.Integer, db.ForeignKey('izlet.id'))
    messages = db.relationship('Message', backref='group', lazy=True)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))

@app.route('/get_groups')
def get_groups():
    groups = Group.query.all()
    return jsonify([{
        'id': group.id,
        'name': group.name
    } for group in groups])

@app.route('/get_messages/<int:group_id>')
def get_messages(group_id):
    messages = Message.query.filter_by(group_id=group_id).order_by(Message.timestamp).all()
    return jsonify([{
        'time': msg.timestamp.strftime('%H:%M'),
        'content': msg.content
    } for msg in messages])

@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.get_json()
    new_message = Message(
        group_id=data['group_id'],
        user_id=1,  # Replace with actual user ID
        content=data['content']
    )
    db.session.add(new_message)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/skupine')
def skupine():
    groups = Group.query.all()  # Make sure you have Group model defined
    return render_template("chat.html", groups=groups)

@app.route('/pro')
def pro():
    groups = Group.query.all()  # Make sure you have Group model defined
    return render_template("profil.html", groups=groups)

@app.route('/izl')
def izl():
    groups = Group.query.all()  # Make sure you have Group model defined
    return render_template("izleti.html", groups=groups)

@app.route('/join_izlet/<int:izlet_id>', methods=['POST'])
@login_required
def join_izlet(izlet_id):
    izlet = Izlet.query.get_or_404(izlet_id)
    
    # Check if date has passed
    if izlet.datum < datetime.today().date():
        return jsonify({'success': False, 'error': 'Datum izleta je že mimo!'})
    
    # Check if there are available spots
    current_participants = len(izlet.participants)
    if current_participants >= izlet.iskane_osebe:
        return jsonify({'success': False, 'error': 'Ni več prostih mest!'})
    
    # Add user to izlet
    if current_user not in izlet.participants:
        izlet.participants.append(current_user)
        db.session.commit()
        
        # Add to group chat automatically
        group = Group.query.filter_by(izlet_id=izlet.id).first()
        if not group:
            group = Group(name=izlet.ciljna_tocka, izlet_id=izlet.id)
            db.session.add(group)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Uspešno pridružen izletu!',
            'group_id': group.id
        })
    
    return jsonify({'success': False, 'error': 'Že sodelujete v tem izletu!'})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)