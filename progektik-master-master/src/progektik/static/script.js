console.log("Скрипт загружен!");

$(document).ready(function() {
    $('#registration-form').on('submit', function(e) {
        e.preventDefault();
        
        let name = $('#fullname').val();
        let email = $('#email').val();
        let password = $('#password').val();
        let confirmPassword = $('#password_confirm').val();
        let errorDiv = $('#error-message');
        
        errorDiv.text("");

        if (!name || !email || !password) {
            errorDiv.text("Заполните все поля!");
            return;
        }

        if (password !== confirmPassword) {
            errorDiv.text("Пароли не совпадают!");
            return;
        }

        errorDiv.text("Отправка данных...");

        $.ajax({
            url: '/api/user_register',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                name: name,
                email: email,
                password: password
            }),
            success: function(data) {
                if (data.ok) {
                    window.location.href = '/profile'; 
                }
            },
            error: function(xhr) {
                if (xhr.responseJSON && xhr.responseJSON.error) {
                    errorDiv.text(xhr.responseJSON.error); 
                } else {
                    errorDiv.text("Ошибка сервера.");
                }
            }
        });
    });

    $('#login-form').on('submit', function(e) {
        e.preventDefault();
        
        $.ajax({
            url: '/api/login',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                email: $('#username').val(),
                password: $('#password').val()
            }),
            success: function(response) {
                window.location.href = '/profile'; 
            },
            error: function(xhr) {
                alert("Неверный логин или пароль");
            }
        });
    });
});