const SERVER_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
  ? 'http://127.0.0.1:5000' 
  : 'http://' + window.location.hostname + ':5000';

let cart = [];

document.addEventListener('DOMContentLoaded', () => {
    checkAuthAndLoadCart();
});

function checkAuthAndLoadCart() {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = 'login.html';
        return;
    }
    loadCartFromBackend(token);
}

async function loadCartFromBackend(token) {
    try {
        const response = await fetch(`${SERVER_URL}/api/cart`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) throw new Error('Failed to fetch cart');

        const cartData = await response.json();
        cart = cartData.map(item => {
            const product = item.product;
            // Debug log to verify product status
            console.log('Product:', product.name, 'Status:', product.status);
            return {
                ...product,
                cartItemId: item.id,
                quantity: item.quantity,
                isEcoFriendly: product.status === 'ECO' // Direct comparison with exact case
            };
        });

        updateCartDisplay();
    } catch (error) {
        console.error('Error loading cart:', error);
        document.getElementById('cartItems').innerHTML = `<p class="empty-cart">Unable to load cart</p>`;
    }
}

async function updateQuantity(cartItemId, newQuantity) {
    const token = localStorage.getItem('token');
    if (!token || newQuantity < 1) return;

    try {
        await fetch(`${SERVER_URL}/api/cart/${cartItemId}`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ quantity: newQuantity })
        });
        await loadCartFromBackend(token);
    } catch (error) {
        console.error('Error updating quantity:', error);
    }
}

async function removeFromCart(productId) {
    const token = localStorage.getItem('token');
    if (!token) return;

    try {
        const cartItem = cart.find(p => p.id === productId);
        if (!cartItem) return;

        const response = await fetch(`${SERVER_URL}/api/cart/${cartItem.cartItemId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) await loadCartFromBackend(token);
    } catch (error) {
        console.error('Error removing item:', error);
    }
}


function updateCartDisplay() {
    const cartItemsDiv = document.getElementById('cartItems');
    const totalPriceDiv = document.getElementById('totalPrice');

    if (cart.length === 0) {
        cartItemsDiv.innerHTML = '<p class="empty-cart">Your cart is empty</p>';
        totalPriceDiv.innerHTML = '<p>Total: $0.00</p>';
        return;
    }

    let total = 0;

    const itemHtml = cart.map(item => {
        total += item.price * item.quantity;

        return `
            <div class="cart-item">
                <div class="item-info">
                    <div class="item-name">${item.name}</div>
                    <div class="item-details">
                        <p class="item-price">$${item.price.toFixed(2)}</p>
                    </div>
                </div>
                <button class="remove-btn" onclick="removeFromCart(${item.id})">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;
    }).join('');

    cartItemsDiv.innerHTML = itemHtml;
    totalPriceDiv.innerHTML = `<p>Total: $${total.toFixed(2)}</p>`;
}
