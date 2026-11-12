from flask import Flask, render_template, request, jsonify, session, redirect
from llama_cpp import Llama
import sqlite3
import hashlib

REPO_ID = "bartowski/Qwen2.5-0.5B-Instruct-GGUF"
FILENAME = "Qwen2.5-0.5B-Instruct-Q4_K_M.gguf"

print(f"Загрузка модели {FILENAME} из {REPO_ID}...")
llm = Llama.from_pretrained(
    repo_id=REPO_ID,
    filename=FILENAME,
    n_ctx=2048,
    verbose=False
)
print("Модель успешно загружена.")

app = Flask(__name__)
app.secret_key = "1581"

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            balance REAL DEFAULT 1500.0
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            type TEXT,
            cost REAL DEFAULT 0,
            description TEXT,
            balance_after REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/api/user_register', methods=['POST'])
def user_register():
    req = request.get_json()
    name = req.get('name')
    email = req.get('email')
    password = req.get('password')

    if not name or not email or not password:
        return jsonify({'error': 'заполните все поля'}), 400

    password_hash = hashlib.sha256(password.encode()).hexdigest()

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute('SELECT id FROM users WHERE email = ?', (email,))
        if cur.fetchone():
            return jsonify({'error': 'пользователь с таким email уже существует'}), 400

        cur.execute(
            'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
            (name, email, password_hash)
        )
        conn.commit()
        
        new_id = cur.lastrowid
        session.clear()
        session['user_id'] = new_id
        session['username'] = name

        return jsonify({'ok': True, 'id': new_id})
    finally:
        conn.close()

@app.route('/api/login', methods=['POST'])
def login():
    req = request.get_json()
    email = req.get('email')
    password = req.get('password')

    password_hash = hashlib.sha256(password.encode()).hexdigest()

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute('SELECT id, username, email, password_hash FROM users WHERE email = ?', (email,))
        user = cur.fetchone()
    finally:
        conn.close()

    if not user or user['password_hash'] != password_hash:
        return jsonify({'error': 'неверный email или пароль'}), 401

    session.clear()
    session['user_id'] = user['id']
    session['username'] = user['username']

    return jsonify({
        'id': user['id'],
        'username': user['username'],
        'email': user['email']
    })

@app.route('/api/chat', methods=['POST'])
def api_chat():
    if 'user_id' not in session:
        return jsonify({'error': 'не авторизован'}), 401
    
    req = request.get_json(silent=True) or {}
    message = (req.get('message') or '').strip()
    if not message:
        return jsonify({'error': 'пустое сообщение'}), 400

    prompt = f"<|im_start|>system\nТы полезный ассистент. Отвечай кратко и по-русски.<|im_end|>\n<|im_start|>user\n{message}<|im_end|>\n<|im_start|>assistant\n"
    
    output = llm(
        prompt,
        max_tokens=150,
        temperature=0.7,
        stop=["<|im_end|>"]
    )
    reply = output['choices'][0]['text'].strip()
    return jsonify({'reply': reply})

@app.route('/profile')
def profile_page():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute('SELECT id, username, email, balance FROM users WHERE id = ?', (session['user_id'],))
        user = cur.fetchone()
    finally:
        conn.close()

    if not user:
        session.clear()
        return redirect('/login')

    return render_template('profile.html', user=user)

@app.route('/logout', methods=['POST'])
def api_logout():
    session.clear()
    return redirect('/login')

@app.route('/transactions')
def transactions_page():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT id, amount, type, cost, description, balance_after, created_at
            FROM transactions
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
        ''', (session['user_id'],))
        transactions = cur.fetchall()
    finally:
        conn.close()

    return render_template('transactions.html', transactions=transactions)

@app.route('/api/make_transaction', methods=['POST'])
def make_transaction():
    if 'user_id' not in session:
        return jsonify({'error': 'не авторизован'}), 401

    req = request.get_json()
    amount = req.get('amount')
    tx_type = req.get('type')
    description = req.get('description', 'Транзакция')
    cost = req.get('cost', 0)

    if not amount or amount <= 0:
        return jsonify({'error': 'неверная сумма'}), 400

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute('SELECT balance FROM users WHERE id = ?', (session['user_id'],))
        user = cur.fetchone()
        
        current_balance = user['balance']
        
        if tx_type == 'deposit':
            new_balance = current_balance + amount
        elif tx_type == 'withdraw':
            if current_balance < amount:
                return jsonify({'error': 'недостаточно средств'}), 400
            new_balance = current_balance - amount
        else:
            return jsonify({'error': 'неверный тип транзакции'}), 400

        cur.execute('UPDATE users SET balance = ? WHERE id = ?', (new_balance, session['user_id']))
        
        cur.execute('''
            INSERT INTO transactions (user_id, amount, type, cost, description, balance_after) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (session['user_id'], amount, tx_type, cost, description, new_balance))
        
        conn.commit()
        return jsonify({'ok': True, 'new_balance': new_balance})
    except Exception as err:
        conn.rollback()
        return jsonify({'error': f'Ошибка БД: {err}'}), 500
    finally:
        conn.close()

@app.route('/ai-request')
def ai_request_page():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('ai_request.html')

@app.route("/")
def registration():
    return render_template('registration.html')

@app.route("/login")
def login_page():
    return render_template('login.html')

if __name__ == '__main__':
    app.run(debug=True)