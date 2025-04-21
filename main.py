from flask import Flask, render_template, request, redirect, url_for, session
from tinydb import TinyDB, Query
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

@app.route("/")
def home():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = db.get(User.username == username)

        if user and check_password_hash(user["password"], password):
            session["username"] = username
            return redirect(url_for("dashboard"))
        return "Invalid credentials"
    return render_template("login.html")

@app.route("/signup", methods=["POST"])
def signup():
    username = request.form["username"]
    password = request.form["password"]
    if db.contains(User.username == username):
        return "Username already exists"
    db.insert({
        "username": username,
        "password": generate_password_hash(password)
    })
    return redirect(url_for("login"))

@app.route("/dashboard")
def dashboard():
    if "username" in session:
        return f"Welcome, {session['username']}! <a href='/logout'>Logout</a>"
    return redirect(url_for("login"))

@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))


app.run(debug=True)