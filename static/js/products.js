let allProducts = [];
let allUnits = [];

async function fetchUnits() {
  const res = await fetch('/api/units');
  allUnits = await res.json();
  const select = document.getElementById('p-unit');
  select.innerHTML = allUnits.map(u => `<option value="${u.id}">${u.name}</option>`).join('');
}

async function fetchProducts(query = '') {
  const url = query ? `/api/products?q=${encodeURIComponent(query)}` : '/api/products';
  const res = await fetch(url);
  allProducts = await res.json();
  renderProducts();
}

function renderProducts() {
  const tbody = document.getElementById('products-tbody');
  tbody.innerHTML = allProducts.map(p => `
    <tr data-id="${p.id}">
      <td class="editable" data-field="name">${p.name}</td>
      <td class="editable" data-field="category">${p.category || ''}</td>
      <td>${p.unit_name}</td>
      <td class="editable" data-field="price">${p.price.toFixed(2)}</td>
      <td class="editable" data-field="stock_qty">${p.stock_qty}</td>
      <td><button class="btn btn-sm btn-danger delete-btn">Delete</button></td>
    </tr>
  `).join('');

  tbody.querySelectorAll('.delete-btn').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      const row = e.target.closest('tr');
      const id = row.dataset.id;
      if (!confirm('Delete this product?')) return;
      const res = await fetch(`/api/products/${id}`, { method: 'DELETE' });
      if (res.ok) {
        fetchProducts(document.getElementById('product-search').value);
      } else {
        alert('Could not delete product.');
      }
    });
  });

  // Inline edit: click a cell, edit the text, blur to save
  tbody.querySelectorAll('.editable').forEach(cell => {
    cell.addEventListener('click', () => {
      if (cell.querySelector('input')) return; // already editing
      const original = cell.textContent.trim();
      const field = cell.dataset.field;
      const isNumber = field === 'price' || field === 'stock_qty';
      cell.innerHTML = `<input type="${isNumber ? 'number' : 'text'}" step="0.01" value="${original}" />`;
      const input = cell.querySelector('input');
      input.focus();

      const save = async () => {
        const newValue = input.value;
        const row = cell.closest('tr');
        const id = row.dataset.id;
        const payload = { [field]: isNumber ? parseFloat(newValue) : newValue };
        const res = await fetch(`/api/products/${id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (res.ok) {
          fetchProducts(document.getElementById('product-search').value);
        } else {
          cell.textContent = original;
        }
      };

      input.addEventListener('blur', save);
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') input.blur();
        if (e.key === 'Escape') { cell.textContent = original; }
      });
    });
  });
}

document.getElementById('add-product-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const errorEl = document.getElementById('add-product-error');
  errorEl.textContent = '';

  const payload = {
    name: document.getElementById('p-name').value.trim(),
    category: document.getElementById('p-category').value.trim(),
    unit_id: parseInt(document.getElementById('p-unit').value, 10),
    price: parseFloat(document.getElementById('p-price').value),
    stock_qty: parseFloat(document.getElementById('p-stock').value),
  };

  const res = await fetch('/api/products', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (res.ok) {
    e.target.reset();
    fetchProducts();
  } else {
    const data = await res.json().catch(() => ({}));
    errorEl.textContent = data.error || 'Could not add product.';
  }
});

let searchDebounce;
document.getElementById('product-search').addEventListener('input', (e) => {
  clearTimeout(searchDebounce);
  searchDebounce = setTimeout(() => fetchProducts(e.target.value), 250);
});

(async function init() {
  await fetchUnits();
  await fetchProducts();
})();
