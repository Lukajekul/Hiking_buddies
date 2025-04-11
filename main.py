from flask import Flask, render_template, request

app = Flask(__name__)

@app.route("/")
def index():
    ime = request.args.get("ime")
    geslo = request.args.get("geslo")

app.run(debug=True)