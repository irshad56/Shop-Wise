// Get cart items from localStorage
const cart = JSON.parse(localStorage.getItem('cart')) || [];
let selectedProducts = [];

// Initialize the product list
function initializeProductList() {
    const productList = document.getElementById('productList');
    productList.innerHTML = '';

    cart.forEach(item => {
        const productElement = document.createElement('div');
        productElement.className = 'product-item';
        productElement.innerHTML = `
            <h4>${item.name}</h4>
            <p>Price: $${item.price.toFixed(2)}</p>
            <p>Sustainability Score: ${item.sustainabilityScore}</p>
        `;

        productElement.addEventListener('click', () => {
            toggleProductSelection(item, productElement);
        });

        productList.appendChild(productElement);
    });
}

// Toggle product selection
function toggleProductSelection(product, element) {
    const index = selectedProducts.findIndex(p => p.id === product.id);
    
    if (index === -1) {
        if (selectedProducts.length < 2) {
            selectedProducts.push(product);
            element.classList.add('selected');
        } else {
            alert('You can only compare two products at a time');
            return;
        }
    } else {
        selectedProducts.splice(index, 1);
        element.classList.remove('selected');
    }

    updateComparisonTable();
}

// Update the comparison table
function updateComparisonTable() {
    // Reset table
    document.getElementById('name1').textContent = '-';
    document.getElementById('name2').textContent = '-';
    document.getElementById('price1').textContent = '-';
    document.getElementById('price2').textContent = '-';
    document.getElementById('score1').textContent = '-';
    document.getElementById('score2').textContent = '-';
    document.getElementById('desc1').textContent = '-';
    document.getElementById('desc2').textContent = '-';

    // Update with selected products
    selectedProducts.forEach((product, index) => {
        const suffix = index + 1;
        document.getElementById(`name${suffix}`).textContent = product.name;
        document.getElementById(`price${suffix}`).textContent = `$${product.price.toFixed(2)}`;
        document.getElementById(`score${suffix}`).textContent = product.sustainabilityScore;
        document.getElementById(`desc${suffix}`).textContent = product.description;
    });

    // Highlight differences
    if (selectedProducts.length === 2) {
        highlightDifferences();
    }
}

// Highlight differences between products
function highlightDifferences() {
    const features = ['price', 'score'];
    
    features.forEach(feature => {
        const value1 = selectedProducts[0][feature];
        const value2 = selectedProducts[1][feature];
        
        if (value1 !== value2) {
            const cell1 = document.getElementById(`${feature}1`);
            const cell2 = document.getElementById(`${feature}2`);
            
            if (feature === 'price') {
                const price1 = parseFloat(value1);
                const price2 = parseFloat(value2);
                
                if (price1 < price2) {
                    cell1.classList.add('highlight');
                } else {
                    cell2.classList.add('highlight');
                }
            } else if (feature === 'score') {
                const score1 = parseInt(value1);
                const score2 = parseInt(value2);
                
                if (score1 > score2) {
                    cell1.classList.add('highlight');
                } else {
                    cell2.classList.add('highlight');
                }
            }
        }
    });
}

// Initialize the page
document.addEventListener('DOMContentLoaded', () => {
    initializeProductList();
}); 