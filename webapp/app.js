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
const cartBarEl = document.getElementById("cart-bar");
const cartSummaryEl = document.getElementById("cart-summary");
const checkoutBtn = document.getElementById("checkout-btn");

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
    card.innerHTML = `
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
  const payload = {
    user_id: user?.id,
    username: user?.username || user?.first_name || "",
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
    if (data.order_id) {
      cart = {};
      renderProducts();
      renderCartBar();
      if (tg) {
        tg.showAlert(`✅ Buyurtmangiz qabul qilindi! №${data.order_id}`, () => tg.close());
      } else {
        alert(`Buyurtma qabul qilindi! №${data.order_id}`);
      }
    } else {
      throw new Error(data.error || "Xatolik");
    }
  } catch (e) {
    if (tg) tg.showAlert("Xatolik yuz berdi, qayta urinib ko'ring.");
    else alert("Xatolik yuz berdi.");
  } finally {
    checkoutBtn.disabled = false;
    checkoutBtn.textContent = "Buyurtma berish";
  }
};

loadProducts();
