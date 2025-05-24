from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
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
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///izleti.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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
        # Convert form data
        new_izlet = Izlet(
            ciljna_tocka=request.form['ciljna_tocka'],
            datum=datetime.strptime(request.form['datum'], '%Y-%m-%d').date(),
            tip_vrha=request.form.get('tip_vrha', ''),
            tezavnost=request.form.get('tezavnost', ''),
            ferata=request.form.get('ferata', 'Ne'),
            cas_hoje=float(request.form.get('cas_hoje', 0)),
            iskane_osebe=int(request.form.get('iskane_osebe', 0))
        )

        # Validate date
        if new_izlet.datum < datetime.today().date():
            return jsonify({'success': False, 'error': 'Datum ne sme biti v preteklosti'}), 400
        
        db.session.add(new_izlet)
        db.session.commit()
        
        # Return the new izlet data for JavaScript
        return jsonify({
            'success': True,
            'izlet': {
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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
    create_tables()
    app.run(debug=True)

app.run(debug=True)