# Nima o'zgardi

## 1. Buyurtma "qabul qilinmayapti" bug'i
Eski kodda mini-ilova biror sababga ko'ra Telegram foydalanuvchisini
aniqlay olmasa (masalan brauzerda ochilgan bo'lsa), server hech qanday
tushunarli xato qaytarmasdan shunchaki "invalid data" derdi va odam buni
"ishlamayapti" deb qabul qilardi. Endi:
- `app.js` — agar Telegram foydalanuvchisi topilmasa, aniq xabar chiqadi:
  *"Do'konni Telegram bot ichidagi tugma orqali oching"*.
- `bot.py` — server xatoliklari endi `try/except` bilan ushlanadi va admin
  konsolida (`logging`) ko'rinadi, frontendga esa aniq xato matni qaytadi.

## 2. Mahsulotlarga rasm qo'shish
- Admin "➕ Mahsulot qo'shish" bosganda endi oxirida rasm so'raladi
  (yoki rasm bo'lmasa "-" deb yozish mumkin).
- Rasm `webapp/uploads/` papkasiga saqlanadi va mini-ilovada avtomatik
  ko'rsatiladi (skrinshotdagidek kartochka ko'rinishida).

## 3. Mijozdan kontakt (telefon) so'rash
- `/start` bosilganda, agar foydalanuvchi avval raqam yubormagan bo'lsa,
  botga faqat "📱 Telefon raqamni yuborish" tugmasi chiqadi.
- Raqam bazaga saqlanadi va yangi buyurtma kelganda admin xabarida
  ko'rsatiladi (qo'ng'iroq qilish uchun).

## 4. Fon rasmi (orqa fon)
- Admin panelda yangi tugma: "🖼 Fon rasmini o'rnatish".
- Rasm yuborilsa, u mini-ilovaning butun sahifasiga fon sifatida
  qo'yiladi (`/api/settings` orqali frontendga uzatiladi).

## 5. Savatdagi tovarlar alohida ko'rinishi
- Avval faqat pastda umumiy summa ko'rinardi. Endi savatga qo'shilgan
  har bir tovar alohida qatorda, miqdorini o'zgartirish tugmalari bilan
  ko'rinadi (`cart-list`).

## 6. Savdo statistikasi
- Admin panelda yangi tugma: "📈 Savdo statistikasi".
- Bosilganda 1 kun, 1 hafta, 1 oy va 1 yil ichidagi umumiy savdo summasi
  va buyurtmalar soni chiqadi (bekor qilingan buyurtmalar hisobga
  olinmaydi).

## 7. Navbat / buyurtma raqami
- Avval buyurtma raqami baza ichidagi umumiy ID edi (masalan #482), bu
  mijoz uchun tushunarsiz va tartibsiz edi.
- Endi har bir buyurtmaga **kunlik navbat raqami** beriladi — har kuni
  №1 dan qayta boshlanadi. Masalan bugungi birinchi buyurtma — №1,
  ikkinchisi — №2 va h.k.
- Bu raqam:
  - mini-ilovada buyurtma tasdiqlanganda mijozga ko'rsatiladi,
  - "Qabul qilindi / Tayyor / Bekor qilindi" xabarlarida ishlatiladi,
  - "📜 Mening buyurtmalarim" bo'limida ko'rinadi,
  - admin uchun yangi buyurtma xabarida asosiy raqam sifatida chiqadi
    (ichki baza ID'si qavs ichida qo'shimcha ko'rsatiladi).

## 8. Bir xil dizayn
- Barcha mahsulot kartochkalari endi bir xil tuzilishda: rasm (yoki
  ikonka), nomi, tavsifi, narxi, miqdor tugmalari — skrinshotga o'xshab.

---

## Nimalarni deploy qilishdan oldin tekshirish kerak

1. **`shop.db` fayli avtomatik yangilanadi** — kod ishga tushganda
   (`database.init_db()`) yangi ustunlar (`image_url`, `phone` va h.k.)
   avtomatik qo'shiladi, eski ma'lumotlar yo'qolmaydi.
2. Railway'da qayta deploy qilinganda `webapp/uploads/` papkasi avtomatik
   yaratiladi — lekin **Railway'ning fayl tizimi doimiy emas** (restart
   bo'lsa fayllar o'chib ketishi mumkin). Agar bu muammo bo'lsa, keyinroq
   rasmlarni tashqi saqlash (masalan Cloudinary yoki S3) ga o'tkazish
   tavsiya etiladi — hozircha oddiy yechim sifatida shu yetarli.
3. Fayllarni GitHub repo'ga joylashtirib (`bot.py`, `database.py`,
   `webapp/index.html`, `webapp/app.js`, `webapp/style.css`), commit va
   push qiling — Railway avtomatik qayta deploy qiladi.
   
