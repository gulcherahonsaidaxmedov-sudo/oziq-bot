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
const searchInput = document.getElementById("search-input");
const searchBtn = document.getElementById("search-btn");
const searchResultEl = document.getElementById("search-result");
const promoEl = document.getElementById("promo");
const promoTrackEl = document.getElementById("promo-track");
const promoDotsEl = document.getElementById("promo-dots");

// ---------- Tema: Telegramning light/dark rejimiga moslashish ----------

function applyTheme() {
  const scheme =
    tg?.colorScheme ||
    (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  document.body.classList.toggle("dark", scheme === "dark");
}

applyTheme();
if (tg) {
  tg.onEvent("themeChanged", applyTheme);
  try {
    // Telegramning yuqori panelini ham do'kon rangiga moslaymiz (qo'llab-quvvatlanmasa xato bermaydi)
    tg.setHeaderColor("secondary_bg_color");
  } catch (e) {
    /* eski Telegram versiyalarida mavjud emas — e'tiborsiz qoldiramiz */
  }
}

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
  renderPromo();
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
      searchInput.value = "";
      searchResultEl.classList.add("hidden");
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
  renderProductCards(list);
}

function isDiscounted(p) {
  return Number(p.old_price) > Number(p.price);
}

function discountPercent(p) {
  return Math.round((1 - Number(p.price) / Number(p.old_price)) * 100);
}

function renderProductCards(list) {
  productsEl.innerHTML = "";

  if (list.length === 0) {
    productsEl.innerHTML = `<div class="no-results">Hech narsa topilmadi 🙁</div>`;
    return;
  }

  list.forEach(p => {
    const qty = cart[p.id]?.qty || 0;
    const name = p.name || "Nomsiz mahsulot";
    const price = Number(p.price) || 0;
    const discounted = isDiscounted(p);

    const card = document.createElement("div");
    card.className = "product-card";

    const imgInner = p.image_url
      ? `<img class="product-img" src="${p.image_url}" alt="${name}">`
      : `<div class="product-img-placeholder">🛒</div>`;

    const badgeHtml = discounted
      ? `<span class="discount-badge">-${discountPercent(p)}%</span>`
      : "";

    const priceHtml = discounted
      ? `<span class="old">${Number(p.old_price).toLocaleString()}</span>${price.toLocaleString()} so'm`
      : `${price.toLocaleString()} so'm`;

    const controlsHtml = qty === 0
      ? `<button class="add-btn">🛒 Savatga qo'shish</button>`
      : `
        <div class="product-controls">
          <button class="qty-btn minus">−</button>
          <span class="qty-value">${qty}</span>
          <button class="qty-btn plus">+</button>
        </div>
      `;

    card.innerHTML = `
      <div class="product-img-wrap">
        ${imgInner}
        ${badgeHtml}
      </div>
      <div class="product-body">
        <div class="product-name">${name}</div>
        <div class="product-desc">${p.description || ""}</div>
        <div class="product-price">${priceHtml}</div>
        ${controlsHtml}
      </div>
    `;

    if (qty === 0) {
      card.querySelector(".add-btn").onclick = () => changeQty(p, 1);
    } else {
      card.querySelector(".plus").onclick = () => changeQty(p, 1);
      card.querySelector(".minus").onclick = () => changeQty(p, -1);
    }

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

  // Joriy ko'rinishni saqlab, faqat shu ro'yxatni qayta chizamiz
  // (qidiruv natijasi ustida bo'lsa ham, kategoriya ustida bo'lsa ham to'g'ri ishlaydi)
  if (searchInput.dataset.mode === "name" && searchInput.value.trim()) {
    const q = searchInput.value.trim().toLowerCase();
    renderProductCards(products.filter(p => (p.name || "").toLowerCase().includes(q)));
  } else {
    renderProducts();
  }

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

// ---------- Qidiruv: RAQAM bo'lsa — buyurtma, MATN bo'lsa — mahsulot nomi ----------

searchBtn.onclick = async () => {
  const query = searchInput.value.trim();
  if (!query) return;

  const isOrderNumber = /^\d+$/.test(query);

  if (!isOrderNumber) {
    // Mahsulot nomi bo'yicha qidiruv (mavjud katalog ichida, darhol)
    searchInput.dataset.mode = "name";
    searchResultEl.classList.add("hidden");
    activeCategory = "Hammasi";
    renderCategories();
    const q = query.toLowerCase();
    renderProductCards(products.filter(p => (p.name || "").toLowerCase().includes(q)));
    return;
  }

  // Buyurtma raqami bo'yicha qidiruv
  searchInput.dataset.mode = "order";
  const user = tg?.initDataUnsafe?.user;
  if (!user?.id) {
    const msg = "Iltimos, botni Telegram ichida oching.";
    if (tg) tg.showAlert(msg); else alert(msg);
    return;
  }

  searchResultEl.classList.remove("hidden");
  searchResultEl.textContent = "Qidirilmoqda...";

  try {
    const res = await fetch(`/api/order/search?user_id=${user.id}&number=${encodeURIComponent(query)}`);
    if (res.status === 404) {
      searchResultEl.textContent = "Bunday raqamli buyurtma topilmadi.";
      return;
    }
    const data = await res.json();
    const itemsText = data.items.map(i => `${i.name} x${i.qty}`).join(", ");
    searchResultEl.innerHTML = `
      <div><b>№${data.daily_number}</b> — ${data.status_label}</div>
      <div>${itemsText}</div>
      <div>Jami: ${data.total.toLocaleString()} so'm</div>
    `;
  } catch (e) {
    searchResultEl.textContent = "Xatolik yuz berdi.";
  }
};

searchInput.addEventListener("input", () => {
  const query = searchInput.value.trim();

  if (query === "") {
    searchInput.dataset.mode = "";
    searchResultEl.classList.add("hidden");
    renderProducts();
    return;
  }

  // Faqat raqamlardan iborat bo'lsa — bu buyurtma raqami, lupa tugmasi orqali qidiriladi
  if (/^\d+$/.test(query)) return;

  // Matn kiritilsa — darhol, tugma bosmasdan mahsulotlar orasidan qidiradi
  searchInput.dataset.mode = "name";
  searchResultEl.classList.add("hidden");
  activeCategory = "Hammasi";
  renderCategories();
  const q = query.toLowerCase();
  renderProductCards(products.filter(p => (p.name || "").toLowerCase().includes(q)));
});

// ---------- Yuqoridagi aksiya banneri (avtomatik almashinadi) ----------

let promoIndex = 0;
let promoTimer = null;
let promoItems = [];

function renderPromo() {
  promoItems = products.filter(isDiscounted).slice(0, 8);

  if (promoTimer) {
    clearInterval(promoTimer);
    promoTimer = null;
  }

  if (promoItems.length === 0) {
    promoEl.classList.add("hidden");
    promoTrackEl.innerHTML = "";
    promoDotsEl.innerHTML = "";
    return;
  }

  promoEl.classList.remove("hidden");
  promoIndex = 0;

  promoTrackEl.innerHTML = promoItems.map(p => {
    const img = p.image_url
      ? `<img src="${p.image_url}" alt="${p.name}">`
      : `<div class="product-img-placeholder" style="width:64px;height:64px;">🛒</div>`;
    return `
      <div class="promo-slide">
        ${img}
        <div class="promo-info">
          <span class="promo-label">-${discountPercent(p)}% AKSIYA</span>
          <div class="promo-name">${p.name || "Mahsulot"}</div>
          <div class="promo-prices">
            <span class="promo-old">${Number(p.old_price).toLocaleString()}</span>
            <span class="promo-new">${Number(p.price).toLocaleString()} so'm</span>
          </div>
        </div>
      </div>
    `;
  }).join("");

  promoDotsEl.innerHTML = promoItems.map((_, i) =>
    `<span class="${i === 0 ? "active" : ""}"></span>`
  ).join("");

  Array.from(promoDotsEl.children).forEach((dot, i) => {
    dot.onclick = () => goToPromo(i);
  });

  startPromoAutoplay();
  attachPromoSwipe();
}

function goToPromo(i) {
  promoIndex = (i + promoItems.length) % promoItems.length;
  promoTrackEl.style.transform = `translateX(-${promoIndex * 100}%)`;
  Array.from(promoDotsEl.children).forEach((dot, idx) => {
    dot.classList.toggle("active", idx === promoIndex);
  });
}

function startPromoAutoplay() {
  if (promoItems.length < 2) return;
  promoTimer = setInterval(() => goToPromo(promoIndex + 1), 4000);
}

function attachPromoSwipe() {
  let startX = 0;
  promoTrackEl.ontouchstart = e => { startX = e.touches[0].clientX; };
  promoTrackEl.ontouchend = e => {
    const delta = e.changedTouches[0].clientX - startX;
    if (Math.abs(delta) < 30) return;
    if (promoTimer) clearInterval(promoTimer);
    goToPromo(promoIndex + (delta < 0 ? 1 : -1));
    startPromoAutoplay();
  };
}

loadSettings();
loadProducts();
