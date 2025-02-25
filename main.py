from flask import Flask, render_template, request, redirect, flash, abort
import flask_login
import pymysql
from dynaconf import Dynaconf
from datetime import datetime

app = Flask(__name__)

conf = Dynaconf(
    settings_file = ["settings.toml"]
)

app = Flask(__name__)
app.secret_key = conf.secret_key

login_manager = flask_login.LoginManager()
login_manager.init_app(app)

def connect_db():
    conn = pymysql.connect(
        host = "db.steamcenter.tech",
        database = "clear_path",
        user = "nshovo",
        password = conf.password,
        autocommit = True,
        cursorclass= pymysql.cursors.DictCursor
    )

    return conn

class User:
    is_authenticated = True
    is_anonymous = False
    is_active = True

    def __init__(self, user_id, username, email):
        self.id = user_id
        self.username = username
        self.email = email

    def get_id(self):
        return str(self.id)

@login_manager.user_loader
def load_user(user_id):
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute(f"SELECT * FROM `Customer` WHERE `id` = {user_id};")

    result = cursor.fetchone()

    cursor.close
    conn.close

    if result is not None:
        return User(result["id"], result["username"], result["email"])

@app.route("/")
def index():
    return render_template("homepage.html.jinja")


@app.route("/signup", methods=["POST", "GET"])
def signup():
    if flask_login.current_user.is_authenticated:
        return redirect("/")
    
    if request.method == 'POST':
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        conn = connect_db()
    
        cursor = conn.cursor()
        
        if confirm_password != password:
            flash("Passwords does not match")
        
        if len(password)< 12 :
            flash("Your password must be at least 12 characters ")
            return render_template("signup.html.jinja")

        try:
            cursor.execute(f"""
                INSERT INTO `Customer` 
                    ( `username`, `email`, `password`)
                VALUES
                    ( '{username}', '{email}', '{password}' );
            """)

        except pymysql.err.IntegrityError:
            flash("sorry, that username/email is already in use")
        
        else: 
            return redirect("/signin")
        
        finally:
            cursor.close
            conn.close

        return redirect("/signin")
    return render_template("signup.html.jinja")
    

@app.route("/signin", methods=["POST", "GET"])
def signin():
    if flask_login.current_user.is_authenticated:
        return redirect("/")

    if request.method == "POST":
        username = request.form['username'].strip()
        password = request.form['password']

        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute(f"SELECT * FROM `Customer` WHERE `username` = '{username}';")

        result = cursor.fetchone()

        if result is None: 
            flash("username or password is incorrect")
        elif password != result["password"]:
            flash("username or password is incorrect")
        else:
            user = User(result["id"], result["username"], result["email"], result["first_name"], result["last_name"])

            flask_login.login_user(user)
            
            return redirect('/')


    return render_template("signin.html.jinja")