import sqlite3
import os

# Función para crear la base de datos y las tablas
def crear_bd():
    conn = sqlite3.connect('cliente.db')
    cursor = conn.cursor()
    
    # Crear tabla Producto
    cursor.execute('''CREATE TABLE IF NOT EXISTS Producto (
                        id_producto INTEGER PRIMARY KEY,
                        nombre_producto TEXT,
                        precio REAL,
                        stock INTEGER,
                        id_categoria INTEGER,
                        FOREIGN KEY (id_categoria) REFERENCES Categoria(id_categoria)
                    )''') 
    # Crear tabla Categoria
    cursor.execute('''CREATE TABLE IF NOT EXISTS Categoria (
                        id_categoria INTEGER PRIMARY KEY,
                        nombre TEXT,
                        descripcion TEXT
                    )''')
    # Crear tabla Categoria
    cursor.execute('''CREATE TABLE IF NOT EXISTS Usuario (
                        id_usuario INTEGER PRIMARY KEY,
                        usuario TEXT,
                        contraseña TEXT
                    )''')
    # Crear tabla Usuario
    cursor.execute('''CREATE TABLE IF NOT EXISTS Usuario (
                        id_usuario INTEGER PRIMARY KEY,
                        usuario TEXT,
                        contraseña TEXT
                    )''')

    conn.commit()
    conn.close()
# Función para registrar un producto en la base de datos
def registrar_producto(nombre, precio, stock, id_categoria):
    conn = sqlite3.connect('cliente.db')
    cursor = conn.cursor()

    cursor.execute('''INSERT INTO Producto (nombre_producto, precio, stock, id_categoria)
                      VALUES (?, ?, ?, ?, ?)''', (nombre_producto, precio, stock, id_categoria))

    conn.commit()
    conn.close()
# Función para registrar una categoría en la base de datos
def registrar_categoria(nombre, descripcion):
    conn = sqlite3.connect('cliente.db')
    cursor = conn.cursor()

    cursor.execute('''INSERT INTO Categoria (nombre, descripcion)
                      VALUES (?, ?)''', (nombre, descripcion))

    conn.commit()
    conn.close()
#FUNCIONES CORRESPONDIENTES A RELACIONES ENTRE ENTIDADES

def agregar_producto_a_categoria(id_producto, id_categoria):
    conn = sqlite3.connect('gestion_inventario.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''UPDATE Producto
                          SET id_categoria = ?
                          WHERE id_producto = ?''', (id_categoria, id_producto))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print("Error:", e)
        conn.close()
        return False
# Función para imprimir los datos de una tabla
def imprimir_tabla(tabla):
    conn = sqlite3.connect('cliente.db')
    cursor = conn.cursor()

    cursor.execute(f"SELECT * FROM {tabla};")
    rows = cursor.fetchall()

    print(f"\nDatos de la tabla {tabla}:")
    for row in rows:
        print(row)

    conn.close()
#CONSULTAS Y REPORTES:

def consultar_info_producto(id_producto):
    conexion = sqlite3.connect('cliente.db')
    conexion.row_factory = sqlite3.Row
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM Producto WHERE id_producto = ?", (id_producto,))
    producto = cursor.fetchone()
    conexion.close()
    if producto:
        return dict(producto)
    return None
# Crear la base de datos y las tablas
crear_bd()