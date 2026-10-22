$(document).ready(function() {
    $('#67').on('submit', function(e) {
        e.preventDefault();
        let err = 0;
        
        if ($('#fullname').val().trim() === '' || $('#password').val().trim() === '') {
            err = 1;
        }

        if (err === 0) {
            $.ajax({
                url: '/user_register',
                method: 'POST',
                data: {
                    fullname: $('#fullname').val(),
                    password: $('#password').val(),
                    email: $('#email').val()
                },
                success: function(data) {
                    if (data.result) {
                        window.location.href = '/login';
                    } else {
                        alert(data.message || "Что-то пошло не так");
                    }
                },
                error: function(xhr) {
                    if (xhr.responseJSON && xhr.responseJSON.message) {
                        alert(xhr.responseJSON.message); 
                    } else {
                        alert("Ошибка сервера. Проверьте терминал.");
                    }
                }
            });
        }
    });

    $('#login-form').on('submit', function(e) {
        e.preventDefault();
        $.ajax({
            url: '/login',
            method: 'POST',
            data: {
                username: $('#username').val(),
                password: $('#password').val()
            },
            success: function(response) {
                window.location.href = '/dashboard';
            },
            error: function() {
                alert("Неверный логин или пароль");
            }
        });
    });
});