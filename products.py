from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from functools import wraps
from db import get_db_connection
from utils.queries import get_products_list, get_brands
import os
import mysql.connector
from werkzeug.utils import secure_filename

products_bp = Blueprint('products', __name__, template_folder='templates')

# Reuse admin_required from main app or define here
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('auth.login'))
        if session.get('role') != 'manager':
            flash("CẢNH BÁO: Khu vực này chỉ dành cho Quản trị viên!")
            return redirect(url_for('sales.pos'))
        return f(*args, **kwargs)
    return decorated_function

@products_bp.route('/', methods=['GET'])
@admin_required
def index():
    products = get_products_list()
    return render_template('index.html', products=products)

@products_bp.route('/add_product', methods=['GET', 'POST'])
@admin_required
def add_product():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        try:
            # Validate required fields
            required_fields = ['brand_id', 'model_name', 'storage', 'color', 'buy_price', 'sell_price', 'stock']
            missing = [f for f in required_fields if f not in request.form or not request.form[f].strip()]
            if missing:
                flash(f"Lỗi: Thiếu trường bắt buộc: {', '.join(missing)}", 'danger')
            else:
                brand_id = request.form['brand_id']
                model_name = request.form['model_name'].strip()
                color = request.form['color'].strip()
                storage = request.form['storage'].strip()
                buy_price = float(request.form['buy_price'])
                sell_price = float(request.form['sell_price'])
                stock = int(request.form['stock'])

                # Image handling
                image_url = 'default_phone.png'
                if 'image' in request.files and request.files['image'].filename:
                    file = request.files['image']
                    filename = secure_filename(file.filename)
                    if filename:
                        image_url = filename
                        filepath = os.path.join('static/uploads', image_url)
                        file.save(filepath)

                cursor.execute("""
                    INSERT INTO Products (brand_id, model_name, color, storage, buy_price, sell_price, stock, image_url) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (brand_id, model_name, color, storage, buy_price, sell_price, stock, image_url))
                conn.commit()

                flash(f"✅ Đã thêm thành công {stock} máy {model_name} vào kho!", 'success')
                return redirect(url_for('products.index'))
        except ValueError:
            flash("Lỗi dữ liệu: Giá và số lượng phải là số hợp lệ!", 'danger')
        except mysql.connector.Error as e:
            flash(f"Lỗi database: {str(e).split(';')[0]} Kiểm tra table Brands/Products!", 'danger')
        except Exception as e:
            flash(f"Lỗi hệ thống: {str(e)}", 'danger')
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    cursor.execute("SELECT * FROM Brands")
    brands = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('add_product.html', brands=brands)

@products_bp.route('/add_imei', methods=['GET', 'POST'])
@admin_required
def add_imei():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        product_id = request.form['product_id']
        imei = request.form['imei']
        
        try:
            cursor.execute(
                "INSERT INTO IMEI_Tracking (imei, product_id, status) VALUES (%s, %s, 'Available')",
                (imei, product_id)
            )
            conn.commit()
        except Exception as err:
            print(f"Lỗi Database: {err}")
            
        cursor.close()
        conn.close()
        return redirect(url_for('products.index'))
        
    cursor.execute("SELECT id, CONCAT(model_name, ' (', storage, ' - ', color, ')') AS full_name FROM Products")
    products = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('add_imei.html', products=products)

@products_bp.route('/edit_product/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_product(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        brand_id = request.form['brand_id']
        model_name = request.form['model_name']
        color = request.form['color']
        storage = request.form['storage']
        buy_price = request.form['buy_price']
        sell_price = request.form['sell_price']
        stock = request.form['stock'] 
        
        cursor.execute("""
            UPDATE Products 
            SET brand_id = %s, model_name = %s, color = %s, storage = %s, 
                buy_price = %s, sell_price = %s, stock = %s
            WHERE id = %s
        """, (brand_id, model_name, color, storage, buy_price, sell_price, stock, id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash(f"Đã cập nhật máy {model_name} thành công!")
        return redirect(url_for('products.index'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM Products WHERE id = %s", (id,))
    product = cursor.fetchone()

    cursor.execute("SELECT * FROM Brands")
    brands = cursor.fetchall()

    cursor.close()
    conn.close()
    
    if not product:
        return "Không tìm thấy máy này", 404
        
    return render_template('edit_product.html', product=product, brands=brands)

@products_bp.route('/delete_product/<int:id>')
@admin_required
def delete_product(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM IMEI_Tracking WHERE product_id = %s", (id,))
    cursor.execute("DELETE FROM Products WHERE id = %s", (id,))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    flash("Đã xóa sản phẩm khỏi kho!")
    return redirect(url_for('products.index'))

