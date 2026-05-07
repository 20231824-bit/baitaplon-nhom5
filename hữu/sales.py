from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
from db import get_db_connection
from datetime import datetime

sales_bp = Blueprint('sales', __name__, template_folder='templates')

@sales_bp.route('/pos', methods=['GET', 'POST'])
def pos():
    if request.method == 'POST':
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            customer_name = request.form['customer_name']
            customer_phone = request.form['customer_phone']
            cart_str = request.form['cart_json']
            discount_percent = int(request.form.get('discount_percent', 0))
            payment_method = request.form.get('payment_method', 'Tiền mặt')
            
            import json
            cart = json.loads(cart_str)
            if not cart:
                flash('Giỏ hàng trống!', 'danger')
                return redirect(url_for('sales.pos'))

            # Process cart - check stock
            total_amount = 0
            for item in cart:
                product_id = item['id']
                price = item['price']
                quantity = 1
                
                cursor.execute("SELECT stock FROM Products WHERE id = %s", (product_id,))
                product_row = cursor.fetchone()
                if not product_row or product_row['stock'] < quantity:
                    flash(f"Sản phẩm {item['name']} hết hàng!")
                    return redirect(url_for('sales.pos'))
                
                total_amount += price * quantity

            # Customer
            cursor.execute("SELECT id FROM Customers WHERE phone = %s", (customer_phone,))
            existing_customer = cursor.fetchone()
            if existing_customer:
                customer_id = existing_customer['id']
            else:
                cursor.execute("INSERT INTO Customers (name, phone) VALUES (%s, %s)", (customer_name, customer_phone))
                customer_id = cursor.lastrowid

            final_amount = total_amount - (total_amount * discount_percent / 100)

            # Create invoice
            cursor.execute("""
                INSERT INTO Invoices (customer_id, total_amount, final_amount, payment_method, created_at) 
                VALUES (%s, %s, %s, %s, %s)
            """, (customer_id, total_amount, final_amount, payment_method, datetime.now()))
            invoice_id = cursor.lastrowid

            # Add details and update stocks
            for item in cart:
                product_id = item['id']
                price = item['price']
                cursor.execute("""
                    INSERT INTO Invoice_Details (invoice_id, product_id, quantity, price) 
                    VALUES (%s, %s, %s, %s)
                """, (invoice_id, product_id, 1, price))
                cursor.execute("UPDATE Products SET stock = stock - 1 WHERE id = %s", (product_id,))
            
            conn.commit()
            flash(f'✅ Thanh toán thành công {len(cart)} sản phẩm! Tổng: {total_amount:,}đ', 'success')
            return redirect(url_for('sales.invoices'))
            
        except Exception as e:
            conn.rollback()
            flash(f'❌ Lỗi xử lý đơn hàng: {str(e)}', 'danger')
            return redirect(url_for('sales.pos'))
        finally:
            cursor.close()
            conn.close()
    
    # GET request - show POS page
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT id, model_name, color, storage, sell_price, image_url, stock
        FROM Products
    """)
    devices = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('pos.html', devices=devices)

# Rest of routes remain the same...
@sales_bp.route('/invoices')
def invoices():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    query = """
        SELECT 
            i.id as invoice_id, 
            i.created_at, 
            c.name as customer_name, 
            c.phone,
            p.model_name, 
            d.quantity,
            d.price,
            i.payment_method
        FROM Invoices i
        JOIN Customers c ON i.customer_id = c.id
        JOIN Invoice_Details d ON i.id = d.invoice_id
        JOIN Products p ON d.product_id = p.id
        ORDER BY i.created_at DESC
    """
    cursor.execute(query)
    invoice_list = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('invoices.html', invoices=invoice_list)

@sales_bp.route('/print/<int:invoice_id>')
def print_invoice(invoice_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    query = """
        SELECT i.id, i.total_amount, i.discount, i.final_amount, i.payment_method, i.created_at,
               c.name AS customer_name, c.phone AS customer_phone,
               p.model_name, p.color, p.storage, d.quantity, d.price
        FROM Invoices i
        JOIN Customers c ON i.customer_id = c.id
        JOIN Invoice_Details d ON i.id = d.invoice_id
        JOIN Products p ON d.product_id = p.id
        WHERE i.id = %s
    """
    cursor.execute(query, (invoice_id,))
    invoice_data = cursor.fetchall()

    if not invoice_data:
        return "Không tìm thấy hóa đơn!"

    invoice_info = invoice_data[0]
    details = invoice_data
    
    cursor.close()
    conn.close()
    
    if not invoice_info:
        return "Không tìm thấy hóa đơn!", 404
        
    return render_template('print_invoice.html', invoice=invoice_info, details=details)

@sales_bp.route('/api/check_phone/<phone>')
def check_phone(phone):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT c.id, c.name, IFNULL(SUM(i.final_amount), 0) as total_spent
        FROM Customers c
        LEFT JOIN Invoices i ON c.id = i.customer_id
        WHERE c.phone = %s
        GROUP BY c.id
    """, (phone,))
    customer = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if customer:
        total_spent = float(customer['total_spent'])
        discount = 0
        rank = "Thành viên"
        
        if total_spent >= 100000000: 
            discount = 10
            rank = "VIP Vàng"
        elif total_spent >= 50000000:
            discount = 5
            rank = "VIP Bạc"
            
        return jsonify({
            'exists': True, 
            'name': customer['name'], 
            'total_spent': total_spent,
            'discount': discount,
            'rank': rank
        })
        
    return jsonify({'exists': False})
