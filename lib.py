# Import the tools we need from Flask and Python
from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import webbrowser

# Initialize the Flask application
app = Flask(__name__)

# A secret key is required by Flask to keep user sessions safe and encrypted
app.secret_key = 'super_secret_key_for_library_system'

# Define our database file name
DB_NAME = 'library.db'

# ==========================================
# 1. DATABASE SETUP FUNCTION
# ==========================================
def init_db():
    # Connect to SQLite database (creates 'library.db' automatically if it doesn't exist)
    with sqlite3.connect(DB_NAME) as conn:
        
        # Create 'users' table to store account info
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT DEFAULT 'member'
            )
        ''')
        
        # Create 'books' table to store the library inventory
        conn.execute('''
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                available_copies INTEGER NOT NULL
            )
        ''')
        
        # Create 'transactions' table to track who borrowed what and when
        conn.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER,
                user_id INTEGER,
                borrow_date TEXT,
                FOREIGN KEY(book_id) REFERENCES books(id),
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        
        # Check if the books table is empty; if so, add sample books automatically
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM books")
        if cursor.fetchone()[0] == 0:
            conn.execute("INSERT INTO books (title, author, available_copies) VALUES (?, ?, ?)", 
                           ("Python Programming for Beginners", "John Smith", 5))
            conn.execute("INSERT INTO books (title, author, available_copies) VALUES (?, ?, ?)", 
                           ("Data Structures Made Easy", "Jane Doe", 3))

# ==========================================
# 2. ROUTE: HOME PAGE (LOGIN / WELCOME)
# ==========================================
@app.route('/')
def home():
    return render_template('index.html')

# ==========================================
# 3. ROUTE: USER REGISTRATION
# ==========================================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
        try:
            with sqlite3.connect(DB_NAME) as conn:
                conn.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", (name, email, password))
            return render_template('register.html', message="Registration successful! You can now login.")
        except sqlite3.IntegrityError:
            return render_template('register.html', message="Email already exists!")
            
    return render_template('register.html')

# ==========================================
# 4. ROUTE: USER LOGIN
# ==========================================
@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
        user = cursor.fetchone()
        
        if user:
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            return redirect(url_for('dashboard'))
        else:
            return render_template('index.html', error="Invalid email or password")

# ==========================================
# 5. ROUTE: DASHBOARD (BOOK CATALOG)
# ==========================================
@app.route('/dashboard')
def dashboard():
    if 'user_name' not in session:
        return redirect(url_for('home'))
        
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM books")
        books = cursor.fetchall()
        
    return render_template('dashboard.html', name=session['user_name'], books=books)

# ==========================================
# 6. ROUTE: BORROW BOOK ACTION
# ==========================================
@app.route('/borrow/<int:book_id>')
def borrow_book(book_id):
    if 'user_id' not in session:
        return redirect(url_for('home'))
        
    user_id = session['user_id']
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT available_copies FROM books WHERE id = ?", (book_id,))
        book = cursor.fetchone()
        
        if book and book[0] > 0:
            conn.execute("UPDATE books SET available_copies = available_copies - 1 WHERE id = ?", (book_id,))
            conn.execute("INSERT INTO transactions (book_id, user_id, borrow_date) VALUES (?, ?, datetime('now'))", (book_id, user_id))
            conn.commit()
            
    return redirect(url_for('dashboard'))

# ==========================================
# 7. ROUTE: LOGOUT
# ==========================================
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# ==========================================
# RUN THE APPLICATION
# ==========================================
if __name__ == '__main__':
    init_db()
    webbrowser.open('http://127.0.0.1:5000')
    app.run(debug=True)