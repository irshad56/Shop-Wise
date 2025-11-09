// profile-dropdown.js
// Handles profile dropdown, edit profile navigation, and logout

document.addEventListener('DOMContentLoaded', function() {
    // Dropdown elements
    const profileIcon = document.getElementById('profileIcon');
    const profileDropdown = document.getElementById('profileDropdown');
    const settingsToggle = document.getElementById('settingsToggle');
    const settingsContent = document.getElementById('settingsContent');
    const editProfileLink = document.getElementById('editProfileLink');
    const logoutBtn = document.getElementById('logoutBtn');

    // Toggle profile dropdown
    if (profileIcon && profileDropdown) {
        profileIcon.addEventListener('click', function(e) {
            e.stopPropagation();
            profileDropdown.classList.toggle('active');
        });
    }

    // Close dropdown when clicking outside
    document.addEventListener('click', function(e) {
        if (profileDropdown && !profileDropdown.contains(e.target) && e.target !== profileIcon) {
            profileDropdown.classList.remove('active');
            if (settingsContent) settingsContent.classList.remove('active');
            if (settingsToggle) settingsToggle.classList.remove('active');
        }
    });

    // Toggle Account Settings submenu
    if (settingsToggle && settingsContent) {
        settingsToggle.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            settingsContent.classList.toggle('active');
            settingsToggle.classList.toggle('active');
        });
    }

    // Edit Profile navigation
    if (editProfileLink) {
        editProfileLink.addEventListener('click', function(e) {
            e.preventDefault();
            window.location.href = 'edit-profile.html';
        });
    }

    // Logout functionality
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async function(e) {
            e.preventDefault();
            const SERVER_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
                ? 'http://127.0.0.1:5000' 
                : 'http://' + window.location.hostname + ':5000';
            try {
                await fetch(`${SERVER_URL}/api/auth/logout`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('token')}`
                    }
                });
            } catch (error) {
                // Ignore error, just clear storage
            }
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            window.location.href = 'login.html';
        });
    }
}); 