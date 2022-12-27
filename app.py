import os
from flask import Flask, flash, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import login_required


app = Flask(__name__)
@app.route("/")
def index():
    return render_template("index.html",nav=True)


@app.route("/encryption")
def encryption():
    return render_template("encryption.html",nav=True)


@app.route("/decryption")
def decryption():
    return render_template("decryption.html",nav=True)


@app.route("/passwordGen")
def passwordGen():
    return render_template("passwordsGen.html",nav=True)


@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/register")
def register():
    return render_template("register.html")


if __name__ == "__main__":
    app.run(debug=True)