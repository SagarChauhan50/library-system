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
        # added status TEXT DEFAULT 'borrowed', to get return func in dash on 22/09/26
        conn.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER,
                user_id INTEGER,
                borrow_date TEXT,
                status TEXT DEFAULT 'borrowed',
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

# Initialize the database immediately so Render/Gunicorn picks it up on startup
init_db()

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
'''
@app.route('/dashboard')
def dashboard():
    if 'user_name' not in session:
        return redirect(url_for('home'))
        
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM books")
        books = cursor.fetchall()
        
    return render_template('dashboard.html', name=session['user_name'], books=books)
'''

# Updated dash 22/09/26

@app.route('/dashboard')
def dashboard():
    if 'user_name' not in session:
        return redirect(url_for('home'))
        
    user_id = session['user_id']
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        
        # 1. Get all books for the catalog table
        cursor.execute("SELECT * FROM books")
        books = cursor.fetchall()
        
        # 2. Get only the books currently borrowed by this logged-in user
        cursor.execute("""
            SELECT transactions.id, books.title, transactions.borrow_date 
            FROM transactions 
            JOIN books ON transactions.book_id = books.id 
            WHERE transactions.user_id = ? AND transactions.status = 'borrowed'
        """, (user_id,))
        borrowed_books = cursor.fetchall()
        
    return render_template('dashboard.html', name=session['user_name'], books=books, borrowed_books=borrowed_books)





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
# RUN THE APPLICATION LOCALLY
# ==========================================
if __name__ == '__main__':
    webbrowser.open('http://127.0.0.1:5000')
    app.run(debug=True)


# ==========================================
# EXTRA ROUTE: VIEW DATABASE LIVE (FOR VIVA)
# ==========================================
@app.route('/admin/view-data')
def view_data():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        
        # Get all registered users
        cursor.execute("SELECT id, name, email, role FROM users")
        users = cursor.fetchall()
        
        # Get all borrowing transactions
        cursor.execute("""
            SELECT transactions.id, users.name, books.title, transactions.borrow_date 
            FROM transactions 
            JOIN users ON transactions.user_id = users.id 
            JOIN books ON transactions.book_id = books.id
        """)
        transactions = cursor.fetchall()
        
    return render_template('admin.html', users=users, transactions=transactions)



# ==========================================
# ROUTE: RETURN BOOK ACTION                                   22/09/26
# ==========================================
@app.route('/return/<int:transaction_id>')
def return_book(transaction_id):
    if 'user_id' not in session:
        return redirect(url_for('home'))
        
    user_id = session['user_id']
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        
        # Check if the transaction belongs to this user and is active
        cursor.execute("SELECT book_id FROM transactions WHERE id = ? AND user_id = ? AND status = 'borrowed'", (transaction_id, user_id))
        transaction = cursor.fetchone()
        
        if transaction:
            book_id = transaction[0]
            
            # Mark transaction as returned
            conn.execute("UPDATE transactions SET status = 'returned' WHERE id = ?", (transaction_id,))
            
            # Increase available copies of the book by 1
            conn.execute("UPDATE books SET available_copies = available_copies + 1 WHERE id = ?", (book_id,))
            
            conn.commit()
            
    return redirect(url_for('dashboard'))
