let products = [];
let cart = {}; // { productId: { product, quantity } }

async function loadProducts(query = '') {
  const url = query ? `/api/products?q=${encodeURIComponent(query)}` : '/api/products';
  const res = await fetch(url);
  products = await res.json();
  renderProductGrid();
}

function renderProductGrid() {
  const grid = document.getElementById('billing-products');
  grid.innerHTML = products.map(p => `
    <div class="product-tile ${p.stock_qty <= 0 ? 'out-of-stock' : ''}" data-id="${p.id}">
      <p class="name">${p.name}</p>
      <p class="meta">${p.stock_qty} ${p.unit_name} left</p>
      <p class="price">₹${p.price.toFixed(2)} / ${p.unit_name}</p>
    </div>
  `).join('');

  grid.querySelectorAll('.product-tile').forEach(tile => {
    tile.addEventListener('click', () => {
      if (tile.classList.contains('out-of-stock')) return;
      const id = parseInt(tile.dataset.id, 10);
      const product = products.find(p => p.id === id);
      addToCart(product);
    });
  });
}

function addToCart(product) {
  if (cart[product.id]) {
    cart[product.id].quantity += 1;
  } else {
    cart[product.id] = { product, quantity: 1 };
  }
  renderCart();
}

function updateQuantity(id, quantity) {
  if (quantity <= 0) {
    delete cart[id];
  } else {
    cart[id].quantity = quantity;
  }
  renderCart();
}

function renderCart() {
  const tbody = document.getElementById('cart-tbody');
  const items = Object.values(cart);

  tbody.innerHTML = items.map(({ product, quantity }) => `
    <tr data-id="${product.id}">
      <td>${product.name}</td>
      <td><input type="number" class="qty-input" min="0" step="0.01" value="${quantity}" /></td>
      <td>₹${(product.price * quantity).toFixed(2)}</td>
      <td><button class="btn btn-sm btn-danger remove-btn">✕</button></td>
    </tr>
  `).join('');

  const grandTotal = items.reduce((sum, { product, quantity }) => sum + product.price * quantity, 0);
  document.getElementById('cart-grand-total').textContent = `₹${grandTotal.toFixed(2)}`;

  tbody.querySelectorAll('.qty-input').forEach(input => {
    input.addEventListener('change', (e) => {
      const id = parseInt(e.target.closest('tr').dataset.id, 10);
      updateQuantity(id, parseFloat(e.target.value) || 0);
    });
  });

  tbody.querySelectorAll('.remove-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const id = parseInt(e.target.closest('tr').dataset.id, 10);
      delete cart[id];
      renderCart();
    });
  });
}

document.getElementById('checkout-btn').addEventListener('click', async () => {
  const errorEl = document.getElementById('checkout-error');
  errorEl.textContent = '';

  const items = Object.values(cart).map(({ product, quantity }) => ({
    product_id: product.id,
    quantity,
  }));

  if (items.length === 0) {
    errorEl.textContent = 'Add at least one item to the bill.';
    return;
  }

  const res = await fetch('/api/orders', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ items }),
  });

  const data = await res.json();

  if (res.ok) {
    showReceipt(data);
    cart = {};
    renderCart();
    loadProducts(document.getElementById('billing-search').value);
  } else {
    errorEl.textContent = data.error || 'Checkout failed.';
  }
});

function showReceipt(order) {
  document.getElementById('receipt-order-number').textContent = order.order_number;
  document.getElementById('receipt-items').innerHTML = order.items.map(i => `
    <div style="display:flex; justify-content:space-between; padding:6px 0; border-bottom:1px solid var(--border); font-size:14px;">
      <span>${i.product_name} × ${i.quantity}</span>
      <span>₹${i.line_total.toFixed(2)}</span>
    </div>
  `).join('');
  document.getElementById('receipt-total').textContent = `₹${order.total_amount.toFixed(2)}`;
  document.getElementById('receipt-modal').classList.remove('hidden');
}

document.getElementById('receipt-close').addEventListener('click', () => {
  document.getElementById('receipt-modal').classList.add('hidden');
});

let searchDebounce;
document.getElementById('billing-search').addEventListener('input', (e) => {
  clearTimeout(searchDebounce);
  searchDebounce = setTimeout(() => loadProducts(e.target.value), 250);
});

loadProducts();
