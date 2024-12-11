document.addEventListener('DOMContentLoaded', function () {
    // Seleccionamos todos los botones de decremento y los inputs
    const minusButtons = document.querySelectorAll('.minus');
    const plusButtons = document.querySelectorAll('.plus');

    // Para cada botón de decremento, añadimos el evento de clic
    minusButtons.forEach(button => {
        button.addEventListener('click', function () {
            const input = this.nextElementSibling; // El input que está después del botón
            let value = parseInt(input.value);
            if (value > 1) { // Evitamos que el valor sea menor que 1
                input.value = value - 1;
            }
        });
    });

    // Para cada botón de incremento, añadimos el evento de clic
    plusButtons.forEach(button => {
        button.addEventListener('click', function () {
            const input = this.previousElementSibling; // El input que está antes del botón
            let value = parseInt(input.value);
            input.value = value + 1;
        });
    });
});
function agregarAlCarrito(idProducto) {
    fetch(`/agregar_al_carrito/${idProducto}`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Producto agregado al carrito');
            // Aquí puedes actualizar el carrito visualmente
        } else {
            alert('Error al agregar el producto: ' + data.error);
        }
    })
    .catch(error => console.error('Error:', error));
}
// cart.js

function actualizarCantidad(idDetalle, cantidad) {
    fetch(`/actualizar_cantidad/${idDetalle}/${cantidad}`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload(); // Recargar la página para ver los cambios
        } else {
            alert('Error al actualizar la cantidad');
        }
    });
}

function eliminarDelCarrito(idDetalle) {
    fetch(`/eliminar_del_carrito/${idDetalle}`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload(); // Recargar la página para ver los cambios
        } else {
            alert('Error al eliminar el producto');
        }
    });
}

function confirmarCompra() {
    // Lógica para confirmar la compra
    fetch('/confirmar_compra', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Compra confirmada');
            // Redireccionar o limpiar el carrito
        } else {
            alert('Error al confirmar la compra');
        }
    });
}
document.getElementById("confirmarPedidoBtn").addEventListener("click", function() {
    const carrito = getCarrito();  // Asumimos que esta función obtiene el carrito en formato de objeto
    const metodoPago = document.getElementById("metodoPago").value; // Supongo que tienes un input para el método de pago

    fetch("/confirmar_pedido", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            carrito: carrito,
            metodo_pago: metodoPago,
        }),
    })
    .then(response => response.json())
    .then(data => {
        console.log(data.message);  // Muestra el mensaje recibido del servidor
    })
    .catch(error => {
        console.error("Error al enviar el pedido:", error);
    });
});
