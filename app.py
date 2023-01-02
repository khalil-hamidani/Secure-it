from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import login_required
from cs50 import SQL
import re

app = Flask(__name__)

app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

db = SQL("sqlite:///secure.db")
pass_pat = re.compile(r"[A-Za-z0-9]+") #! To avoid SQL injections
user_pat = re.compile(r"[A-Za-z0-9]+\_?[A-Za-z0-9]") #! To avoid SQL injections

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
def index():
    user = "Account"
    if session.get("user_id"):
        user = db.execute("SELECT name FROM users WHERE id = ?",session["user_id"])[0]
    return render_template("index.html",nav=True,user=user)


@app.route("/encryption")
@login_required
def encryption():
    user = "Account"
    if session.get("user_id"):
        user = db.execute("SELECT name FROM users WHERE id = ?",session["user_id"])[0]
    return render_template("encryption.html",nav=True,user=user)


@app.route("/decryption")
@login_required
def decryption():
    user = "Account"
    if session.get("user_id"):
        user = db.execute("SELECT name FROM users WHERE id = ?",session["user_id"])[0]
    return render_template("decryption.html",nav=True,user=user)


@app.route("/passwordGen")
@login_required
def passwordGen():
    user = "Account"
    if session.get("user_id"):
        user = db.execute("SELECT name FROM users WHERE id = ?",session["user_id"])[0]
    return render_template("passwordsGen.html",nav=True,user=user)


@app.route("/passwordMan",methods=["GET", "POST"])
@login_required
def passwordMan():
    user = "Account"
    if session.get("user_id"):
        user = db.execute("SELECT name FROM users WHERE id = ?",session["user_id"])[0]
    if request.method == "GET":
        accounts = db.execute("SELECT * FROM passwords WHERE user_id = ?",session["user_id"])
        return render_template("passwordMan.html",nav=True,accounts=accounts,user=user)
    else:
        accountName = request.form.get("name")
        accountPassword = request.form.get("password")
        accountLink = request.form.get("link")
        if not accountName:
            return error("No account name is providedd !")
        elif not accountPassword:
            return error("No account Password is providedd !")
        elif not accountLink:
            return error("No account Link is providedd !")
        db.execute("INSERT INTO passwords (user_id,name,link,password) VALUES (?,?,?,?);",session["user_id"],accountName,accountLink,accountPassword)
        return redirect("/passwordMan")


@app.route("/goupdate", methods=["GET", "POST"])
def goUpdate():
    id = request.form.get("id")
    account = db.execute("SELECT * FROM passwords WHERE user_id = ? AND id = ?",session["user_id"],id)[0]
    return render_template("update.html",account=account)
          
            
@app.route("/update", methods=["POST"])
def update():
    if request.method == "POST":
        id = request.form.get("id")
        name = request.form.get("name")
        password = request.form.get("password")
        link = request.form.get("link")
        if id and name and password and link:
            db.execute("UPDATE passwords SET name=?,password=?,link=? WHERE id=? AND user_id = ?;",name,password,link,id,session["user_id"])
            return redirect("/passwordMan")
        else:
            return error("Something wrong !")


@app.route("/delete", methods=["POST"])
def delete():
    if request.method == "POST":
        id = request.form.get("id")
        if id :
            db.execute("DELETE FROM passwords WHERE id = ?;",id)
        return redirect("/passwordMan")


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
        elif not re.fullmatch(pass_pat, password):
            return error("Invalid password 🤨 !")
        elif not re.fullmatch(user_pat, username):
            return error("Invalid user name 🤨 !")
        exist = db.execute("SELECT * FROM users WHERE name = ?",username)
        if len(exist) < 1 or not check_password_hash(exist[0]["hash"],password):
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
        elif not re.fullmatch(pass_pat, password):
            return error("Invalid password 🤨 !")
        elif not re.fullmatch(user_pat, username):
            return error("Invalid user name 🤨 !")
        exist = db.execute("SELECT name FROM users WHERE name = ?",username)
        if len(exist) > 0:
            return error("user name already exists")
        hash = generate_password_hash(password)
        db.execute("INSERT INTO users (name,hash) VALUES(?,?)",username,hash)
        session["user_id"] = db.execute("SELECT id FROM users WHERE name = ?",username)[0]["id"]
        return redirect("/")
        

@app.route("/user")
@login_required
def user():
    user = "Account"
    if session.get("user_id"):
        user = db.execute("SELECT * FROM users WHERE id = ?",session["user_id"])[0]
        nbr = len(db.execute("SELECT * FROM passwords WHERE user_id = ?",session["user_id"]))
    return render_template("user.html",nav=True,user=user,nbr=nbr)


@app.route("/deleteAccount", methods=["POST"])
def deleteAccount():
    if request.method == "POST":
        id = request.form.get("id")
        if id :
            db.execute("DELETE FROM passwords WHERE user_id = ?;",session["user_id"])
            db.execute("DELETE FROM users WHERE id = ?;",session["user_id"])
            session.clear()
        return redirect("/")

def error(msg):
    return render_template("bad.html",msg=msg)

if __name__ == "__main__":
    app.run(debug=True)