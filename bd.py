import sqlite3
import os

def conectar_bd():
    # Conecta a la base de datos 'cliente.db' en la ruta actual del archivo
    db_path = os.path.join(os.path.dirname(__file__), 'cliente.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Permite acceder a las columnas por nombre
    return conn

def crear_usuario(usuario, contrasena):
    conn = conectar_bd()
    cursor = conn.cursor()
    try:
        # Inserta en las columnas `usuario` y `contrasena` en la tabla Usuario
        cursor.execute("INSERT INTO Usuario (usuario, contrasena) VALUES (?, ?)", (usuario, contrasena))
        conn.commit()  # Asegura que los cambios se guarden en la base de datos
        print("Usuario creado exitosamente.")
    except sqlite3.Error as e:
        print(f"Error al crear el usuario: {e}")
    finally:
        conn.close()
# Función para registrar un producto en la base de datos
def registrar_producto(nombre, precio, stock, id_categoria):
    conn = sqlite3.connect('cliente.db')
    cursor = conn.cursor()

    cursor.execute('''INSERT INTO Producto (nombre_producto, precio, stock, id_categoria)
                      VALUES (?, ?, ?, ?, ?)''', (nombre_producto, precio, stock, id_categoria))

    conn.commit()
    conn.close()
#FUNCIONES CORRESPONDIENTES A RELACIONES ENTRE ENTIDADES

#CONSULTAS Y REPORTES:
