from flask import Flask, render_template, request, redirect, session, send_file
import sqlite3
import uuid

app = Flask(__name__)
app.secret_key = "secret123"

# Database connection
def get_db():
    return sqlite3.connect("database.db")

# Initialize database
def init_db():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS projects(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            link TEXT,
            limit_count INTEGER
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS contacts(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            name TEXT,
            phone TEXT
        )
    """)
    db.commit()
    db.close()

init_db()

# Login
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form["username"]
        password = request.form["password"]
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT * FROM users WHERE username=? AND password=?", (user, password))
        data = cur.fetchone()
        if data:
            session["user_id"] = data[0]
            return redirect("/dashboard")
        else:
            return "❌ Invalid username/password"
    return render_template("login.html")

# Signup
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        user = request.form["username"]
        password = request.form["password"]
        db = get_db()
        cur = db.cursor()
        try:
            cur.execute("INSERT INTO users(username,password) VALUES(?,?)", (user, password))
            db.commit()
            return redirect("/")
        except:
            return "❌ Username already exists"
    return render_template("signup.html")

# Dashboard
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/")
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM projects WHERE user_id=?", (session["user_id"],))
    projects = cur.fetchall()
    return render_template("dashboard.html", projects=projects)

# Create VCF
@app.route("/create", methods=["GET", "POST"])
def create():
    if "user_id" not in session:
        return redirect("/")
    if request.method == "POST":
        name = request.form["name"]
        limit = int(request.form["limit"])
        unique_link = str(uuid.uuid4())[:8]
        db = get_db()
        cur = db.cursor()
        cur.execute(
            "INSERT INTO projects(user_id,name,link,limit_count) VALUES(?,?,?,?)",
            (session["user_id"], name, unique_link, limit)
        )
        db.commit()
        return redirect("/dashboard")
    return render_template("create.html")

# Add contact
@app.route("/add/<link>", methods=["GET", "POST"])
def add_contact(link):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM projects WHERE link=?", (link,))
    project = cur.fetchone()
    if not project:
        return "❌ Invalid link"
    project_id = project[0]
    limit_count = project[4]  # 0 = unlimited
    cur.execute("SELECT COUNT(*) FROM contacts WHERE project_id=?", (project_id,))
    count = cur.fetchone()[0]
    if limit_count == 0:
        remaining = "Unlimited"
    else:
        remaining = limit_count - count
        if remaining <= 0:
            return "❌ Contact limit reached"
    if request.method == "POST":
        name = request.form["name"]
        phone = request.form["phone"]
        if limit_count != 0 and count >= limit_count:
            return "❌ Contact limit reached"
        cur.execute("INSERT INTO contacts(project_id,name,phone) VALUES(?,?,?)",
                    (project_id, name, phone))
        db.commit()
        return f"✅ Contact added! Slots remaining: {remaining-1 if remaining != 'Unlimited' else 'Unlimited'}"
    return render_template("add_contact.html", project=project, remaining=remaining)

# Download VCF (Admin Only)
@app.route("/download/<int:project_id>")
def download(project_id):
    if "user_id" not in session:
        return redirect("/")
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM projects WHERE id=?", (project_id,))
    project = cur.fetchone()
    if project[1] != session["user_id"]:
        return "❌ Unauthorized"
    cur.execute("SELECT name,phone FROM contacts WHERE project_id=?", (project_id,))
    contacts = cur.fetchall()
    filename = f"{project[2]}.vcf"
    with open(filename, "w") as f:
        for c in contacts:
            f.write(f"""BEGIN:VCARD
VERSION:3.0
FN:{c[0]}
TEL;TYPE=CELL:{c[1]}
END:VCARD
""")
    return send_file(filename, as_attachment=True)

# Logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
