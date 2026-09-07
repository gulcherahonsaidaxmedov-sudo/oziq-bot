const tg = window.Telegram?.WebApp;

if (tg) {
  tg.ready();
  tg.expand();

  try {
    tg.setHeaderColor("secondary_bg_color");
  } catch (e) {}
}


/* =========================
   GLOBAL
========================= */

let products = [];
let cart = {};
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
const searchHintEl = document.getElementById("search-hint");

const promoEl = document.getElementById("promo");
const promoTrackEl = document.getElementById("promo-track");
const promoDotsEl = document.getElementById("promo-dots");


/* =========================
   THEME
========================= */

function applyTheme() {
  const scheme =
    tg?.colorScheme ||
    (
      window.matchMedia &&
      window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light"
    );

  document.body.classList.toggle("dark", scheme === "dark");
}

applyTheme();

if (tg) {
  tg.onEvent("themeChanged", applyTheme);
}


/* =========================
   SETTINGS
========================= */

async function loadSettings() {
  try {
    const res = await fetch("/api/settings");

    if (!res.ok) return;

    const settings = await res.json();

    if (settings.background_url) {
      document.body.style.backgroundImage =
        `url("${settings.background_url}")`;

      document.body.classList.add("has-bg");
    }
  } catch (e) {
    console.log("Settings yuklanmadi:", e);
  }
}


/* =========================
   PRODUCTS
========================= */

async function loadProducts() {
  try {
    const res = await fetch("/api/products");

    if (!res.ok) {
      throw new Error("Mahsulotlarni yuklab bo'lmadi");
    }

    products = await res.json();

    renderCategories();
    renderProducts();
    renderPromo();

  } catch (e) {
    console.error(e);

    productsEl.innerHTML = `
      <div class="no-results">
        ❌ Mahsulotlarni yuklashda xatolik yuz berdi.
      </div>
    `;
  }
}


/* =========================
   CATEGORIES
========================= */

function renderCategories() {
  const cats = [
    "Hammasi",
    ...new Set(
      products
        .map(p => p.category)
        .filter(Boolean)
    )
  ];

  categoriesEl.innerHTML = "";

  cats.forEach(cat => {
    const btn = document.createElement("button");

    btn.textContent = cat;

    btn.className =
      "cat-btn" +
      (cat === activeCategory ? " active" : "");

    btn.onclick = () => {
      activeCategory = cat;

      searchInput.value = "";
      searchInput.dataset.mode = "";

      searchResultEl.classList.add("hidden");

      if (searchHintEl) {
        searchHintEl.style.display = "";
      }

      renderCategories();
      renderProducts();
    };

    categoriesEl.appendChild(btn);
  });
}


/* =========================
   RENDER PRODUCTS
========================= */

function renderProducts() {
  let list;

  if (activeCategory === "Hammasi") {
    list = products;
  } else {
    list = products.filter(
      p => p.category === activeCategory
    );
  }

  renderProductCards(list);
}


function isDiscounted(product) {
  return (
    Number(product.old_price) >
    Number(product.price)
  );
}


function discountPercent(product) {
  const oldPrice = Number(product.old_price);
  const price = Number(product.price);

  if (!oldPrice || oldPrice <= price) {
    return 0;
  }

  return Math.round(
    (1 - price / oldPrice) * 100
  );
}


/* =========================
   PRODUCT CARDS
========================= */

function renderProductCards(list) {
  productsEl.innerHTML = "";

  if (!list || list.length === 0) {
    productsEl.innerHTML = `
      <div class="no-results">
        😔 Hech narsa topilmadi
      </div>
    `;
    return;
  }

  list.forEach(product => {
    const qty =
      cart[product.id]?.qty || 0;

    const name =
      product.name || "Nomsiz mahsulot";

    const price =
      Number(product.price) || 0;

    const discounted =
      isDiscounted(product);

    const card =
      document.createElement("div");

    card.className = "product-card";


    /* IMAGE */

    const imgInner = product.image_url
      ? `
        <img
          class="product-img"
          src="${escapeHtml(product.image_url)}"
          alt="${escapeHtml(name)}"
          loading="lazy"
        >
      `
      : `
        <div class="product-img-placeholder">
          🛒
        </div>
      `;


    /* DISCOUNT */

    const badgeHtml = discounted
      ? `
        <span class="discount-badge">
          -${discountPercent(product)}%
        </span>
      `
      : "";


    /* PRICE */

    const priceHtml = discounted
      ? `
        <span class="old">
          ${Number(product.old_price).toLocaleString()}
        </span>

        ${price.toLocaleString()} so'm
      `
      : `
        ${price.toLocaleString()} so'm
      `;


    /* BUTTON */

    const controlsHtml = qty === 0

      ? `
        <button
          class="add-btn"
          type="button"
        >
          🛒 Savatga qo'shish
        </button>
      `

      : `
        <div class="product-controls">

          <button
            class="qty-btn minus"
            type="button"
          >
            −
          </button>

          <span class="qty-value">
            ${qty}
          </span>

          <button
            class="qty-btn plus"
            type="button"
          >
            +
          </button>

        </div>
      `;


    card.innerHTML = `
      <div class="product-img-wrap">

        ${imgInner}

        ${badgeHtml}

      </div>

      <div class="product-body">

        <div class="product-name">
          ${escapeHtml(name)}
        </div>

        <div class="product-desc">
          ${escapeHtml(product.description || "")}
        </div>

        <div class="product-price">
          ${priceHtml}
        </div>

        ${controlsHtml}

      </div>
    `;


    /* EVENTS */

    if (qty === 0) {
      card
        .querySelector(".add-btn")
        .onclick = () => {
          changeQty(product, 1);
        };

    } else {

      card
        .querySelector(".plus")
        .onclick = () => {
          changeQty(product, 1);
        };

      card
        .querySelector(".minus")
        .onclick = () => {
          changeQty(product, -1);
        };
    }


    productsEl.appendChild(card);
  });
}


/* =========================
   ESCAPE HTML
========================= */

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}


/* =========================
   CART
========================= */

function changeQty(product, delta) {
  const current =
    cart[product.id]?.qty || 0;

  const next =
    Math.max(0, current + delta);


  if (next === 0) {
    delete cart[product.id];

  } else {
    cart[product.id] = {
      product,
      qty: next
    };
  }


  /*
    Qidiruv holatini saqlaymiz.
  */

  if (
    searchInput.dataset.mode === "name" &&
    searchInput.value.trim()
  ) {

    const q =
      searchInput.value
        .trim()
        .toLowerCase();

    renderProductCards(
      products.filter(product =>
        (product.name || "")
          .toLowerCase()
          .includes(q)
      )
    );

  } else {

    renderProducts();
  }


  renderCartBar();
  renderCartList();
}


/* =========================
   CART LIST
========================= */

function renderCartList() {
  const items =
    Object.values(cart);


  if (items.length === 0) {
    cartListEl.classList.add("hidden");
    cartListEl.innerHTML = "";
    return;
  }


  cartListEl.classList.remove("hidden");


  cartListEl.innerHTML =
    items.map(item => {

      const subtotal =
        Number(item.product.price) *
        item.qty;

      return `
        <div
          class="cart-item"
          data-id="${item.product.id}"
        >

          <span class="cart-item-name">
            ${escapeHtml(item.product.name)}
          </span>

          <div class="cart-item-controls">

            <button
              class="qty-btn minus"
              type="button"
            >
              −
            </button>

            <span class="qty-value">
              ${item.qty}
            </span>

            <button
              class="qty-btn plus"
              type="button"
            >
              +
            </button>

          </div>

          <span class="cart-item-subtotal">
            ${subtotal.toLocaleString()} so'm
          </span>

        </div>
      `;
    }).join("");


  items.forEach(item => {

    const row =
      cartListEl.querySelector(
        `.cart-item[data-id="${item.product.id}"]`
      );

    if (!row) return;


    row.querySelector(".plus").onclick =
      () => changeQty(item.product, 1);


    row.querySelector(".minus").onclick =
      () => changeQty(item.product, -1);
  });
}


/* =========================
   CART BAR
========================= */

function renderCartBar() {
  const items =
    Object.values(cart);


  if (items.length === 0) {
    cartBarEl.classList.add("hidden");
    return;
  }


  const total =
    items.reduce(
      (sum, item) =>
        sum +
        Number(item.product.price) *
        item.qty,
      0
    );


  const count =
    items.reduce(
      (sum, item) =>
        sum + item.qty,
      0
    );


  cartSummaryEl.textContent =
    `${count} ta mahsulot — ${total.toLocaleString()} so'm`;

  cartBarEl.classList.remove("hidden");
}


/* =========================
   CHECKOUT
========================= */

checkoutBtn.onclick = async () => {

  const items =
    Object.values(cart).map(item => ({
      id: item.product.id,
      name: item.product.name,
      price: item.product.price,
      qty: item.qty
    }));


  if (items.length === 0) {
    return;
  }


  const user =
    tg?.initDataUnsafe?.user;


  if (!user?.id) {

    showAlert(
      "Iltimos, do'konni Telegram bot ichidan oching."
    );

    return;
  }


  const payload = {
    user_id: user.id,
    username:
      user.username ||
      user.first_name ||
      "",
    items
  };


  checkoutBtn.disabled = true;
  checkoutBtn.textContent =
    "Yuborilmoqda...";


  try {

    const res =
      await fetch("/api/order", {
        method: "POST",

        headers: {
          "Content-Type":
            "application/json"
        },

        body:
          JSON.stringify(payload)
      });


    const data =
      await res.json();


    if (!res.ok || !data.order_id) {
      throw new Error(
        data.error ||
        "Buyurtma yuborilmadi"
      );
    }


    cart = {};

    renderProducts();
    renderCartBar();
    renderCartList();


    showAlert(
      `✅ Buyurtmangiz qabul qilindi!\n\n` +
      `📦 Navbat raqamingiz: №${data.daily_number}`,
      () => {

        try {
          tg?.close();
        } catch (e) {}

      }
    );


  } catch (error) {

    console.error(error);

    showAlert(
      `❌ Xatolik:\n${error.message}`
    );

  } finally {

    checkoutBtn.disabled = false;

    checkoutBtn.innerHTML =
      `Buyurtma berish <span>→</span>`;
  }
};


/* =========================
   TELEGRAM ALERT
========================= */

function showAlert(message, callback) {

  if (tg?.showAlert) {
    tg.showAlert(message, callback);
  } else {
    alert(message);

    if (callback) {
      callback();
    }
  }
}


/* =========================
   SEARCH
========================= */

async function searchOrder(number) {

  const user =
    tg?.initDataUnsafe?.user;


  if (!user?.id) {

    showAlert(
      "Iltimos, botni Telegram ichida oching."
    );

    return;
  }


  searchResultEl.classList.remove("hidden");

  searchResultEl.innerHTML =
    "🔎 Qidirilmoqda...";


  try {

    const url =
      `/api/order/search?user_id=${encodeURIComponent(user.id)}` +
      `&number=${encodeURIComponent(number)}`;


    const res =
      await fetch(url);


    if (res.status === 404) {

      searchResultEl.innerHTML =
        "❌ Bunday buyurtma topilmadi.";

      return;
    }


    if (!res.ok) {
      throw new Error(
        "Server xatosi"
      );
    }


    const data =
      await res.json();


    const items =
      Array.isArray(data.items)
        ? data.items
        : [];


    const itemsText =
      items.length
        ? items
            .map(item =>
              `${escapeHtml(item.name)} ×${item.qty}`
            )
            .join("<br>")
        : "Mahsulotlar mavjud emas";


    searchResultEl.innerHTML = `
      <div>
        <b>📦 №${data.daily_number}</b>
        — ${escapeHtml(data.status_label || "")}
      </div>

      <div style="margin-top:7px;">
        ${itemsText}
      </div>

      <div style="margin-top:7px;">
        💰 Jami:
        <b>
          ${Number(data.total).toLocaleString()} so'm
        </b>
      </div>
    `;


  } catch (error) {

    console.error(error);

    searchResultEl.innerHTML =
      "❌ Qidirishda xatolik yuz berdi.";
  }
}


/* =========================
   SEARCH BUTTON
========================= */

searchBtn.onclick = async () => {

  const query =
    searchInput.value.trim();


  if (!query) {

    searchResultEl.classList.add("hidden");

    if (searchHintEl) {
      searchHintEl.style.display = "";
    }

    return;
  }


  /*
    Faqat raqam bo'lsa:
    BUYURTMA RAQAMI
  */

  if (/^\d+$/.test(query)) {

    searchInput.dataset.mode = "order";

    if (searchHintEl) {
      searchHintEl.style.display = "none";
    }

    await searchOrder(query);

    return;
  }


  /*
    Matn bo'lsa:
    MAHSULOT QIDIRUVI
  */

  searchInput.dataset.mode = "name";

  activeCategory = "Hammasi";

  renderCategories();

  const q =
    query.toLowerCase();


  const result =
    products.filter(product =>
      (
        product.name || ""
      )
        .toLowerCase()
        .includes(q)
    );


  if (searchHintEl) {
    searchHintEl.style.display =
      "none";
  }

  searchResultEl.classList.add("hidden");

  renderProductCards(result);
};


/* =========================
   SEARCH INPUT
========================= */

searchInput.addEventListener(
  "input",
  () => {

    const query =
      searchInput.value.trim();


    if (!query) {

      searchInput.dataset.mode = "";

      searchResultEl.classList.add(
        "hidden"
      );

      if (searchHintEl) {
        searchHintEl.style.display = "";
      }

      renderProducts();

      return;
    }


    /*
      Raqam bo'lsa avtomatik qidirmaymiz.
      🔍 bosilganda buyurtmani tekshiradi.
    */

    if (/^\d+$/.test(query)) {

      searchInput.dataset.mode =
        "order";

      searchResultEl.classList.add(
        "hidden"
      );

      if (searchHintEl) {
        searchHintEl.textContent =
          "🔢 Buyurtma raqamini tekshirish uchun 🔍 bosing";
        searchHintEl.style.display = "";
      }

      return;
    }


    /*
      Matn bo'lsa darhol mahsulotlarni
      qidiramiz.
    */

    searchInput.dataset.mode =
      "name";

    activeCategory = "Hammasi";

    renderCategories();

    const q =
      query.toLowerCase();


    const result =
      products.filter(product => {

        const name =
          (product.name || "")
            .toLowerCase();

        const category =
          (product.category || "")
            .toLowerCase();

        const description =
          (product.description || "")
            .toLowerCase();


        return (
          name.includes(q) ||
          category.includes(q) ||
          description.includes(q)
        );
      });


    searchResultEl.classList.add(
      "hidden"
    );


    if (searchHintEl) {
      searchHintEl.textContent =
        "🔎 Mahsulotlar orasidan qidirilmoqda";
      searchHintEl.style.display = "";
    }


    renderProductCards(result);
  }
);


/* =========================
   ENTER = SEARCH
========================= */

searchInput.addEventListener(
  "keydown",
  event => {

    if (event.key === "Enter") {

      event.preventDefault();

      searchBtn.click();
    }
  }
);


/* =========================
   PROMO
========================= */

let promoIndex = 0;
let promoTimer = null;
let promoItems = [];


function renderPromo() {

  promoItems =
    products
      .filter(isDiscounted)
      .slice(0, 8);


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


  promoTrackEl.innerHTML =
    promoItems
      .map(product => {

        const img =
          product.image_url

            ? `
              <img
                src="${escapeHtml(product.image_url)}"
                alt="${escapeHtml(product.name || "Mahsulot")}"
              >
            `

            : `
              <div
                class="product-img-placeholder"
                style="
                  width:78px;
                  height:78px;
                "
              >
                🛒
              </div>
            `;


        return `
          <div class="promo-slide">

            ${img}

            <div class="promo-info">

              <span class="promo-label">
                -${discountPercent(product)}% AKSIYA
              </span>

              <div class="promo-name">
                ${escapeHtml(product.name || "Mahsulot")}
              </div>

              <div class="promo-prices">

                <span class="promo-old">
                  ${Number(product.old_price).toLocaleString()}
                </span>

                <span class="promo-new">
                  ${Number(product.price).toLocaleString()} so'm
                </span>

              </div>

            </div>

          </div>
        `;
      })
      .join("");


  promoDotsEl.innerHTML =
    promoItems
      .map(
        (_, index) =>
          `<span class="${index === 0 ? "active" : ""}"></span>`
      )
      .join("");


  Array
    .from(promoDotsEl.children)
    .forEach((dot, index) => {

      dot.onclick = () =>
        goToPromo(index);

    });


  startPromoAutoplay();
  attachPromoSwipe();
}


/* =========================
   PROMO SLIDE
========================= */

function goToPromo(index) {

  promoIndex =
    (index + promoItems.length) %
    promoItems.length;


  promoTrackEl.style.transform =
    `translateX(-${promoIndex * 100}%)`;


  Array
    .from(promoDotsEl.children)
    .forEach((dot, idx) => {

      dot.classList.toggle(
        "active",
        idx === promoIndex
      );

    });
}


/* =========================
   PROMO AUTOPLAY
========================= */

function startPromoAutoplay() {

  if (promoItems.length < 2) {
    return;
  }


  promoTimer =
    setInterval(
      () => {
        goToPromo(
          promoIndex + 1
        );
      },
      4000
    );
}


/* =========================
   PROMO SWIPE
========================= */

function attachPromoSwipe() {

  let startX = 0;


  promoTrackEl.ontouchstart =
    event => {

      startX =
        event.touches[0].clientX;
    };


  promoTrackEl.ontouchend =
    event => {

      const delta =
        event.changedTouches[0].clientX -
        startX;


      if (Math.abs(delta) < 30) {
        return;
      }


      if (promoTimer) {
        clearInterval(promoTimer);
}
  
