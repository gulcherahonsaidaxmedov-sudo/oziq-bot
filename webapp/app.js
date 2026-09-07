const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
}

let products = [];
let cart = {}; // id -> {product, qty}
let activeCategory = "Hammasi";

const productsEl = document.getElementById("products");
const categoriesEl = document.getElementById("categories");
const cartListEl = document.getElementById("cart-list");
const cartBarEl = document.getElementById("cart-bar");
const cartSummaryEl = document.getElementById("cart-summary");
const checkoutBtn = document.getElementById("checkout-btn");

async function loadSettings() {
  try {
    const res = await fetch("/api/settings");
    const settings = await res.json();
    if (settings.background_url) {
      document.body.style.backgroundImage = `url(${settings.background_url})`;
      document.body.classList.add("has-bg");
    }
  } catch (e) {
    // fon rasmi ixtiyoriy, xato bo'lsa e'tiborsiz qoldiramiz
  }
}

async function loadProducts() {
  const res = await fetch("/api/products");
  products = await res.json();
  renderCategories();
  renderProducts();
}

function renderCategories() {
  const cats = ["Hammasi", ...new Set(products.map(p => p.category).filter(Boolean))];
  categoriesEl.innerHTML = "";
  cats.forEach(cat => {
    const btn = document.createElement("button");
    btn.textContent = cat;
    btn.className = "cat-btn" + (cat === activeCategory ? " active" : "");
    btn.onclick = () => {
      activeCategory = cat;
      renderCategories();
      renderProducts();
    };
    categoriesEl.appendChild(btn);
  });
}

function renderProducts() {
  const list = activeCategory === "Hammasi"
    ? products
    : products.filter(p => p.category === activeCategory);

  productsEl.innerHTML = "";
  list.forEach(p => {
    const qty = cart[p.id]?.qty || 0;
    const card = document.createElement("div");
    card.className = "product-card";
    const imgHtml = p.image_url
      ? `<img class="product-img" src="${p.image_url}" alt="${p.name}">`
      : `<div class="product-img product-img-placeholder">🛒</div>`;
    card.innerHTML = `
      ${imgHtml}
      <div class="product-name">${p.name}</div>
      <div class="product-desc">${p.description || ""}</div>
      <div class="product-price">${p.price.toLocaleString()} so'm</div>
      <div class="product-controls">
        <button class="qty-btn minus">−</button>
        <span class="qty-value">${qty}</span>
        <button class="qty-btn plus">+</button>
      </div>
    `;
    card.querySelector(".plus").onclick = () => changeQty(p, 1);
    card.querySelector(".minus").onclick = () => changeQty(p, -1);
    productsEl.appendChild(card);
  });
}

function changeQty(product, delta) {
  const current = cart[product.id]?.qty || 0;
  const next = Math.max(0, current + delta);
  if (next === 0) {
    delete cart[product.id];
  } else {
    cart[product.id] = { product, qty: next };
  }
  renderProducts();
  renderCartBar();
  renderCartList();
}

function renderCartList() {
  const items = Object.values(cart);
  if (items.length === 0) {
    cartListEl.classList.add("hidden");
    cartListEl.innerHTML = "";
    return;
  }
  cartListEl.classList.remove("hidden");
  cartListEl.innerHTML = items.map(i => `
    <div class="cart-item" data-id="${i.product.id}">
      <span class="cart-item-name">${i.product.name}</span>
      <div class="cart-item-controls">
        <button class="qty-btn minus">−</button>
        <span class="qty-value">${i.qty}</span>
        <button class="qty-btn plus">+</button>
      </div>
      <span class="cart-item-subtotal">${(i.product.price * i.qty).toLocaleString()} so'm</span>
    </div>
  `).join("");

  items.forEach(i => {
    const row = cartListEl.querySelector(`.cart-item[data-id="${i.product.id}"]`);
    row.querySelector(".plus").onclick = () => changeQty(i.product, 1);
    row.querySelector(".minus").onclick = () => changeQty(i.product, -1);
  });
}

function renderCartBar() {
  const items = Object.values(cart);
  if (items.length === 0) {
    cartBarEl.classList.add("hidden");
    return;
  }
  const total = items.reduce((sum, i) => sum + i.product.price * i.qty, 0);
  const count = items.reduce((sum, i) => sum + i.qty, 0);
  cartSummaryEl.textContent = `${count} ta mahsulot — ${total.toLocaleString()} so'm`;
  cartBarEl.classList.remove("hidden");
}

checkoutBtn.onclick = async () => {
  const items = Object.values(cart).map(i => ({
    id: i.product.id,
    name: i.product.name,
    price: i.product.price,
    qty: i.qty,
  }));
  if (items.length === 0) return;

  const user = tg?.initDataUnsafe?.user;
  if (!user?.id) {
    // MUHIM TUZATISH: agar mini-ilova Telegram tashqarisida ochilgan bo'lsa,
    // avvalgi kodda buyurtma "sababsiz" qabul qilinmas edi. Endi aniq xabar chiqadi.
    const msg = "Iltimos, do'konni Telegram bot ichidagi \"🛒 Do'kon\" tugmasi orqali oching.";
    if (tg) tg.showAlert(msg); else alert(msg);
    return;
  }

  const payload = {
    user_id: user.id,
    username: user.username || user.first_name || "",
    items,
  };

  checkoutBtn.disabled = true;
  checkoutBtn.textContent = "Yuborilmoqda...";

  try {
    const res = await fetch("/api/order", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (res.ok && data.order_id) {
      cart = {};
      renderProducts();
      renderCartBar();
      renderCartList();
      const okMsg = `✅ Buyurtmangiz qabul qilindi! Navbat raqamingiz: №${data.daily_number}`;
      if (tg) tg.showAlert(okMsg, () => tg.close());
      else alert(okMsg);
    } else {
      throw new Error(data.error || "Noma'lum xatolik");
    }
  } catch (e) {
    const errMsg = `Xatolik: ${e.message}`;
    if (tg) tg.showAlert(errMsg);
    else alert(errMsg);
  } finally {
    checkoutBtn.disabled = false;
    checkoutBtn.textContent = "Buyurtma berish";
  }
};

loadSettings();
loadProducts();
      
