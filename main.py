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

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# FIRST configure the app ⬇️
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///izleti.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# THEN create database instance ⬇️
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

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
    created_izlets = db.relationship('Izlet', back_populates='creator')

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

# Asociacijska tabela mora biti definirana ZUNAJ razredov
izlet_participants = db.Table('izlet_participants',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('izlet_id', db.Integer, db.ForeignKey('izlet.id'), primary_key=True)
)

class Izlet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ciljna_tocka = db.Column(db.String(100), nullable=False)
    datum = db.Column(db.Date, nullable=False)
    tip_vrha = db.Column(db.String(50))
    tezavnost = db.Column(db.String(20))
    ferata = db.Column(db.String(20), default='Ne')
    cas_hoje = db.Column(db.Float)
    iskane_osebe = db.Column(db.Integer)
    
    # Povezave
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    creator = db.relationship('User', back_populates='created_izlets')
    participants = db.relationship('User', secondary=izlet_participants, backref=db.backref('prijavljeni_izleti', lazy='dynamic'))
    
    # Ostala polja
    opis = db.Column(db.Text)
    status = db.Column(db.String(20), default='aktivno')

@app.route('/')
def index():
    today = datetime.today().date()
    valid_izleti = Izlet.query.filter(Izlet.datum >= today).order_by(Izlet.datum).all()
    return render_template("izleti.html", izleti=valid_izleti)

@app.route('/dodaj_izlet', methods=['POST'])
def dodaj_izlet():
    try:
        # Parse and validate date
        datum_str = request.form['datum']
        try:
            datum_obj = datetime.strptime(datum_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'error': 'Neveljaven format datuma.'}), 400

        # Handle 'cas_hoje'
        cas_hoje_str = request.form.get('cas_hoje', '')
        if cas_hoje_str == '' or cas_hoje_str is None:
            cas_hoje_value = 0.0
        else:
            try:
                cas_hoje_value = float(cas_hoje_str)
            except ValueError:
                return jsonify({'success': False, 'error': 'Neveljavna vrednost za čas hoje.'}), 400

        # Handle 'iskane_osebe'
        iskane_osebe_str = request.form.get('iskane_osebe', '')
        if iskane_osebe_str == '' or iskane_osebe_str is None:
            iskane_osebe_value = 0
        else:
            try:
                iskane_osebe_value = int(iskane_osebe_str)
            except ValueError:
                return jsonify({'success': False, 'error': 'Neveljavna vrednost za število iskanih oseb.'}), 400

        # Create new Izlet
        new_izlet = Izlet(
            ciljna_tocka=request.form['ciljna_tocka'],
            datum=datum_obj,
            tip_vrha=request.form.get('tip_vrha', ''),
            tezavnost=request.form.get('tezavnost', ''),
            ferata=request.form.get('ferata', 'Ne'),
            cas_hoje=cas_hoje_value,
            iskane_osebe=iskane_osebe_value
        )

        # Validation: date not in past
        if new_izlet.datum < datetime.today().date():
            return jsonify({'success': False, 'error': 'Datum ne sme biti v preteklosti'}), 400

        db.session.add(new_izlet)
        db.session.commit()

        # Return the data to update front-end
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
        # Log the exception for debugging
        print(f"Error in dodaj_izlet: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400

def create_tables():
    with app.app_context():
        db.create_all()



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)