from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from db import get_db_connection

auth_bp = Blueprint('auth', __name__, template_folder='templates')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Users WHERE username=%s AND password=%s", (username, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            session['logged_in'] = True
            session['username'] = user['username']
            session['fullname'] = user['fullname']
            session['role'] = user['role']
            
            if user['role'] == 'manager':
                return redirect(url_for('products.index'))
            else:
                return redirect(url_for('sales.pos'))
        else:
            flash("Sai tài khoản hoặc mật khẩu!")
            
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

