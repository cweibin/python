from flask import Flask, render_template, request, flash, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

def init_db():
    conn = sqlite3.connect('contacts.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  email TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL,
                  phone TEXT,
                  company TEXT,
                  bio TEXT,
                  avatar TEXT,
                  created_at TIMESTAMP,
                  updated_at TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS contacts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  name TEXT NOT NULL,
                  email TEXT NOT NULL,
                  message TEXT NOT NULL,
                  created_at TIMESTAMP,
                  FOREIGN KEY(user_id) REFERENCES users(id))''')
    conn.commit()
    conn.close()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # 验证输入
        if not username or not email or not password:
            flash('所有字段都是必需的')
            return redirect(url_for('register'))
        
        if len(username) < 3:
            flash('用户名长度至少为3个字符')
            return redirect(url_for('register'))
        
        if password != confirm_password:
            flash('两次输入的密码不一致')
            return redirect(url_for('register'))
        
        if len(password) < 6:
            flash('密码长度至少为6个字符')
            return redirect(url_for('register'))
        
        # 验证邮箱格式
        if '@' not in email or '.' not in email:
            flash('请输入有效的邮箱地址')
            return redirect(url_for('register'))
        
        try:
            conn = sqlite3.connect('contacts.db')
            c = conn.cursor()
            # 使用 pbkdf2 算法兼容 Python 3.9
            hashed_password = generate_password_hash(password, method='pbkdf2')
            now = datetime.now()
            c.execute("INSERT INTO users (username, email, password, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                     (username, email, hashed_password, now, now))
            conn.commit()
            conn.close()
            flash('注册成功！请登录。')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError as e:
            if 'username' in str(e):
                flash('用户名已存在，请选择其他用户名')
            elif 'email' in str(e):
                flash('邮箱已被注册，请使用其他邮箱')
            else:
                flash('注册失败，请重试')
            return redirect(url_for('register'))
        except Exception as e:
            print(f"注册错误: {type(e).__name__}: {e}")
            flash('注册失败，请检查输入后重试')
            return redirect(url_for('register'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('用户名和密码不能为空')
            return redirect(url_for('login'))
        
        try:
            conn = sqlite3.connect('contacts.db')
            c = conn.cursor()
            c.execute("SELECT id, username, password FROM users WHERE username = ?", (username,))
            user = c.fetchone()
            conn.close()
            
            if user and check_password_hash(user[2], password):
                session['user_id'] = user[0]
                session['username'] = user[1]
                flash(f'欢迎, {user[1]}!')
                return redirect(url_for('home'))
            else:
                flash('用户名或密码错误')
                return redirect(url_for('login'))
        except Exception as e:
            print(f"登录错误: {type(e).__name__}: {e}")
            flash('登录失败，请重试')
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('您已退出登录')
    return redirect(url_for('home'))

@app.route('/profile')
def profile():
    if not session.get('user_id'):
        flash('请先登录')
        return redirect(url_for('login'))
    
    user_id = session.get('user_id')
    
    try:
        conn = sqlite3.connect('contacts.db')
        c = conn.cursor()
        
        # 获取用户信息
        c.execute("SELECT id, username, email, phone, company, bio, avatar, created_at FROM users WHERE id = ?", (user_id,))
        user = c.fetchone()
        
        # 获取用户的留言历史
        c.execute("SELECT id, name, email, message, created_at FROM contacts WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        messages = c.fetchall()
        
        conn.close()
        
        if not user:
            flash('用户不存在')
            return redirect(url_for('home'))
        
        user_dict = {
            'id': user[0],
            'username': user[1],
            'email': user[2],
            'phone': user[3],
            'company': user[4],
            'bio': user[5],
            'avatar': user[6],
            'created_at': user[7]
        }
        
        return render_template('profile.html', user=user_dict, messages=messages)
    except Exception as e:
        flash('获取个人资料失败')
        return redirect(url_for('home'))

@app.route('/profile/edit', methods=['GET', 'POST'])
def edit_profile():
    if not session.get('user_id'):
        flash('请先登录')
        return redirect(url_for('login'))
    
    user_id = session.get('user_id')
    
    if request.method == 'POST':
        phone = request.form.get('phone')
        company = request.form.get('company')
        bio = request.form.get('bio')
        
        try:
            conn = sqlite3.connect('contacts.db')
            c = conn.cursor()
            c.execute("UPDATE users SET phone = ?, company = ?, bio = ?, updated_at = ? WHERE id = ?",
                     (phone, company, bio, datetime.now(), user_id))
            conn.commit()
            conn.close()
            
            flash('个人资料更新成功')
            return redirect(url_for('profile'))
        except Exception as e:
            flash('更新失败，请重试')
            return redirect(url_for('edit_profile'))
    
    try:
        conn = sqlite3.connect('contacts.db')
        c = conn.cursor()
        c.execute("SELECT id, username, email, phone, company, bio FROM users WHERE id = ?", (user_id,))
        user = c.fetchone()
        conn.close()
        
        if not user:
            flash('用户不存在')
            return redirect(url_for('home'))
        
        user_dict = {
            'id': user[0],
            'username': user[1],
            'email': user[2],
            'phone': user[3],
            'company': user[4],
            'bio': user[5]
        }
        
        return render_template('edit_profile.html', user=user_dict)
    except Exception as e:
        flash('获取用户信息失败')
        return redirect(url_for('home'))

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')
        
        if not name or not email or not message:
            flash('所有字段都是必需的')
            return redirect(url_for('contact'))
        
        user_id = session.get('user_id')
        
        try:
            conn = sqlite3.connect('contacts.db')
            c = conn.cursor()
            c.execute("INSERT INTO contacts (user_id, name, email, message, created_at) VALUES (?, ?, ?, ?, ?)",
                     (user_id, name, email, message, datetime.now()))
            conn.commit()
            conn.close()
            
            flash('感谢您的留言！我们会尽快与您联系。')
            return redirect(url_for('contact'))
        except Exception as e:
            flash('提交失败，请重试')
            return redirect(url_for('contact'))
    
    return render_template('contact.html')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
