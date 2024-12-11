
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
from flask_login import login_required, current_user
from flask_login import LoginManager
from flask_login import login_user
from flask_login import UserMixin
from flask_login import logout_user

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

class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

    @staticmethod
    def get(user_id):
        # Recupera al usuario desde la base de datos según su ID
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM Usuario WHERE id_usuario = ?', (user_id,))
        user = cursor.fetchone()
        conn.close()
        if user:
            return User(user['id_usuario'], user['usuario'])
        return None

login_manager = LoginManager()
login_manager.init_app(app)

# Redirigir a la página de inicio de sesión si el usuario no está autenticado
login_manager.login_view = 'login'  # Nombre de tu función para el login
login_manager.login_message = "Por favor, inicia sesión para acceder a esta página."

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)
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
            # Crear instancia del usuario
            authenticated_user = User(user['id_usuario'], user['usuario'])

            # Autenticar al usuario
            login_user(authenticated_user)

            session.pop('carrito', None)  # Opcional: borra el carrito de la sesión
            flash('Inicio de sesión exitoso', 'success')
            return redirect(url_for('home'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
            return redirect(url_for('login'))

    return render_template('login.html', show_navbar=False)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Has cerrado sesión exitosamente.", "success")
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
@app.route('/vaciar_carrito', methods=['POST'])
@login_required
def vaciar_carrito():
    # Eliminar el carrito de la sesión
    session.pop('carrito', None)
    session.modified = True  # Asegura que la sesión se actualice

    flash("El carrito ha sido vaciado.", "success")
    return redirect(url_for('menu'))

@app.route('/menu')
@login_required
def menu():
    # Obtiene los productos del menú de la base de datos
    conn = get_db_connection()
    cursor = conn.cursor()

    # Consulta de productos
    cursor.execute("SELECT id_producto, nombre, descripcion, precio, stock FROM Producto")
    productos = cursor.fetchall()

    # Consulta de promociones
    cursor.execute("SELECT id, nombre, productos, precio FROM Promociones")
    promociones = cursor.fetchall()

    promociones_validas = []
    for promocion in promociones:
        promocion_id = promocion[0]
        promocion_nombre = promocion[1]
        productos_ids = [int(id.strip()) for id in promocion[2].split(',') if id.strip().isdigit()]
        promocion_precio = promocion[3]

        # Verificar si todos los productos de la promoción existen
        cursor.execute("SELECT COUNT(*) FROM Producto WHERE id_producto IN ({})".format(
            ','.join(['?'] * len(productos_ids))
        ), productos_ids)
        productos_existentes = cursor.fetchone()[0]

        if productos_existentes == len(productos_ids):
            # Si todos los productos existen, la promoción es válida
            promociones_validas.append({
                'id': promocion_id,
                'nombre': promocion_nombre,
                'productos': promocion[2],
                'precio': promocion_precio
            })
        else:
            # Eliminar la promoción inválida
            cursor.execute("DELETE FROM Promociones WHERE id = ?", (promocion_id,))
            conn.commit()

    conn.close()

    # Transformar productos en una lista de diccionarios
    productos_lista = []
    for producto in productos:
        productos_lista.append({
            'id_producto': producto[0],
            'nombre': producto[1],
            'descripcion': producto[2],
            'precio': producto[3],
            'stock': producto[4]
        })

    # Pasamos los productos y las promociones al template
    return render_template(
        'menu.html',
        productos=productos_lista,
        promociones=promociones_validas,
        show_navbar=True
    )

@app.route('/agregar_al_carrito_ajax', methods=['POST'])
@login_required
def agregar_al_carrito_ajax():
    item_id = request.json.get('producto_id')  # Puede ser producto o promoción
    nombre = request.json.get('nombre')
    precio = float(request.json.get('precio'))

    # Si el ID comienza con "promocion-", es una promoción
    if str(item_id).startswith('promocion-'):
        promocion_id = int(item_id.split('-')[1])  # Extrae el ID de la promoción
        return agregar_promocion_al_carrito(promocion_id, nombre, precio)

    # Si no es promoción, trata como un producto normal
    return agregar_producto_al_carrito(item_id, nombre, precio)


def agregar_producto_al_carrito(producto_id, nombre, precio):
    # Conectar a la base de datos para verificar el stock
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT stock FROM Producto WHERE id_producto = ?", (producto_id,))
    producto = cursor.fetchone()
    conn.close()

    # Validar que haya stock disponible
    if not producto or producto[0] <= 0:  # Cambié producto['stock'] por producto[0]
        return {"success": False, "message": f"No hay suficiente stock para {nombre}."}, 400

    # Inicializa el carrito si no existe en la sesión
    if 'carrito' not in session:
        session['carrito'] = []

    carrito = session['carrito']

    # Verifica si existe un producto exactamente igual en el carrito
    for item in carrito:
        if item['id'] == producto_id:
            # Incrementa la cantidad en el carrito, pero verifica el stock
            if item['cantidad'] < producto[0]:  # Verifica stock
                item['cantidad'] += 1
                item['precio_total'] += precio
                session.modified = True
                return {"success": True, "message": f"¡{nombre} añadido al carrito!"}
            else:
                return {"success": False, "message": f"No puedes agregar más de {producto[0]} unidades de {nombre}."}, 400
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


def agregar_promocion_al_carrito(promocion_id, nombre, precio):
    # Inicializa el carrito si no existe en la sesión
    if 'carrito' not in session:
        session['carrito'] = []

    carrito = session['carrito']

    # Verifica si la promoción ya está en el carrito
    for item in carrito:
        if item['id'] == f"promocion-{promocion_id}":
            # Las promociones se manejan como cantidades individuales
            item['cantidad'] += 1
            item['precio_total'] += precio
            session.modified = True
            return {"success": True, "message": f"¡{nombre} añadido al carrito!"}

    # Si la promoción no está en el carrito, la agrega como nueva
    carrito.append({
        'id': f"promocion-{promocion_id}",
        'nombre': nombre,
        'precio_unitario': precio,
        'cantidad': 1,
        'precio_total': precio
    })

    session.modified = True
    return {"success": True, "message": f"¡{nombre} añadido al carrito!"}

@app.route('/carrito')
@login_required
def ver_carrito():
    # Recupera el carrito de la sesión
    carrito = session.get('carrito', [])
    
    # Calcula el total
    total = sum(item['precio_total'] for item in carrito)

    # Renderiza la página del carrito con los datos
    return render_template('carrito.html', carrito=carrito, total=total)
    session.modified = True

@app.route('/obtener_carrito_total', methods=['GET'])
@login_required
def obtener_carrito_total():
    total_items = 0
    if 'carrito' in session:
        carrito = session['carrito']
        total_items = sum(item['cantidad'] for item in carrito)
    return {"total_items": total_items}
@app.route('/carrito/<producto_id>', methods=['POST'])
@login_required
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
@app.template_filter('clp')
def format_clp(value):
    try:
        return "{:,.0f}".format(value).replace(",", ".")
    except (ValueError, TypeError):
        return value
@app.route('/modificar_usuario', methods=['POST'])
@login_required
def modificar_usuario_post():
    id_usuario = request.form['id_usuario']
    nuevo_usuario = request.form['usuario']
    nueva_contraseña = request.form['contraseña']

    conn = get_db_connection()
    conn.execute(
        'UPDATE usuario SET usuario = ?, contrasena = ? WHERE id_usuario = ?',
        (nuevo_usuario, nueva_contraseña, id_usuario)
    )
    conn.commit()
    conn.close()
    return redirect(url_for('ver_usuarios'))

@app.route('/boleta/<int:id_pago>/pdf', methods=['GET'])
@login_required
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
                CASE 
                    WHEN rp.id_producto LIKE 'promocion-%' THEN pr.nombre 
                    ELSE p.nombre 
                END AS producto,
                rp.cantidad,
                CASE 
                    WHEN rp.id_producto LIKE 'promocion-%' THEN rp.monto_total / rp.cantidad 
                    ELSE p.precio 
                END AS precio_unitario,
                rp.monto_total AS valor_acumulado,
                rp.metodo_pago,
                SUM(rp.monto_total) OVER (PARTITION BY rp.id_pago) AS total_pago
            FROM registro_pagos rp
            LEFT JOIN Producto p ON rp.id_producto = p.id_producto
            LEFT JOIN Promociones pr ON rp.id_producto = 'promocion-' || pr.id
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
                "precio_unitario": round(row[4]),
                "valor_acumulado": round(row[5])
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
@app.route('/boletas', methods=['GET', 'POST'])
@login_required
def listar_boletas():
    if request.method == 'POST':
        # Manejar agregar retiro
        try:
            monto = float(request.form['monto'])
            descripcion = request.form['descripcion']
            metodo_pago = request.form['metodo_pago']

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO registro_retiros (monto, descripcion, metodo_pago)
                VALUES (?, ?, ?)
            """, (monto, descripcion, metodo_pago))
            conn.commit()
            conn.close()

            flash('Retiro agregado exitosamente.', 'success')
        except Exception as e:
            flash(f'Error al agregar el retiro: {e}', 'danger')
        return redirect(url_for('listar_boletas'))

    # Parámetros para boletas
    id_pago = request.args.get('id_pago')
    fecha = request.args.get('fecha')
    page = int(request.args.get('page', 1))
    per_page = 10
    offset = (page - 1) * per_page

    # Parámetros para retiros
    retiro_page = int(request.args.get('retiro_page', 1))
    retiro_per_page = 5  # Cambia este valor si necesitas más retiros por página
    retiro_offset = (retiro_page - 1) * retiro_per_page

    conn = get_db_connection()
    cursor = conn.cursor()

    # Consultas de boletas
    count_query = """
        SELECT COUNT(DISTINCT rp.id_pago)
        FROM registro_pagos rp
        WHERE 1 = 1
    """
    data_query = """
        SELECT rp.id_pago, rp.fecha_pago, SUM(rp.monto_total) AS monto_total, rp.metodo_pago
        FROM registro_pagos rp
        WHERE 1 = 1
        GROUP BY rp.id_pago, rp.fecha_pago, rp.metodo_pago
        ORDER BY rp.fecha_pago DESC
        LIMIT ? OFFSET ?
    """
    params = [per_page, offset]

    if id_pago:
        count_query += " AND rp.id_pago = ?"
        data_query = data_query.replace("WHERE 1 = 1", "WHERE 1 = 1 AND rp.id_pago = ?")
        params = [id_pago, per_page, offset]

    if fecha:
        count_query += " AND DATE(rp.fecha_pago) = ?"
        data_query = data_query.replace("WHERE 1 = 1", "WHERE 1 = 1 AND DATE(rp.fecha_pago) = ?")
        params = [fecha, per_page, offset]

    # Contar total de boletas
    cursor.execute(count_query, params[:-2])
    total_boletas = cursor.fetchone()[0]
    total_paginas = (total_boletas + per_page - 1) // per_page

    # Obtener boletas
    cursor.execute(data_query, params)
    boletas = cursor.fetchall()

    # Consultas de retiros
    retiro_count_query = "SELECT COUNT(*) FROM registro_retiros"
    retiro_query = """
        SELECT id, fecha, monto, metodo_pago, descripcion
        FROM registro_retiros
        ORDER BY fecha DESC
        LIMIT ? OFFSET ?
    """
    cursor.execute(retiro_count_query)
    total_retiros = cursor.fetchone()[0]
    retiro_total_paginas = (total_retiros + retiro_per_page - 1) // retiro_per_page

    cursor.execute(retiro_query, (retiro_per_page, retiro_offset))
    retiros = cursor.fetchall()

    conn.close()

    # Transformar datos a listas de diccionarios
    boletas_data = [
        {"id_pago": boleta[0], "fecha_pago": boleta[1], "monto_total": boleta[2], "metodo_pago": boleta[3]}
        for boleta in boletas
    ]
    retiros_data = [
        {"id": retiro[0], "fecha": retiro[1], "monto": retiro[2], "metodo_pago": retiro[3], "descripcion": retiro[4]}
        for retiro in retiros
    ]

    return render_template(
        'listar_boletas.html',
        boletas=boletas_data,
        retiros=retiros_data,
        page=page,
        total_paginas=total_paginas,
        total_boletas=total_boletas,
        retiro_page=retiro_page,
        retiro_total_paginas=retiro_total_paginas,
        show_navbar=True
    )
def convertir_html_a_pdf(source_html):
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(source_html.encode("UTF-8")), result)
    if not pdf.err:
        return result.getvalue()
    return None


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
@app.route('/crear_producto', methods=['GET', 'POST'])
@login_required
def crear_producto():
    if request.method == 'POST':
        try:
            data = request.get_json()
            nombre = data.get('nombre')
            descripcion = data.get('descripcion')  # Puede ser None
            precio = data.get('precio', 0)
            stock = int(data.get('stock', 0))
            tipo = data.get('tipo', 'producto')  # Valor predeterminado

            # Asegurar que el precio sea un entero
            if not isinstance(precio, int):
                return jsonify({"message": "El precio debe ser un número entero."}), 400

            # Validar campos
            if not nombre or precio <= 0 or stock < 0 or precio > 99999:
                return jsonify({"message": "Todos los campos son obligatorios y deben tener valores válidos. El precio no puede exceder 99,999."}), 400

            conn = get_db_connection()
            cursor = conn.cursor()

            # Insertar el nuevo producto
            cursor.execute("""
                INSERT INTO Producto (nombre, descripcion, precio, stock, tipo)
                VALUES (?, ?, ?, ?, ?)
            """, (nombre, descripcion, precio, stock, tipo))
            conn.commit()
            conn.close()

            return jsonify({"message": f"Producto '{nombre}' agregado exitosamente."}), 200
        except Exception as e:
            print(f"Error al agregar producto: {e}")
            return jsonify({"message": "Error al agregar el producto."}), 500

    return render_template('crear_producto.html', show_navbar=True)

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
@login_required
def simulacion_pago():
    if request.method == 'POST':
        metodo_pago = request.form.get('metodo_pago')  # Obtener método de pago
        carrito = session.get('carrito', [])  # Obtener carrito de la sesión
        id_usuario = session.get('user_id')  # Obtener ID del usuario autenticado

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

            # Registrar cada elemento del carrito
            for item in carrito:
                if str(item['id']).startswith("promocion"):
                    # Manejo de promociones
                    promocion_id = int(item['id'].split('-')[1])

                    # Registrar la promoción como un solo ítem en `registro_pagos`
                    cursor.execute(
                        """
                        INSERT INTO registro_pagos (id_pago, fecha_pago, id_producto, cantidad, monto_total, metodo_pago, estado, id_usuario)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (id_pago, fecha_pago, item['id'], item['cantidad'], item['precio_total'], metodo_pago, "pendiente", id_usuario)
                    )

                    # Obtener productos asociados a la promoción
                    cursor.execute(
                        "SELECT productos FROM Promociones WHERE id = ?",
                        (promocion_id,)
                    )
                    promocion = cursor.fetchone()
                    if not promocion:
                        raise ValueError(f"La promoción con ID {promocion_id} no existe.")

                    productos_ids = promocion[0].split(",")  # Lista de IDs de productos

                    # Registrar ventas y actualizar el stock de cada producto en la promoción
                    for producto_id in productos_ids:
                        cursor.execute("SELECT nombre, stock FROM Producto WHERE id_producto = ?", (producto_id,))
                        producto = cursor.fetchone()
                        if not producto:
                            raise ValueError(f"Producto con ID {producto_id} no encontrado.")

                        # Registrar la venta
                        cursor.execute(
                            """
                            INSERT INTO ventas (id_producto, cantidad, fecha_venta)
                            VALUES (?, ?, ?)
                            """,
                            (producto_id, item['cantidad'], fecha_pago)
                        )

                        # Actualizar el stock
                        cursor.execute(
                            """
                            UPDATE Producto
                            SET stock = stock - ?
                            WHERE id_producto = ?
                            """,
                            (item['cantidad'], producto_id)
                        )

                        # Verificar si el stock quedó en negativo
                        cursor.execute(
                            "SELECT stock FROM Producto WHERE id_producto = ?",
                            (producto_id,)
                        )
                        stock_actual = cursor.fetchone()[0]
                        if stock_actual < 0:
                            raise ValueError(f"El stock del producto con ID {producto_id} es insuficiente.")
                else:
                    # Manejo de productos normales
                    cursor.execute(
                        """
                        INSERT INTO registro_pagos (id_pago, fecha_pago, id_producto, cantidad, monto_total, metodo_pago, estado, id_usuario)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (id_pago, fecha_pago, item['id'], item['cantidad'], item['precio_total'], metodo_pago, "pendiente", id_usuario)
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
@login_required
def ver_productos():
    conn = sqlite3.connect('cliente.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM Producto')
    productos = cursor.fetchall()
    conn.close()
    return render_template('ver_productos.html', productos=productos)
@app.route('/ver_usuarios')
@login_required
def ver_usuarios():
    conn = sqlite3.connect('cliente.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM Usuario')
    usuarios = cursor.fetchall()
    conn.close()
    return render_template('ver_usuarios.html', usuarios=usuarios, show_navbar=True)
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
@login_required
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
@login_required
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
@app.route('/eliminar_usuario/<int:usuario_id>', methods=['POST'])
@login_required
def eliminar_usuario(usuario_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Verificar si el usuario existe
        cursor.execute("SELECT id_usuario FROM usuario WHERE id_usuario = ?", (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario:
            flash("El usuario no existe.", "error")
            return redirect(url_for('ver_usuarios'))

        # Intentar eliminar
        cursor.execute("DELETE FROM usuario WHERE id_usuario = ?", (usuario_id,))
        conn.commit()
        conn.close()

        flash("Usuario eliminado exitosamente.", "success")
    except Exception as e:
        print(f"Error al eliminar usuario: {e}")
        flash(f"Error al eliminar usuario: {e}", "error")

    return redirect(url_for('ver_usuarios'))

@app.route('/eliminar_producto', methods=['POST'])
@login_required
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
    
@app.route('/actualizar_producto', methods=['POST'])
@login_required
def actualizar_producto():
    # Obtener los datos del formulario
    producto_id = request.form['id_producto']
    nombre = request.form['nombre']
    descripcion = request.form['descripcion']
    precio = float(request.form['precio'])
    stock = int(request.form['stock'])
    # Obtiene la lista de productos desde la base de datos
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if descripcion:  # Si la descripción está presente
            cursor.execute('''
                UPDATE Producto
                SET nombre = ?, descripcion = ?, precio = ?, stock = ?
                WHERE id_producto = ?
            ''', (nombre, descripcion, precio, stock, producto_id))
        else:  # Si no hay descripción, no la actualices
            cursor.execute('''
                UPDATE Producto
                SET nombre = ?, precio = ?, stock = ?
                WHERE id_producto = ?
            ''', (nombre, precio, stock, producto_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error al actualizar la base de datos: {e}")
        flash("Hubo un error al actualizar el producto.", "danger")
    finally:
        conn.close()    
    flash('Producto actualizado correctamente.', 'success')
    return redirect(url_for('inventario'))

@app.route('/inventario', methods=['GET'])
@login_required
def inventario():
    # Parámetros de paginación y ordenación
    page = int(request.args.get('page', 1))  # Página actual, por defecto 1
    per_page = 10  # Número de productos por página
    offset = (page - 1) * per_page  # Desplazamiento
    order_by = request.args.get('order_by', 'id_producto')  # Columna para ordenar
    order_dir = request.args.get('order_dir', 'asc')  # Dirección de orden: asc o desc

    # Validar columnas para ordenar
    valid_columns = ['id_producto', 'nombre', 'precio', 'stock']
    if order_by not in valid_columns:
        order_by = 'id_producto'

    # Validar dirección de orden
    if order_dir not in ['asc', 'desc']:
        order_dir = 'asc'

    # Conexión a la base de datos
    conn = get_db_connection()
    cursor = conn.cursor()

    # Contar el total de productos para la tabla
    cursor.execute("SELECT COUNT(*) FROM Producto")
    total_productos = cursor.fetchone()[0]
    total_paginas = (total_productos + per_page - 1) // per_page  # Calcular total de páginas

    # Consultar productos con paginación y ordenación para la tabla
    query = f"""
        SELECT id_producto, nombre, descripcion, precio, stock 
        FROM Producto
        ORDER BY {order_by} {order_dir}
        LIMIT ? OFFSET ?
    """
    cursor.execute(query, (per_page, offset))
    productos_tabla = cursor.fetchall()

    # Consultar todos los productos para el carrusel (sin paginación)
    cursor.execute("SELECT id_producto, nombre, descripcion, precio, stock FROM Producto ORDER BY id_producto ASC")
    productos_carrusel = cursor.fetchall()

    conn.close()

    # Transformar los datos en listas de diccionarios
    productos_data_tabla = [
        {"id_producto": prod[0], "nombre": prod[1], "descripcion": prod[2], "precio": prod[3], "stock": prod[4]}
        for prod in productos_tabla
    ]

    productos_data_carrusel = [
       {"id_producto": prod[0], "nombre": prod[1], "descripcion": prod[2], "precio": prod[3], "stock": prod[4]}
        for prod in productos_carrusel
    ]

    # Renderizar plantilla
    return render_template(
        'inventario.html',
        productos=productos_data_tabla,  # Solo los productos paginados para la tabla
        productos_carrusel=productos_data_carrusel,  # Todos los productos para el carrusel
        page=page,
        total_paginas=total_paginas,
        total_productos=total_productos,
        order_by=order_by,
        order_dir=order_dir,
        show_navbar=True
    )

import matplotlib.pyplot as plt
from io import BytesIO
import base64

@app.route('/analisis_ventas')
@login_required
def analisis_ventas():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Ventas Diarias
        cursor.execute("""
            SELECT strftime('%Y-%m-%d', fecha_pago) AS fecha, SUM(monto_total) AS total 
            FROM registro_pagos 
            GROUP BY fecha
        """)
        data_ventas_diarias = cursor.fetchall()
        fechas_diarias = [row[0] for row in data_ventas_diarias]
        totales_diarios = [row[1] for row in data_ventas_diarias]

        # Ventas Mensuales
        cursor.execute("""
            SELECT strftime('%Y-%m', fecha_pago) AS mes, SUM(monto_total) AS total 
            FROM registro_pagos 
            GROUP BY mes
        """)
        data_ventas_mensuales = cursor.fetchall()
        meses = [row[0] for row in data_ventas_mensuales]
        totales_mensuales = [row[1] for row in data_ventas_mensuales]

        # Generar gráficos
        def generar_grafico(x, y, titulo, xlabel, ylabel, color, grid=True):
            plt.style.use('ggplot')
            plt.figure(figsize=(10, 6))
            plt.bar(x, y, color=color, alpha=0.9, edgecolor="black", linewidth=1.2)
            plt.title(titulo, fontsize=16, fontweight='bold', color='black', loc='center')
            plt.xlabel(xlabel, fontsize=14, color='black')
            plt.ylabel(ylabel, fontsize=14, color='black')
            plt.xticks(rotation=45, fontsize=12, color='black')
            plt.yticks(fontsize=12, color='black')
            if grid:
                plt.grid(axis='y', linestyle='--', alpha=0.7)
            plt.tight_layout()
            for i, val in enumerate(y):
                plt.text(i, val, f'${val:,}', ha='center', va='bottom', fontsize=10, fontweight='bold', color='black')
            img = BytesIO()
            plt.savefig(img, format='png', dpi=300)
            img.seek(0)
            return base64.b64encode(img.getvalue()).decode()

        # Crear imágenes
        img_url_ventas_diarias = generar_grafico(
            fechas_diarias, totales_diarios, 
            'Ventas Diarias', 'Fecha', 'Monto Total ($)', 'skyblue'
        )
        img_url_ventas_mensuales = generar_grafico(
            meses, totales_mensuales, 
            'Ventas Mensuales', 'Mes', 'Monto Total ($)', 'mediumpurple'
        )

        # Renderizar la plantilla con los gráficos
        return render_template(
            'analisis_ventas.html',
            img_url_ventas_diarias=img_url_ventas_diarias,
            img_url_ventas_mensuales=img_url_ventas_mensuales,
            show_navbar=True
        )

    except Exception as e:
        flash(f"Error al generar el análisis: {str(e)}", "danger")
        return redirect(url_for('home'))

    finally:
        if conn:
            conn.close()



@app.route('/promociones', methods=['GET'])
def promociones():
    conn = sqlite3.connect('cliente.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, productos, precio FROM Promociones")
    promociones = cursor.fetchall()
    conn.close()

    return render_template('promociones.html', promociones=promociones)
@app.route('/guardar_promocion', methods=['POST'])
@login_required
def guardar_promocion():
    data = request.get_json()
    productos = data.get('productos')  # Lista de IDs de productos seleccionados
    precio_promocional = data.get('precio_promocional')

    if not productos:
        return jsonify({'success': False, 'message': 'Debe seleccionar al menos un producto.'}), 400

    conn = sqlite3.connect('cliente.db')
    cursor = conn.cursor()

    # Obtener los nombres de los productos seleccionados
    nombres_productos = []
    for producto_id in productos:
        cursor.execute("SELECT nombre FROM Producto WHERE id_producto = ?", (producto_id,))
        nombres_productos.append(cursor.fetchone()[0])

    # Crear la promoción como una combinación de productos
    promocion_nombre = " + ".join(nombres_productos)
    promocion_precio = float(precio_promocional) if precio_promocional else sum(
        cursor.execute("SELECT precio FROM Producto WHERE id_producto = ?", (producto_id,)).fetchone()[0]
        for producto_id in productos
    )
    # Obtener los nombres y validar stock de los productos seleccionados
    nombres_productos = []
    for producto_id in productos:
        cursor.execute("SELECT nombre, stock FROM Producto WHERE id_producto = ?", (producto_id,))
        producto = cursor.fetchone()
        if not producto or producto[1] <= 0:
            return jsonify({'success': False, 'message': f"Producto con ID {producto_id} no es válido o no tiene stock."}), 400
        nombres_productos.append(producto[0])

    # Guardar la promoción en una tabla dedicada
    cursor.execute('''
        INSERT INTO Promociones (nombre, productos, precio)
        VALUES (?, ?, ?)
    ''', (promocion_nombre, ','.join(map(str, productos)), promocion_precio))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': 'Promoción creada exitosamente.'})
@app.route('/crear_promocion', methods=['GET', 'POST'])
@login_required
def crear_promocion():
    if request.method == 'POST':
        # Capturar datos del formulario
        productos = request.form.getlist('productos')  # Lista de IDs de productos seleccionados
        precio = request.form.get('precio', 0)  # Precio de la promoción, o 0 si está vacío

        if not productos:
            flash("Debes seleccionar al menos un producto.", "danger")
            return redirect(url_for('crear_promocion'))

        # Generar el nombre dinámicamente
        conn = sqlite3.connect('cliente.db')
        cursor = conn.cursor()
        cursor.execute(f"SELECT nombre FROM Producto WHERE id_producto IN ({','.join('?' for _ in productos)})", productos)
        nombres_productos = [row[0] for row in cursor.fetchall()]
        nombre_promocion = " + ".join(nombres_productos)

        # Convertir lista de productos a cadena separada por comas
        productos_str = ','.join(productos)

        # Validar si la promoción ya existe
        cursor.execute("SELECT COUNT(*) FROM Promociones WHERE productos = ? AND precio = ?", (productos_str, float(precio)))
        promocion_existente = cursor.fetchone()[0]

        if promocion_existente > 0:
            conn.close()
            flash("Ya existe una promoción con los mismos productos y precio.", "danger")
            return redirect(url_for('crear_promocion'))

        try:
            # Inserción de promoción
            cursor.execute("INSERT INTO Promociones (nombre, productos, precio) VALUES (?, ?, ?)",
                        (nombre_promocion, productos_str, float(precio)))
            conn.commit()
            flash("Promoción creada exitosamente.", "success")
        except sqlite3.OperationalError as e:
            flash(f"Error en la base de datos: {e}", "danger")
        except sqlite3.IntegrityError:
            flash("Ya existe una promoción con los mismos productos.", "danger")
        finally:
            conn.close()


    # Método GET: Mostrar los productos disponibles para crear promociones
    conn = sqlite3.connect('cliente.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id_producto, nombre, precio FROM Producto")
    productos = cursor.fetchall()
    conn.close()

    return render_template('crear_promocion.html', productos=productos, show_navbar=True)
@app.template_filter('format_clp')
@login_required
def format_clp(value):
    return f"${int(value):,}".replace(",", ".")

@app.route('/eliminar_promocion/<int:id>', methods=['POST'])
@login_required
def eliminar_promocion(id):
    conn = sqlite3.connect('cliente.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Promociones WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    flash("Promoción eliminada exitosamente.", "success")
    return redirect(url_for('menu'))

@app.route('/agregar_promocion_carrito', methods=['POST'])
@login_required
def agregar_promocion_carrito():
    data = request.get_json()
    promocion_id = data.get('promocion_id')

    if not promocion_id:
        return jsonify({'success': False, 'message': 'Promoción no válida.'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    # Obtener los productos asociados a la promoción
    cursor.execute("SELECT productos, nombre, precio FROM Promociones WHERE id = ?", (promocion_id,))
    promocion = cursor.fetchone()
    if not promocion:
        conn.close()
        return jsonify({'success': False, 'message': 'Promoción no encontrada.'}), 404

    productos_ids = [id.strip() for id in promocion[0].split(',') if id.strip().isdigit()]  # Lista de IDs de productos
    promocion_nombre = promocion[1]  # Nombre de la promoción
    promocion_precio = promocion[2]  # Precio total de la promoción
    productos_stock_insuficiente = []

    # Verificar el stock de cada producto asociado a la promoción
    for producto_id in productos_ids:
        cursor.execute("SELECT nombre, stock FROM Producto WHERE id_producto = ?", (producto_id,))
        producto = cursor.fetchone()

        if not producto:  # Si el producto no existe
            conn.close()
            return jsonify({'success': False, 'message': f"Producto con ID {producto_id} no encontrado."}), 404

        if producto[1] <= 0:  # Si no hay stock suficiente
            productos_stock_insuficiente.append(producto[0])

        print(f"[DEBUG] Producto ID: {producto_id}, Nombre: {producto[0]}, Stock: {producto[1]}")

    # Si algún producto no tiene stock suficiente, informar al cliente
    if productos_stock_insuficiente:
        conn.close()
        return jsonify({
            'success': False,
            'message': f"No hay suficiente stock para: {', '.join(productos_stock_insuficiente)}."
        })

    # Reducir el stock de cada producto asociado a la promoción
    for producto_id in productos_ids:
        cursor.execute(
            "UPDATE Producto SET stock = stock - 1 WHERE id_producto = ? AND stock > 0",
            (producto_id,)
        )

    conn.commit()
    conn.close()

    # Agregar la promoción al carrito
    if 'carrito' not in session:
        session['carrito'] = []

    carrito = session['carrito']

    # Verificar si la promoción ya existe en el carrito
    for item in carrito:
        if item['id'] == f"promocion-{promocion_id}":
            # Incrementar la cantidad y el precio total si ya existe
            item['cantidad'] += 1
            item['precio_total'] += promocion_precio
            session.modified = True
            return jsonify({'success': True, 'message': f"¡{promocion_nombre} añadida al carrito!"})

    # Si la promoción no está en el carrito, agregarla como un nuevo elemento
    carrito.append({
        'id': f"promocion-{promocion_id}",
        'nombre': promocion_nombre,
        'precio_unitario': promocion_precio,
        'cantidad': 1,
        'precio_total': promocion_precio
    })

    session.modified = True
    return jsonify({'success': True, 'message': f"¡{promocion_nombre} añadida al carrito!"})
@app.route('/chef/marcar_listo/<int:id_pago>/<string:id_producto>', methods=['POST'])
@login_required
def marcar_pedido_listo(id_pago, id_producto):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Actualizar el estado del ítem específico a "listo"
        cursor.execute("""
            UPDATE registro_pagos 
            SET estado = 'listo'
            WHERE id_pago = ? AND id_producto = ?
        """, (id_pago, id_producto))
        conn.commit()
        conn.close()

        flash("Ítem del pedido marcado como listo.", "success")
    except Exception as e:
        print(f"Error al marcar ítem del pedido como listo: {e}")
        flash("Hubo un error al marcar el ítem del pedido como listo.", "error")

    # Redirigir a la vista del chef
    return redirect(url_for('vista_chef'))

@app.route('/chef', methods=['GET'])
@login_required
def vista_chef():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Obtener todos los registros de pedidos pendientes
    cursor.execute("""
        SELECT 
            rp.id_pago,
            rp.metodo_pago,
            CASE 
                WHEN rp.id_producto LIKE 'promocion-%' THEN pr.nombre  -- Nombre de la promoción
                ELSE p.nombre  -- Nombre del producto
            END AS producto,
            rp.cantidad,
            rp.monto_total AS subtotal,
            rp.id_producto  -- Asegúrate de incluir esta columna
        FROM registro_pagos rp
        LEFT JOIN Producto p ON rp.id_producto = p.id_producto
        LEFT JOIN Promociones pr ON rp.id_producto = 'promocion-' || pr.id
        WHERE rp.estado = 'pendiente'
        ORDER BY rp.id_pago, rp.id_producto;
    """)

    pedidos = cursor.fetchall()
    conn.close()

    # Transformar los datos en una lista de diccionarios
    pedidos_data = [
        {
            "id_pago": row[0],       # ID del pago
            "metodo_pago": row[1],  # Método de pago
            "producto": row[2],     # Nombre del producto o promoción
            "cantidad": row[3],     # Cantidad
            "subtotal": row[4],     # Subtotal
            "id_producto": row[5]   # ID del producto o promoción
        }
        for row in pedidos
    ]
    if not pedidos_data:
        flash("No hay pedidos pendientes.", "info")
        return render_template('vista_chef.html', pedidos=[], show_navbar=True)

    return render_template('vista_chef.html', pedidos=pedidos_data, show_navbar=True)
@app.route('/agregar_retiro', methods=['POST'])
@login_required
def agregar_retiro():
    try:
        # Obtener los datos del formulario
        monto = request.form['monto']
        descripcion = request.form['descripcion']
        metodo_pago = request.form['metodo_pago']
        conn = sqlite3.connect('cliente.db')
        cursor = conn.cursor()

        # Insertar los datos en la tabla
        cursor.execute(
            "INSERT INTO registro_retiros (monto, descripcion, metodo_pago) VALUES (?, ?, ?)",
            (monto, descripcion, metodo_pago)
        )
        conn.commit()
        conn.close()

        # Mensaje de éxito y redirección
        flash('Retiro agregado exitosamente.', 'success')
        return redirect(url_for('listar_boletas'))

    except Exception as e:
        # Mensaje de error
        flash(f'Error al agregar el retiro: {e}', 'danger')
        return redirect(url_for('listar_boletas'))
@app.route('/eliminar_retiro/<int:id>', methods=['POST'])
@login_required
def eliminar_retiro(id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM registro_retiros WHERE id = ?", (id,))
        conn.commit()
        conn.close()
        flash('Retiro eliminado correctamente.', 'success')
    except Exception as e:
        flash(f'Error al eliminar el retiro: {e}', 'danger')
    return redirect(url_for('listar_boletas'))
@app.route('/modificar_retiro', methods=['POST'])
@login_required
def modificar_retiro():
    try:
        id = request.form['id']
        monto = float(request.form['monto'])
        metodo_pago = request.form['metodo_pago']
        descripcion = request.form['descripcion']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE registro_retiros
            SET monto = ?, metodo_pago = ?, descripcion = ?
            WHERE id = ?
        """, (monto, metodo_pago, descripcion, id))
        conn.commit()
        conn.close()
        flash('Retiro modificado correctamente.', 'success')
    except Exception as e:
        flash(f'Error al modificar el retiro: {e}', 'danger')
    return redirect(url_for('listar_boletas'))
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)