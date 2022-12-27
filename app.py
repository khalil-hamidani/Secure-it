from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import login_required
from cs50 import SQL

app = Flask(__name__)

app.config["TEMPLATES_AUTO_RELOAD"] = True

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

db = SQL("sqlite:///secure.db")

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/")
def index():
    return render_template("index.html",nav=True)


@app.route("/encryption")
@login_required
def encryption():
    return render_template("encryption.html",nav=True)


@app.route("/decryption")
@login_required
def decryption():
    return render_template("decryption.html",nav=True)


@app.route("/passwordGen")
@login_required
def passwordGen():
    return render_template("passwordsGen.html",nav=True)


@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    if request.method == "GET":
        return render_template("login.html")
    else:
        username = request.form.get("username")
        password = request.form.get("password")
        if not username:
            return error("No user name is providedd !")
        elif not password:
            return error("No Password is providedd !")
        exist = db.execute("SELECT * FROM users WHERE name = ?",username)
        if len(exist) < 0 or not check_password_hash(exist[0]["hash"],password):
            return error("invalid username or password !")
        session["user_id"] = exist[0]["id"] 
        return redirect("/")
        
        
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    else:
        username = request.form.get("username")
        password = request.form.get("password")
        check = request.form.get("check")
        if not username:
            return error("No user name is providedd !")
        elif not password:
            return error("No Password is providedd !")
        elif not check or password != check:
            return error("passwords are not matched !")
        exist = db.execute("SELECT name FROM users WHERE name = ?",username)
        if len(exist) > 0:
            return error("user name already exists")
        hash = generate_password_hash(password)
        db.execute("INSERT INTO users (name,hash) VALUES(?,?)",username,hash)
        session["user_id"] = db.execute("SELECT id FROM users WHERE name = ?",username)[0]["id"]
        return redirect("/")
        
         
def error(msg):
    return render_template("bad.html",msg=msg)

if __name__ == "__main__":
    app.run(debug=True)