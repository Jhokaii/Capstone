document.addEventListener('DOMContentLoaded', () => {
    const welcomePage = document.getElementById('welcomePage');
    const loginPage = document.getElementById('loginPage');
    const registerPage = document.getElementById('registerPage');
    const homeLink = document.getElementById('homeLink');
    const loginLink = document.getElementById('loginLink');
    const registerLink = document.getElementById('registerLink');
    const backButton = document.getElementById('backButton');
    const logoutButton = document.getElementById('logoutButton');

    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    const loginMessage = document.getElementById('loginMessage');
    const registerMessage = document.getElementById('registerMessage');
    const welcomeMessage = document.getElementById('welcomeMessage');

    function showPage(page) {
        welcomePage.style.display = 'none';
        loginPage.style.display = 'none';
        registerPage.style.display = 'none';
        page.style.display = 'block';
    }

    function checkLoggedIn() {
        const user = JSON.parse(localStorage.getItem('user'));
        if (user) {
            welcomeMessage.textContent = `Bienvenido, ${user.username}!`;
            logoutButton.style.display = 'block';
            loginLink.style.display = 'none';
            registerLink.style.display = 'none';
            showPage(welcomePage);
        } else {
            logoutButton.style.display = 'none';
            loginLink.style.display = 'inline';
            registerLink.style.display = 'inline';
        }
    }

    homeLink.addEventListener('click', (e) => {
        e.preventDefault();
        showPage(welcomePage);
    });

    loginLink.addEventListener('click', (e) => {
        e.preventDefault();
        showPage(loginPage);
    });

    registerLink.addEventListener('click', (e) => {
        e.preventDefault();
        showPage(registerPage);
    });

    backButton.addEventListener('click', () => {
        showPage(welcomePage);
    });

    logoutButton.addEventListener('click', () => {
        localStorage.removeItem('user');
        checkLoggedIn();
        showPage(welcomePage);
    });

    loginForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const username = document.getElementById('loginUsername').value;
        const password = document.getElementById('loginPassword').value;
        
        // Simulación de login (en una app real, esto se haría en el servidor)
        const users = JSON.parse(localStorage.getItem('users')) || [];
        const user = users.find(u => u.username === username && u.password === password);
        
        if (user) {
            localStorage.setItem('user', JSON.stringify(user));
            loginMessage.textContent = '¡Inicio de sesión exitoso!';
            loginMessage.style.color = 'green';
            setTimeout(() => {
                checkLoggedIn();
                showPage(welcomePage);
            }, 2000);
        } else {
            loginMessage.textContent = 'Usuario o contraseña incorrectos.';
            loginMessage.style.color = 'red';
        }
    });

    registerForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const username = document.getElementById('registerUsername').value;
        const email = document.getElementById('registerEmail').value;
        const password = document.getElementById('registerPassword').value;
        
        const users = JSON.parse(localStorage.getItem('users')) || [];
        
        if (users.some(u => u.username === username)) {
            registerMessage.textContent = 'Este nombre de usuario ya está en uso.';
            registerMessage.style.color = 'red';
        } else {
            users.push({ username, email, password });
            localStorage.setItem('users', JSON.stringify(users));
            registerMessage.textContent = '¡Registro exitoso! Puedes iniciar sesión ahora.';
            registerMessage.style.color = 'green';
            setTimeout(() => showPage(loginPage), 2000);
        }
    });

    // Verificar si hay un usuario logueado al cargar la página
    checkLoggedIn();
});