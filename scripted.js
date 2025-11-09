// Check if we're on the signup page
if (document.getElementById("signupForm")) {
  document.getElementById("signupForm").addEventListener("submit", async function (e) {
    e.preventDefault();

    const username = document.getElementById("username").value.trim();
    const email = document.getElementById("email").value.trim();
    const phone = document.getElementById("phone").value.trim();
    const password = document.getElementById("password").value;
    const confirm = document.getElementById("confirm").value;
    const messageElement = document.getElementById("message");

    // Validate phone number
    if (!/^\d{10}$/.test(phone)) {
      messageElement.textContent = "Phone number must be exactly 10 digits.";
      messageElement.style.color = "red";
      return;
    }

    // Validate password match
    if (password !== confirm) {
      messageElement.textContent = "Passwords do not match.";
      messageElement.style.color = "red";
      return;
    }

    try {
      const response = await fetch('http://127.0.0.1:5000/api/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: username,
          email: email,
          password: password
        })
      });

      const data = await response.json();

      if (response.ok) {
        messageElement.textContent = "Registration successful! Redirecting to login...";
        messageElement.style.color = "green";
        setTimeout(() => {
          window.location.href = "login.html";
        }, 2000);
      } else {
        messageElement.textContent = data.error || "Registration failed. Please try again.";
        messageElement.style.color = "red";
      }
    } catch (error) {
      messageElement.textContent = "An error occurred. Please try again later.";
      messageElement.style.color = "red";
      console.error('Error:', error);
    }
  });
}

// Check if we're on the login page
if (document.getElementById("loginForm")) {
  document.getElementById("loginForm").addEventListener("submit", async function (e) {
    e.preventDefault();

    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;
    const messageElement = document.getElementById("message");

    if (!email || !password) {
      messageElement.textContent = "Please enter both email and password.";
      messageElement.style.color = "red";
      return;
    }

    try {
      const response = await fetch('http://127.0.0.1:5000/api/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: email,
          password: password
        })
      });

      const data = await response.json();

      if (response.ok) {
        // Store the token
        localStorage.setItem('token', data.token);
        messageElement.textContent = "Login successful! Redirecting to home...";
        messageElement.style.color = "green";
        setTimeout(() => {
          window.location.href = "home.html";
        }, 2000);
      } else {
        messageElement.textContent = data.error || "Login failed. Please try again.";
        messageElement.style.color = "red";
      }
    } catch (error) {
      messageElement.textContent = "An error occurred. Please try again later.";
      messageElement.style.color = "red";
      console.error('Error:', error);
    }
  });
}
