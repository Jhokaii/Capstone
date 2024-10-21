
    document.addEventListener('DOMContentLoaded', function () {
        // Seleccionamos todos los botones de decremento y los inputs
        const minusButtons = document.querySelectorAll('.minus');
        const plusButtons = document.querySelectorAll('.plus');

        // Para cada botón de decremento, añadimos el evento de clic
        minusButtons.forEach(button => {
            button.addEventListener('click', function () {
                const input = this.nextElementSibling; // El input que está después del botón
                let value = parseInt(input.value);
                if (value > 0) {
                    input.value = value - 1; // Reducimos el valor
                }
            });
        });

        // Para cada botón de incremento, añadimos el evento de clic
        plusButtons.forEach(button => {
            button.addEventListener('click', function () {
                const input = this.previousElementSibling; // El input que está antes del botón
                let value = parseInt(input.value);
                input.value = value + 1; // Aumentamos el valor
            });
        });
    });
