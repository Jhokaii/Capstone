import sqlite3
import os

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
