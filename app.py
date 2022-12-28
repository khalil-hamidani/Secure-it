import os

from flask import Flask, flash, jsonify, redirect, render_template, request ,session

app = Flask(__name__)
@app.route("/login")
def login():

    return render_template("login.html")

