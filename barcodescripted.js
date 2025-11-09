let selectedDeviceId;
const codeReader = new ZXing.BrowserMultiFormatReader();

// DOM Elements
const barcodeVideo = document.getElementById('barcode-video');
const qrVideo = document.getElementById('qr-video');
const startBarcodeButton = document.getElementById('start-barcode-scan');
const stopBarcodeButton = document.getElementById('stop-barcode-scan');
const startQRButton = document.getElementById('start-qr-scan');
const stopQRButton = document.getElementById('stop-qr-scan');
const barcodeResult = document.getElementById('barcode-result');
const qrResult = document.getElementById('qr-result');
const tabButtons = document.querySelectorAll('.tab-btn');
const scannerSections = document.querySelectorAll('.scanner-section');

// Get available video devices
codeReader.listVideoInputDevices()
  .then(videoInputDevices => {
    if (videoInputDevices.length > 0) {
      selectedDeviceId = videoInputDevices[0].deviceId;
    }
  })
  .catch(err => {
    console.error(err);
  });

// Tab switching functionality
tabButtons.forEach(button => {
  button.addEventListener('click', () => {
    const tabName = button.dataset.tab;
    
    // Update active tab button
    tabButtons.forEach(btn => btn.classList.remove('active'));
    button.classList.add('active');
    
    // Show corresponding section
    scannerSections.forEach(section => {
      section.classList.remove('active');
      if (section.id === `${tabName}-section`) {
        section.classList.add('active');
      }
    });

    // Stop any active scanning when switching tabs
    if (tabName === 'barcode') {
      stopQRScanning();
    } else {
      stopBarcodeScanning();
    }
  });
});

// Barcode scanning
startBarcodeButton.addEventListener('click', () => {
  startBarcodeButton.style.display = 'none';
  stopBarcodeButton.style.display = 'flex';
  barcodeResult.classList.add('hidden');
  barcodeVideo.style.display = 'block';

  codeReader.decodeFromVideoDevice(selectedDeviceId, 'barcode-video', (result, err) => {
    if (result) {
      console.log(result.text);
      displayBarcodeResult(result.text);
    }
    if (err && !(err instanceof ZXing.NotFoundException)) {
      console.error(err);
    }
  });
});

stopBarcodeButton.addEventListener('click', () => {
  stopBarcodeScanning();
});

// QR code scanning
startQRButton.addEventListener('click', () => {
  startQRButton.style.display = 'none';
  stopQRButton.style.display = 'flex';
  qrResult.classList.add('hidden');
  qrVideo.style.display = 'block';

  codeReader.decodeFromVideoDevice(selectedDeviceId, 'qr-video', (result, err) => {
    if (result) {
      console.log(result.text);
      displayQRResult(result.text);
    }
    if (err && !(err instanceof ZXing.NotFoundException)) {
      console.error(err);
    }
  });
});

stopQRButton.addEventListener('click', () => {
  stopQRScanning();
});

// Stop barcode scanning
function stopBarcodeScanning() {
  codeReader.reset();
  startBarcodeButton.style.display = 'flex';
  stopBarcodeButton.style.display = 'none';
  barcodeVideo.style.display = 'none';
}

// Stop QR scanning
function stopQRScanning() {
  codeReader.reset();
  startQRButton.style.display = 'flex';
  stopQRButton.style.display = 'none';
  qrVideo.style.display = 'none';
}

// Mock product database
const productDatabase = {
  '123456789': {
    id: '123456789',
    name: 'Eco-Friendly Shampoo',
    price: 12.99,
    sustainabilityScore: '8/10',
    description: 'Natural ingredients, plastic-free packaging'
  },
  '987654321': {
    id: '987654321',
    name: 'Sustainable Toothbrush',
    price: 3.99,
    sustainabilityScore: '9/10',
    description: 'Bamboo handle, biodegradable bristles'
  },
  '456789123': {
    id: '456789123',
    name: 'Organic Cotton T-shirt',
    price: 24.99,
    sustainabilityScore: '7/10',
    description: '100% organic cotton, fair trade certified'
  }
};

// Display barcode scan result
function displayBarcodeResult(barcode) {
  const productName = document.getElementById('barcode-product-name');
  const productDesc = document.getElementById('barcode-product-desc');
  const sustainabilityScore = document.getElementById('barcode-sustainability-score');

  // Look up product in database
  const product = productDatabase[barcode];
  
  if (product) {
    productName.textContent = product.name;
    productDesc.textContent = product.description;
    sustainabilityScore.textContent = `Sustainability Score: ${product.sustainabilityScore}`;
    
    // Add to cart
    addToCart(product);
    
    // Show success message
    barcodeResult.classList.remove('hidden');
    barcodeResult.innerHTML += `
      <div class="success-message">
        <p>Product added to cart!</p>
        <button onclick="window.location.href='cart.html'">View Cart</button>
      </div>
    `;
  } else {
    productName.textContent = 'Product not found';
    productDesc.textContent = 'This product is not in our database.';
    sustainabilityScore.textContent = 'Sustainability Score: N/A';
  }
}

// Display QR code scan result
function displayQRResult(qrData) {
  const productName = document.getElementById('qr-product-name');
  const productDesc = document.getElementById('qr-product-desc');
  const sustainabilityScore = document.getElementById('qr-sustainability-score');

  // Look up product in database
  const product = productDatabase[qrData];
  
  if (product) {
    productName.textContent = product.name;
    productDesc.textContent = product.description;
    sustainabilityScore.textContent = `Sustainability Score: ${product.sustainabilityScore}`;
    
    // Add to cart
    addToCart(product);
    
    // Show success message
    qrResult.classList.remove('hidden');
    qrResult.innerHTML += `
      <div class="success-message">
        <p>Product added to cart!</p>
        <button onclick="window.location.href='cart.html'">View Cart</button>
      </div>
    `;
  } else {
    productName.textContent = 'Product not found';
    productDesc.textContent = 'This product is not in our database.';
    sustainabilityScore.textContent = 'Sustainability Score: N/A';
  }
}
