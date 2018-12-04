from flask import Flask, render_template
from . import app

@app.route("/")
def home():
    return render_template("main.html")

@app.route("/api/data")
def get_data():
    return app.send_static_file("data.json")
