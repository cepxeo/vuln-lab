// Password reset page: send the new password with the link's e-mail and token.
(function () {
  var form = document.getElementById('reset-form');
  if (!form) { return; }
  form.addEventListener('submit', function (event) {
    event.preventDefault();
    fetch('/api/v1/account/reset/confirm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: form.elements.email.value,
        token: form.elements.token.value,
        password: form.elements.password.value
      })
    }).then(function (response) { return response.json(); }).then(function (data) {
      document.getElementById('reset-result').textContent =
        data.ok ? 'Password changed. You can sign in now.' : (data.error || 'Something went wrong.');
    });
  });
})();
