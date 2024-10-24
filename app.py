from flask import Flask, render_template, request, redirect, url_for, flash
from pymongo import MongoClient
from flask import  g
import sqlite3

app = Flask(__name__)
app.secret_key = '123456789'
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Conectar a la base de datos SQLite
        conn = sqlite3.connect('cliente.db')
        cursor = conn.cursor()

        # Verificar si el usuario existe
        cursor.execute('SELECT * FROM Usuario WHERE usuario = ?', (username,))
        user = cursor.fetchone()
        conn.close()

        if user and user[1] == password:  # user[1] debe ser la columna de la contraseña
            flash('Inicio de sesión exitoso', 'success')
            return redirect(url_for('home'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')
# Ruta para la página principal
@app.route('/')
def index():
    return render_template('login.html')

# Ruta para la página de inicio
@app.route('/home')
def home():
    # Conexión a la base de datos
    conn = sqlite3.connect('cliente.db')
    cursor = conn.cursor()

    # Consulta para obtener los productos
    cursor.execute("SELECT id_producto, nombre, detalle, precio, stock FROM Producto")
    products = cursor.fetchall()

    # Cerramos la conexión
    conn.close()

    # Transformamos los resultados en una lista de diccionarios
    product_list = []
    for product in products:
        product_list.append({
            'id_producto': product[0],
            'nombre': product[1],
            'detalle': product[2],
            'precio': product[3],
            'stock': product[4]
        })

    # Pasamos los productos a la plantilla
    return render_template('home.html', products=product_list)
#Ruta Pagina Detalle Pedido
@app.route('/detalle')
def detalle():
    return render_template('detalle.html')
#Ruta Pagina Caja
@app.route('/caja')
def caja():
    return render_template('caja.html')
#Ruta Pagina Productos
@app.route('/crear_categoria')
def crear_categoria():
    return render_template('crear_categoria.html')
@app.route('/error')
def error():
    return render_template("error.html")
# Rutas para registrar entidades
@app.route('/crear_producto', methods=['GET', 'POST'])
def crear_producto():
    if request.method == 'POST':
        nombre = request.form['nombre']
        precio = float(request.form['precio'])
        stock = int(request.form['stock'])
        id_categoria = int(request.form['id_categoria'])
        bd.registrar_producto(nombre, precio, stock, id_categoria)
        return redirect('/')
    return render_template('crear_producto.html')
# Rutas para consultas y reportes
@app.route('/consultar_info', methods=['GET', 'POST'])
def consultar_info():
    if request.method == 'POST':
        tipo_consulta = request.form['tipo_consulta']
        id_entidad = int(request.form['id_entidad'])
        if tipo_consulta == 'producto':
            info = bd.consultar_info_producto(id_entidad)
        elif tipo_consulta == 'categoria':
            info = bd.consultar_info_categoria(id_entidad)
        return render_template('consultar_info.html', info=info)
    return render_template('consultar_info.html')

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
# Ejecuta la aplicación
if __name__ == '__main__':
    app.run(debug=True)
