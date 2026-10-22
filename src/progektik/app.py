import hashlib
from flask import Flask, render_template, request, jsonify, redirect, session
import mysql.connector
from openai import OpenAI

app = Flask(__name__)
app.secret_key = 'super_secret_pink_key_123'

@app.route('/user_register', methods=['POST'])
def user_register():
    name = request.form.get('fullname')
    login = request.form.get('email')
    password = request.form.get('password')
    
    if not name or not login or not password:
        return {'result': False, 'message': 'Заполните все поля'}, 400

    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    try:
        cnx = mysql.connector.connect(
            host="185.114.247.43",
            port=3306,
            database="sch688_vvedenie",
            user="sch688_vvedenie",
            password="Qwerty123"
        )
        cur = cnx.cursor()

        try:
            cur.execute('INSERT INTO users (`username`, `email`, `password_hash`) VALUES (%s, %s, %s)', (name, login, password_hash))
            cnx.commit()
            new_id = cur.lastrowid
            return {'result': True, 'id': new_id}
        
        except mysql.connector.Error as err:
            if err.errno == 1062:
                return {'result': False, 'message': 'Этот Email уже зарегистрирован'}, 400
            else:
                print(f"Ошибка БД: {err}")
                return {'result': False, 'message': 'Ошибка базы данных'}, 500
        
        finally:
            cur.close()
            cnx.close()

    except mysql.connector.Error as err:
        print(f"Ошибка подключения к БД: {err}")
        return {'result': False, 'message': 'Не удалось подключиться к БД'}, 500

@app.route('/')
def registration():
    return render_template('registration.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        try:
            cnx = mysql.connector.connect(
                host="185.114.247.43",
                port=3306,
                database="sch688_vvedenie",
                user="sch688_vvedenie",
                password="Qwerty123"
            )
            cur = cnx.cursor(dictionary=True)
            cur.execute("SELECT * FROM users WHERE email = %s", (username,))
            user = cur.fetchone()
            cur.close()
            cnx.close()

            if user:
                password_hash = hashlib.sha256(password.encode()).hexdigest()
                
                if user['password_hash'] == password_hash:
                    session['username'] = user['username']
                    return redirect('/dashboard')
                else:
                    return "Неверный пароль", 401
            else:
                return "Пользователь не найден", 404
                
        except mysql.connector.Error as err:
            print(f"Ошибка БД: {err}")
            return "Ошибка сервера", 500

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect('/login')
    
    class User:
        username = session['username']
        balance = 1500
        
    return render_template('dashboard.html', user=User)

@app.route('/history')
def history():
    if 'username' not in session:
        return redirect('/login')
    return render_template('history.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect('/login')

@app.route('/ai-request', methods=['GET', 'POST'])
def ai_request():
    if 'username' not in session:
        return redirect('/login')
        
    if request.method == 'POST':
        data = request.get_json()
        user_prompt = data.get('prompt', '')
        
        try:
            client = OpenAI(
                api_key="sk-0af5a13230ed4119bfc6dbcd7e0c42a0",
                base_url="https://api.deepseek.com"
            )
            
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "Ты полезный ассистент."},
                    {"role": "user", "content": user_prompt}
                ],
                stream=False
            )
            
            if response.choices and response.choices[0].message.content:
                ai_answer = response.choices[0].message.content
                return jsonify({'response': ai_answer})
            else:
                return jsonify({'response': 'Нейросеть вернула пустой ответ. Попробуйте переформулировать запрос.'}), 500
            
        except Exception as e:
            print(f"ПОЛНАЯ ОШИБКА ИИ: {type(e).__name__}: {e}")
            return jsonify({'response': f'Ошибка: {str(e)}'}), 500
        
    return render_template('ai_request.html')

if __name__ == '__main__':
    app.run(port=8000, debug=True)