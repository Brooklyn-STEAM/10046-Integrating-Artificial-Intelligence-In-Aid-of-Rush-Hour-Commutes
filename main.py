from flask import Flask, render_template, request, redirect, flash, abort, session, url_for
import flask_login
import pymysql
from dynaconf import Dynaconf
from datetime import datetime, timedelta
from functools import wraps
import random
import string

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

        if result is None or password != result["password"]:
            flash("Username or password is incorrect")
        else:
            user = User(result["id"], result["username"], result["email"])

            cursor.execute(f"SELECT * FROM `Admin` WHERE `id` = {result['id']};")
            admin_data = cursor.fetchone()

            if admin_data:
                session['is_admin'] = True  
            else:
                session['is_admin'] = False

            flask_login.login_user(user)
            return redirect('/')

    return render_template("signin.html.jinja")

@app.route('/logout')
def logout():
    flask_login.logout_user()
    return  redirect('/')

@app.route("/settings", methods=["GET", "POST"])
@flask_login.login_required
def settings():
    if request.method == "POST":
        new_username = request.form.get("username")
        new_email = request.form.get("email")
        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")
        confirm_new_password = request.form.get("confirm_new_password")

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM `Customer` WHERE `id` = {flask_login.current_user.id};")
        user_data = cursor.fetchone()

        if current_password != user_data["password"]:
            flash("Current password is incorrect.")
            return redirect("/settings")

        if new_password and new_password != confirm_new_password:
            flash("New passwords do not match.")
            return redirect("/settings")

        try:
            if new_username:
                cursor.execute(f"""
                    UPDATE `Customer`
                    SET `username` = '{new_username}'
                    WHERE `id` = {flask_login.current_user.id};
                """)

            if new_email:
                cursor.execute(f"""
                    UPDATE `Customer`
                    SET `email` = '{new_email}'
                    WHERE `id` = {flask_login.current_user.id};
                """)

            if new_password:
                cursor.execute(f"""
                    UPDATE `Customer`
                    SET `password` = '{new_password}'
                    WHERE `id` = {flask_login.current_user.id};
                """)

            flash("Your settings have been updated successfully.")
        except pymysql.err.IntegrityError:
            flash("Sorry, that username or email is already in use.")
        finally:
            cursor.close()
            conn.close()

        return redirect("/settings")

    return render_template("accountpage.html.jinja", user=flask_login.current_user)



@app.route("/admin")
@flask_login.login_required
def admin():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute(f"""
        SELECT * FROM `Admin` 
        WHERE `id` = {flask_login.current_user.id};
    """)
    admin_data = cursor.fetchone()

    if not admin_data:
        abort(403)  

    cursor.execute("SELECT first_name, last_name, state, issue FROM `Contactus`;")
    contactus_data = cursor.fetchall()

    cursor.execute("""
        SELECT username, email, time_stamp 
        FROM `Customer` 
        WHERE id NOT IN (SELECT id FROM `Admin`);
    """)
    customer_data = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "admin.html.jinja", 
        Contactus_data=contactus_data, 
        customer_data=customer_data
    )

@app.route("/admin/signin", methods=["GET", "POST"])
def admin_signin():
    if request.method == "POST":
        username = request.form['username'].strip()
        password = request.form['password']

        conn = connect_db()
        cursor = conn.cursor()


        cursor.execute(f"""
            SELECT * FROM `Admin` 
            WHERE `username` = '{username}' AND `password` = '{password}';
        """)
        admin_data = cursor.fetchone()

        if admin_data:

            user = User(admin_data["id"], admin_data["username"], admin_data["email"])
            flask_login.login_user(user)
            session['is_admin'] = True
            return redirect("/admin")
        else:
            flash("Invalid admin credentials")

    return render_template("admin_signin.html.jinja")

