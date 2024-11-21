
import os
import sqlite3
from bd import crear_usuario
from flask import Flask, flash, g, jsonify, redirect, render_template, request, url_for,session, make_response,session
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from pymongo import MongoClient
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length
from datetime import datetime
import json
from io import BytesIO
from xhtml2pdf import pisa
from functools import wraps


app = Flask(__name__)
app.secret_key = '123456789'
# Conexión a la base de datos
def get_db_connection():
    conn = sqlite3.connect('cliente.db')
    conn.row_factory = sqlite3.Row
    return conn
class RegistroForm(FlaskForm):
    usuario = StringField('Usuario', validators=[DataRequired(), Length(min=4, max=25)])
    contrasena = PasswordField('Contraseña', validators=[DataRequired(), Length(min=6)])
    confirmar_contrasena = PasswordField('Confirmar Contraseña', validators=[
        DataRequired(), EqualTo('contrasena', message='Las contraseñas deben coincidir')
    ])
    submit = SubmitField('Registrar')
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Verificar si el usuario está autenticado
        if 'user_id' not in session:
            flash("Debes iniciar sesión para acceder a esta página.", "error")
            return redirect(url_for('login'))  # Redirigir a la página de inicio de sesión
        return f(*args, **kwargs)
    return decorated_function
# Ruta para el login
@app.route('/login', methods=['GET', 'POST'])
def login():
    session.clear()  # Limpiar cualquier dato de sesión previo
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Conectar a la base de datos SQLite
        conn = get_db_connection()
        cursor = conn.cursor()

        # Verificar si el usuario existe
        cursor.execute('SELECT * FROM Usuario WHERE usuario = ?', (username,))
        user = cursor.fetchone()
        conn.close()

        if user and user['contrasena'] == password:  # Verificar contraseña
            # Guardar el ID del usuario en la sesión
            session['user_id'] = user['id_usuario']  # 'id_usuario' es la clave primaria en la tabla Usuario
            session.pop('carrito', None)  # Opcional: borra el carrito de la sesión
            flash('Inicio de sesión exitoso', 'success')
            return redirect(url_for('home'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
            return redirect(url_for('login'))

    return render_template('login.html', show_navbar=False)
# Decorador para proteger rutas
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:  # Si no hay usuario en sesión
            flash('Debes iniciar sesión para acceder a esta página.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
# Ruta para el logout
@app.route('/logout')
def logout():
    session.clear()  # Limpiar toda la información de la sesión
    flash('Has cerrado sesión exitosamente.', 'success')
    return redirect(url_for('login'))

# Ruta para la página de inicio
@app.route('/home')
@login_required
def home():
    # Conexión a la base de datos
    conn = get_db_connection()
    cursor = conn.cursor()

    # Consulta para obtener los productos
    cursor.execute("SELECT id_producto, nombre, descripcion, precio, stock FROM Producto")
    products = cursor.fetchall()

    # Cerramos la conexión
    conn.close()

    # Transformamos los resultados en una lista de diccionarios
    product_list = []
    for product in products:
        product_list.append({
            'id_producto': product[0],
            'nombre': product[1],
            'descripcion': product[2],
            'precio': product[3],
            'stock': product[4]
        })

    # Pasamos los productos a la plantilla
    return render_template('home.html', products=product_list, show_navbar=True)
@app.route('/flujo_de_caja')
def flujo_de_caja():
    conn = get_db_connection()
    pedidos = conn.execute('SELECT * FROM Pedidos').fetchall()
    detalles = conn.execute('SELECT * FROM DetallePedido').fetchall()
    conn.close()
    return render_template('detalle.html',
                           show_navbar=True,
                           pedidos=pedidos, 
                           detalles=detalles)


@app.route('/vaciar_carrito', methods=['POST'])
def vaciar_carrito():
    # Eliminar el carrito de la sesión
    session.pop('carrito', None)
    session.modified = True  # Asegura que la sesión se actualice

    flash("El carrito ha sido vaciado.", "success")
    return redirect(url_for('menu'))


@app.route('/pagar', methods=['POST'])
def pagar():
    carrito = session.get('carrito', [])
    
    # Conectar a la base de datos
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Para cada producto en el carrito, actualizamos el stock en la base de datos
        for item in carrito:
            producto_id = item['id']
            cantidad_a_descontar = item['cantidad']

            # Obtener el stock actual del producto
            cursor.execute("SELECT stock FROM Producto WHERE id_producto = ?", (producto_id,))
            producto = cursor.fetchone()

            if producto and producto['stock'] >= cantidad_a_descontar:
                # Descontar la cantidad del stock
                nuevo_stock = producto['stock'] - cantidad_a_descontar
                cursor.execute("UPDATE Producto SET stock = ? WHERE id_producto = ?", (nuevo_stock, producto_id))
            else:
                # Si no hay suficiente stock, lanzar error
                flash(f"No hay suficiente stock para {item['nombre']}", "error")
                return redirect(url_for('ver_carrito'))

        # Confirmar cambios en la base de datos
        conn.commit()

        # Vaciar el carrito de la sesión
        session['carrito'] = []
        session.modified = True  # Asegura que se actualice la sesión

        flash("¡Gracias por tu compra! El pedido ha sido procesado exitosamente.", "success")
    except Exception as e:
        # En caso de error, se imprime el error y se envía un mensaje al usuario
        print(f"Error al procesar el pago: {e}")
        flash("Hubo un error al procesar tu pedido. Inténtalo de nuevo.", "error")
    finally:
        # Cierra la conexión a la base de datos
        conn.close()

    # Redirige a la página de inicio
    return redirect(url_for('home'))

def obtener_productos():
    # Conexión a la base de datos
    conn = sqlite3.connect('cliente.db')
    cursor = conn.cursor()
    
    # Consulta para obtener los productos
    cursor.execute("SELECT id_producto, nombre, descripcion, precio, stock FROM Producto")
    productos = cursor.fetchall()
    
    # Cierra la conexión
    conn.close()
    
    # Convierte los resultados en una lista de diccionarios
    productos_lista = []
    for producto in productos:
        productos_lista.append({
            'id_producto': producto[0],
            'nombre': producto[1],
            'descripcion': producto[2],
            'precio': producto[3],
            'stock': producto[4]
        })
    
    return productos_lista
@app.route('/menu')
@login_required
def menu():
    # Obtiene los productos del menú de la base de datos
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id_producto, nombre, descripcion, precio, stock FROM Producto")
    productos = cursor.fetchall()
    conn.close()

    # Transformamos los resultados en una lista de diccionarios
    productos_lista = []
    for producto in productos:
        productos_lista.append({
            'id_producto': producto[0],
            'nombre': producto[1],
            'descripcion': producto[2],
            'precio': producto[3],
            'stock': producto[4]
        })

    # Pasamos los productos al template
    return render_template('menu.html', productos=productos_lista, show_navbar=True)

@app.route('/agregar_al_carrito_ajax', methods=['POST'])
def agregar_al_carrito_ajax():
    producto_id = request.json.get('producto_id')
    nombre = request.json.get('nombre')
    precio = float(request.json.get('precio'))

    # Conectar a la base de datos para verificar el stock
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT stock FROM Producto WHERE id_producto = ?", (producto_id,))
    producto = cursor.fetchone()
    conn.close()

    # Validar que haya stock disponible
    if not producto or producto['stock'] <= 0:
        return {"success": False, "message": f"No hay suficiente stock para {nombre}."}, 400

    # Inicializa el carrito si no existe en la sesión
    if 'carrito' not in session:
        session['carrito'] = []

    carrito = session['carrito']

    # Verifica si existe un producto exactamente igual en el carrito
    for item in carrito:
        if item['id'] == producto_id:
            # Incrementa la cantidad en el carrito, pero verifica el stock
            if item['cantidad'] < producto['stock']:
                item['cantidad'] += 1
                item['precio_total'] += precio
                session.modified = True
                return {"success": True, "message": f"¡{nombre} añadido al carrito!"}
            else:
                return {"success": False, "message": f"No puedes agregar más de {producto['stock']} unidades de {nombre}."}, 400
    else:
        # Si el producto no está en el carrito, lo agrega como nuevo
        carrito.append({
            'id': producto_id,
            'nombre': nombre,
            'precio_unitario': precio,
            'cantidad': 1,
            'precio_total': precio
        })

    session.modified = True
    return {"success": True, "message": f"¡{nombre} añadido al carrito!"}
@app.route('/carrito')
def ver_carrito():
    carrito = session.get('carrito', [])
    # Calcula el total sumando el precio_total de cada producto en el carrito
    total = sum(item['precio_total'] for item in carrito)
    return render_template('carrito.html', carrito=carrito, total=total)

@app.route('/carrito/<producto_id>', methods=['POST'])
def eliminar_unidad(producto_id):
    carrito = session.get('carrito', [])

    # Busca el producto en el carrito por su ID
    for item in carrito:
        if item['id'] == producto_id:
            if item['cantidad'] > 1:
                # Disminuye la cantidad y ajusta el precio total
                item['cantidad'] -= 1
                item['precio_total'] -= item['precio_unitario']
            else:
                # Si la cantidad es 1, elimina el producto del carrito
                carrito.remove(item)
            break

    # Actualiza la sesión con los cambios
    session['carrito'] = carrito
    session.modified = True
    flash("Una unidad eliminada del carrito", "success")
    
    # Redirige al endpoint correcto
    return redirect(url_for('ver_carrito'))





# Ruta para la página principal
@app.route('/')
def index():
    return render_template('login.html', show_navbar=False)


def get_product_stock(id_producto):
        # Conexión a la base de datos
    conn = sqlite3.connect('cliente.db')
    cursor = conn.cursor()

    # Consulta el stock del producto desde la base de datos
    result = cliente.execute("SELECT stock FROM Producto WHERE id_producto = ?", (id_producto,)).fetchone()
    return result['stock'] if result else 0  # Devuelve 0 si no encuentra el producto


@app.route('/boleta/<int:id_pago>/pdf', methods=['GET'])
def boleta_pdf(id_pago):
    # Conexión a la base de datos y obtención de datos
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Consulta para obtener los datos de la boleta
        cursor.execute("""
            SELECT 
                rp.id_pago,
                rp.fecha_pago,
                p.nombre AS producto,
                rp.cantidad,
                p.precio AS precio_unitario,
                (rp.cantidad * p.precio) AS valor_acumulado,
                rp.metodo_pago,
                SUM(rp.monto_total) OVER (PARTITION BY rp.id_pago) AS total_pago
            FROM registro_pagos rp
            JOIN Producto p ON rp.id_producto = p.id_producto
            WHERE rp.id_pago = ?
        """, (id_pago,))
        detalles_venta = cursor.fetchall()
    except Exception as e:
        print(f"Error al ejecutar la consulta: {e}")
        return "Error interno del servidor", 500
    finally:
        conn.close()

    # Verificar si hay datos para el ID de pago solicitado
    if not detalles_venta:
        return f"No se encontraron registros para el ID de pago {id_pago}", 404

    # Transformar datos en un diccionario
    venta = {
        "id_pago": id_pago,
        "fecha_pago": detalles_venta[0][1],
        "metodo_pago": detalles_venta[0][6],
        "monto_total": detalles_venta[0][7],  # Total calculado
        "productos": [
            {
                "nombre": row[2],
                "cantidad": row[3],
                "precio_unitario": row[4],
                "valor_acumulado": row[5]
            }
            for row in detalles_venta
        ]
    }

    # Renderizar la plantilla HTML
    rendered_html = render_template('boleta.html', venta=venta)

    # Convertir el HTML a PDF
    pdf = convertir_html_a_pdf(rendered_html)
    if not pdf:
        return "Error al generar el PDF", 500

    # Responder con el archivo PDF
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=boleta_{id_pago}.pdf'
    return response


def convertir_html_a_pdf(source_html):
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(source_html.encode("UTF-8")), result)
    if not pdf.err:
        return result.getvalue()
    return None
@app.route('/boletas', methods=['GET'])
def listar_boletas():
    # Conexión a la base de datos
    conn = get_db_connection()
    cursor = conn.cursor()

    # Consulta para obtener los pagos únicos
    cursor.execute("""
    SELECT 
        rp.id_pago, 
        rp.fecha_pago, 
        SUM(rp.monto_total) AS monto_total, 
        rp.metodo_pago
    FROM registro_pagos rp
    GROUP BY rp.id_pago, rp.fecha_pago, rp.metodo_pago
    ORDER BY rp.fecha_pago DESC

    """)
    boletas = cursor.fetchall()
    conn.close()

    # Transformar los datos en una lista de diccionarios
    boletas_data = [
        {
            "id_pago": boleta[0],
            "fecha_pago": boleta[1],
            "monto_total": boleta[2],
            "metodo_pago": boleta[3]
        }
        for boleta in boletas
    ]

    # Renderizar la plantilla con las boletas
    return render_template('listar_boletas.html', boletas=boletas_data, show_navbar=True)

@app.route('/detalle', methods=['GET'])
@login_required
def detalle():
    # Obtener el número de página actual (por defecto, 1)
    page = request.args.get('page', 1, type=int)
    if page < 1:
        page = 1  # Asegurarse de que la página sea válida

    per_page = 10  # Registros por página
    offset = (page - 1) * per_page  # Calcula el desplazamiento

    # Conexión a la base de datos
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Consulta para obtener los detalles de los pagos con paginación
        cursor.execute("""
            SELECT 
                rp.id_pago,
                rp.fecha_pago,
                p.nombre AS producto,
                rp.cantidad,
                rp.monto_total,
                rp.metodo_pago
            FROM registro_pagos rp
            JOIN Producto p ON rp.id_producto = p.id_producto
            ORDER BY rp.id_pago DESC -- IMPORTANTE: Ordenar de forma descendente
            LIMIT ? OFFSET ?
        """, (per_page, offset))

        pagos = cursor.fetchall()

        # Consulta para contar el número total de registros
        cursor.execute("SELECT COUNT(DISTINCT id_pago) FROM registro_pagos")
        total_registros = cursor.fetchone()[0]
    except Exception as e:
        print(f"Error al ejecutar la consulta: {e}")
        pagos = []
        total_registros = 0
    finally:
        conn.close()

    # Calcular el número total de páginas
    total_paginas = (total_registros + per_page - 1) // per_page

    # Transformar los resultados en una lista de diccionarios
    registros = [
        {
            "id_pago": pago[0],
            "fecha_pago": pago[1],
            "producto": pago[2],
            "cantidad": pago[3],
            "monto_total": pago[4],
            "metodo_pago": pago[5]
        }
        for pago in pagos
    ]

    # Renderizar la plantilla con los datos
    return render_template('detalle.html', 
                           registros=registros,
                           page=page,
                           total_paginas=total_paginas,
                           show_navbar=True)

#Ruta Pagina Caja
@app.route('/caja')
def caja():
    return render_template('caja.html')
@app.route('/error')
def error():
    return render_template("error.html")
# Rutas para registrar entidades
# Función para registrar un producto en la base de datos
def registrar_producto(nombre, precio, stock):
    # Conexión a la base de datos
    conn = sqlite3.connect('base_de_datos.db')  # Asegúrate de que el nombre de la base de datos es correcto
    c = conn.cursor()

    # Inserción de datos en la tabla producto
    c.execute('''
        INSERT INTO producto (nombre, precio, stock)
        VALUES (?, ?, ?)
    ''', (nombre, precio, stock))

    # Guardar cambios y cerrar la conexión
    conn.commit()
    conn.close()

@app.route('/crear_producto', methods=['GET', 'POST'])
def crear_producto():
    if request.method == 'POST':
        try:
            # Si la solicitud es AJAX, procesamos los datos en JSON
            if request.is_json:
                data = request.get_json()
                nombre = data.get('nombre')
                precio = float(data.get('precio', 0))
                stock = int(data.get('stock', 0))
                
                # Validar los campos
                if not nombre or precio <= 0 or stock < 0 or precio > 99999:
                    message = "Todos los campos son obligatorios y deben tener valores válidos. El precio no puede exceder 99,999."
                    return jsonify({"message": message}), 400

                # Guardamos el producto en la base de datos
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('INSERT INTO Producto (nombre, precio, stock) VALUES (?, ?, ?)',
                               (nombre, precio, stock))
                conn.commit()
                conn.close()
                
                # Devolvemos una respuesta JSON para AJAX
                return jsonify({"message": "Producto agregado exitosamente"}), 200
            else:
                # Manejo tradicional de formulario sin AJAX
                nombre = request.form['nombre']
                precio = float(request.form['precio'])
                stock = int(request.form['stock'])
                
                # Validar los campos
                if not nombre or precio <= 0 or stock < 0 or precio > 99999:
                    flash("Todos los campos son obligatorios y deben tener valores válidos. El precio no puede exceder 99,999.", "error")
                    return redirect(url_for('crear_producto'))

                # Guardamos el producto en la base de datos
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('INSERT INTO Producto (nombre, precio, stock) VALUES (?, ?, ?)',
                               (nombre, precio, stock))
                conn.commit()
                conn.close()

                flash("Producto agregado exitosamente.", "success")
                return redirect(url_for('menu'))

        except Exception as e:
            print(f"Error al agregar producto: {e}")
            if request.is_json:
                return jsonify({"message": "Error al agregar el producto."}), 500
            else:
                flash("Error al agregar el producto.", "error")
                return redirect(url_for('crear_producto'))

    # Renderizamos el formulario si el método es GET
    return render_template('crear_producto.html', show_navbar=True)

@app.route('/ventas', methods=['GET'])
def ventas():
    # Conexión a la base de datos
    conn = get_db_connection()
    cursor = conn.cursor()

    # Consulta para obtener ventas del mes actual por producto
    cursor.execute("""
        SELECT 
            p.nombre AS producto,
            SUM(v.cantidad) AS cantidad_vendida
        FROM ventas v
        JOIN Producto p ON v.id_producto = p.id_producto
        WHERE strftime('%Y-%m', v.fecha_venta) = strftime('%Y-%m', 'now')
        GROUP BY p.id_producto
    """)
    ventas_mes = cursor.fetchall()

    # Consulta para obtener ventas semanales
    cursor.execute("""
        SELECT 
            p.nombre AS producto,
            SUM(v.cantidad) AS cantidad_vendida,
            strftime('%W', v.fecha_venta) AS semana
        FROM ventas v
        JOIN Producto p ON v.id_producto = p.id_producto
        WHERE strftime('%Y-%m', v.fecha_venta) = strftime('%Y-%m', 'now')
        GROUP BY p.id_producto, semana
        ORDER BY semana ASC
    """)
    ventas_semanales = cursor.fetchall()
    conn.close()

    # Preparar datos para el gráfico
    productos = [venta[0] for venta in ventas_semanales]
    semanas = [venta[2] for venta in ventas_semanales]
    cantidades = [venta[1] for venta in ventas_semanales]

    return render_template(
        'ventas.html', 
        ventas_mes=ventas_mes, 
        productos=productos, 
        semanas=semanas, 
        cantidades=cantidades
    )

@app.route('/simulacion_pago', methods=['GET', 'POST'])
def simulacion_pago():
    if request.method == 'POST':
        metodo_pago = request.form.get('metodo_pago')  # Obtener método de pago
        carrito = session.get('carrito', [])  # Obtener carrito de la sesión

        if not carrito:
            flash("El carrito está vacío. No se puede procesar el pago.", "error")
            return redirect(url_for('ver_carrito'))  # Redirigir al carrito si está vacío

        # Conexión a la base de datos
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            fecha_pago = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Fecha y hora actual

            # Generar un ID único para este pago
            cursor.execute("SELECT COALESCE(MAX(id_pago), 0) + 1 FROM registro_pagos")
            id_pago = cursor.fetchone()[0]  # Obtener el siguiente id_pago disponible

            # Registrar cada producto del carrito en la tabla `registro_pagos`
            for item in carrito:
                # Registrar el pago en la tabla `registro_pagos`
                cursor.execute(
                    """
                    INSERT INTO registro_pagos (id_pago, fecha_pago, id_producto, cantidad, monto_total, metodo_pago)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (id_pago, fecha_pago, item['id'], item['cantidad'], item['precio_total'], metodo_pago)
                )

                # Registrar la venta en la tabla `ventas`
                cursor.execute(
                    """
                    INSERT INTO ventas (id_producto, cantidad, fecha_venta)
                    VALUES (?, ?, ?)
                    """,
                    (item['id'], item['cantidad'], fecha_pago)
                )

                # Actualizar el stock del producto
                cursor.execute(
                    """
                    UPDATE Producto
                    SET stock = stock - ?
                    WHERE id_producto = ?
                    """,
                    (item['cantidad'], item['id'])
                )

                # Verificar si el stock quedó en negativo (prevención de errores)
                cursor.execute(
                    "SELECT stock FROM Producto WHERE id_producto = ?",
                    (item['id'],)
                )
                stock_actual = cursor.fetchone()[0]
                if stock_actual < 0:
                    raise ValueError(f"El stock del producto con ID {item['id']} es insuficiente.")

            conn.commit()  # Confirmar los cambios
            conn.close()

            # Vaciar el carrito después del pago
            session['carrito'] = []
            session.modified = True

            flash("¡Pago realizado exitosamente! Gracias por tu compra.", "success")
            return redirect(url_for('menu'))  # Redirigir al menú

        except Exception as e:
            print(f"Error al procesar el pago: {e}")  # Imprimir el error en la consola
            conn.rollback()  # Revertir los cambios si ocurre un error
            conn.close()  # Cerrar la conexión
            flash(f"Hubo un error al procesar tu pago. Error: {e}", "error")
            return redirect(url_for('simulacion_pago'))

    # Renderizar la página de simulación de pago
    total = sum(item['precio_total'] for item in session.get('carrito', []))  # Calcular el total del carrito
    return render_template('simulacion_pago.html', total=total)







@app.route('/ver_productos')
def ver_productos():
    conn = sqlite3.connect('cliente.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM Producto')
    productos = cursor.fetchall()
    conn.close()
    return render_template('ver_productos.html', productos=productos)
@app.route('/ver_usuarios')
def ver_usuarios():
    conn = sqlite3.connect('cliente.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM Usuario')
    usuarios = cursor.fetchall()
    conn.close()
    return render_template('ver_usuarios.html', usuarios=usuarios)
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        usuario = request.form.get('usuario', '').strip()
        contrasena = request.form.get('contrasena', '').strip()
        confirm_password = request.form.get('confirmPassword', '').strip()

        # Verificaciones
        if not usuario or not contrasena or not confirm_password:
            flash("Por favor, complete todos los campos.", "error")
            return redirect(url_for('register'))

        if len(contrasena) < 6:
            flash("La contraseña debe tener al menos 6 caracteres.", "error")
            return redirect(url_for('register'))

        if contrasena != confirm_password:
            flash("Las contraseñas no coinciden.", "error")
            return redirect(url_for('register'))

        # Crear el usuario en la base de datos
        crear_usuario(usuario, contrasena)

        # Mensaje de éxito para el registro
        flash("Registro exitoso. Por favor, inicie sesión.", "success")
        print("Flash message sent: Registro exitoso. Por favor, inicie sesión.")
        return redirect(url_for('login'))

    return render_template('register.html')
@app.route('/obtener_productos', methods=['GET'])
def obtener_productos_para_stock():
    # Obtiene la lista de productos desde la base de datos
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id_producto, nombre, stock FROM Producto")
    productos = cursor.fetchall()
    conn.close()

    # Convierte los datos a un formato JSON para enviarlos al frontend
    productos_lista = [{"id_producto": producto[0], "nombre": producto[1], "stock": producto[2]} for producto in productos]
    return jsonify(productos_lista), 200

@app.route('/editar_stock', methods=['POST'])
def editar_stock():
    try:
        data = request.get_json()
        producto_id = data.get('id_producto')
        nuevo_stock = int(data.get('nuevo_stock', 0))

        if not producto_id or nuevo_stock < 0:
            return jsonify({"message": "Datos inválidos."}), 400

        # Actualizar el stock del producto en la base de datos
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE Producto SET stock = ? WHERE id_producto = ?", (nuevo_stock, producto_id))
        conn.commit()
        conn.close()

        return jsonify({"message": "Stock actualizado exitosamente."}), 200
    except Exception as e:
        print(f"Error al editar stock: {e}")
        return jsonify({"message": "Error al editar el stock."}), 500

@app.route('/eliminar_producto', methods=['POST'])
def eliminar_producto():
    try:
        data = request.get_json()
        producto_id = data.get('id_producto')

        if not producto_id:
            return jsonify({"message": "Producto no encontrado."}), 400

        # Eliminar el producto de la base de datos
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Producto WHERE id_producto = ?", (producto_id,))
        conn.commit()
        conn.close()

        return jsonify({"message": "Producto eliminado exitosamente."}), 200
    except Exception as e:
        print(f"Error al eliminar producto: {e}")
        return jsonify({"message": "Error al eliminar el producto."}), 500

@app.route('/actualizar_stock', methods=['POST'])
def actualizar_stock():
    try:
        data = request.get_json()
        producto_id = data.get('id_producto')
        stock_a_agregar = int(data.get('stock', 0))

        if not producto_id or stock_a_agregar <= 0:
            return jsonify({"message": "Datos inválidos."}), 400

        # Actualizar el stock del producto en la base de datos
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE Producto SET stock = stock + ? WHERE id_producto = ?", (stock_a_agregar, producto_id))
        conn.commit()
        conn.close()

        return jsonify({"message": "Stock actualizado exitosamente."}), 200
    except Exception as e:
        print(f"Error al actualizar stock: {e}")
        return jsonify({"message": "Error al actualizar el stock."}), 500

@app.route('/confirmar_pedido', methods=['POST'])
def confirmar_pedido():
    try:
        # Obtener el carrito de la sesión
        carrito = session.get('carrito', [])

        # Verificamos que el carrito esté presente
        print(f"Carrito recibido desde la sesión: {carrito}")

        if not carrito:
            return jsonify({"message": "El carrito está vacío. No se puede procesar el pedido."}), 400

        # Calcular el total
        total = sum(item['precio'] for item in carrito)

        # Conectar a la base de datos y crear un nuevo pedido
        conn = get_db_connection()
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute('INSERT INTO Pedidos (fecha, total, estado, metodo_pago) VALUES (?, ?, ?, ?)',
                     (fecha, total, 'Pendiente', 'Efectivo'))  # Suponiendo que el método de pago es 'Efectivo'
        id_pedido = conn.execute('SELECT last_insert_rowid()').fetchone()[0]

        # Insertar detalles del pedido en la base de datos
        for item in carrito:
            conn.execute('INSERT INTO DetallePedido (id_pedido, id_producto, cantidad, subtotal) VALUES (?, ?, ?, ?)',
                         (id_pedido, item['id'], 1, item['precio']))

        conn.commit()
        conn.close()

        # Limpiar el carrito en la sesión
        session['carrito'] = []

        return jsonify({"message": "Pedido confirmado correctamente"})

    except Exception as e:
        print(f"Error al procesar el carrito: {e}")
        return jsonify({"message": "Error al procesar el carrito. Formato incorrecto."}), 400
@app.route('/flujo_caja')
def flujo_caja():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Consultar los registros de pagos junto con los productos
    cursor.execute("""
        SELECT 
            rp.id_pago,
            rp.fecha_pago,
            p.nombre AS producto,
            rp.cantidad,
            rp.monto_total,
            rp.metodo_pago
        FROM registro_pagos rp
        JOIN Producto p ON rp.id_producto = p.id_producto
        ORDER BY rp.fecha_pago DESC
    """)
    registros = cursor.fetchall()
    conn.close()
    
    # Transformar los datos en una lista de diccionarios
    registros_list = [
        {
            "id_pago": registro[0],
            "fecha_pago": registro[1],
            "producto": registro[2],
            "cantidad": registro[3],
            "monto_total": registro[4],
            "metodo_pago": registro[5]
        }
        for registro in registros
    ]
    
    return render_template('flujo_caja.html', registros=registros_list)

def guardar_pedido_en_bd(carrito, metodo_pago):
    # Calcula el total del carrito
    total = sum(item['precio'] * item['cantidad'] for item in carrito)
    
    conn = get_db_connection()
    
    # Inserta el pedido en la tabla Pedidos
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute('INSERT INTO Pedidos (fecha, total, estado, metodo_pago) VALUES (?, ?, ?, ?)',
                 (fecha, total, 'Pagado', metodo_pago))
    
    # Obtén el ID del pedido recién creado
    id_pedido = conn.execute('SELECT last_insert_rowid()').fetchone()[0]

    # Inserta cada producto del carrito en DetallePedido
    for item in carrito:
        conn.execute('INSERT INTO DetallePedido (id_pedido, id_producto, cantidad, subtotal) VALUES (?, ?, ?, ?)',
                     (id_pedido, item['id'], item['cantidad'], item['precio'] * item['cantidad']))
    
    # Confirma y cierra la conexión
    conn.commit()
    conn.close()

# Ejecuta la aplicación
if __name__ == '__main__':
    app.run(debug=True)