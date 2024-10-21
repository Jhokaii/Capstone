from flask import Flask, render_template, request, redirect, url_for, flash
from pymongo import MongoClient
from flask import  g
import sqlite3

# Crear instancia de Flask
app = Flask(__name__)


# Ruta principal de la aplicación
@app.route('/')
def index():
    return render_template('index.html')
#Ruta Pagina Home
@app.route('/home')
def home():
    return render_template('home.html')
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
        gestion_inventario.registrar_producto(nombre, precio, stock, id_categoria)
        return redirect('/')
    return render_template('crear_producto.html')
# Rutas para consultas y reportes
@app.route('/consultar_info', methods=['GET', 'POST'])
def consultar_info():
    if request.method == 'POST':
        tipo_consulta = request.form['tipo_consulta']
        id_entidad = int(request.form['id_entidad'])
        if tipo_consulta == 'producto':
            info = gestion_inventario.consultar_info_producto(id_entidad)
        elif tipo_consulta == 'categoria':
            info = gestion_inventario.consultar_info_categoria(id_entidad)
        return render_template('consultar_info.html', info=info)
    return render_template('consultar_info.html')

@app.route("/inicio_sesion", methods=["GET", "POST"])
def inicio_sesion():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Conectar con la base de datos SQLite
        conn = sqlite3.connect('cliente.db')
        cursor = conn.cursor()

        # Consulta para obtener el usuario
        cursor.execute('SELECT * FROM Usuario WHERE usuario = ?', (username,))  # Cambié 'username' a 'usuario' para que coincida con tu tabla
        user = cursor.fetchone()
        conn.close()

        if user and user[2] == password:  # Asegúrate de que user[2] sea la columna de contraseña
            flash('Inicio de sesión exitoso', 'success')
            return redirect(url_for('index'))
        else:
            return redirect(url_for('error'))
    
    return render_template('inicio_sesion.html')

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
@app.route("/registrar_usuario", methods=["GET", "POST"])
def registrar_usuario():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Conectar con la base de datos SQLite
        conn = sqlite3.connect('cliente.db')
        cursor = conn.cursor()

        # Insertar nuevo usuario en la base de datos
        cursor.execute('INSERT INTO Usuario (usuario, contraseña) VALUES (?, ?)', (username, password))

        # Confirmar los cambios y cerrar la conexión
        conn.commit()
        conn.close()

        flash('Usuario registrado exitosamente', 'success')
        return redirect(url_for('login'))  # Redirigir al login después de registrar
    return render_template('registrar_usuario.html')  # Para el método GET
# Ejecuta la aplicación
if __name__ == '__main__':
    app.run(debug=True)