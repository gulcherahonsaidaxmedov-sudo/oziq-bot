Oziq-ovqat do'koni uchun Telegram bot (Mini App)
Loyiha noldan, aiogram 3 va aiohttp asosida qurilgan. Telefondan ham, kompyuterdan ham joylab ishga tushirsa bo'ladi.
Imkoniyatlar
🛒 Telegram ichida ochiladigan mini-ilova (katalog + savat, kategoriya bo'yicha filtr)
📦 Buyurtma qabul qilish, adminga darhol xabar borishi
✅ Admin "Qabul qilish" → "Tayyor" bosgach, mijozga avtomatik xabar boradi
📜 Mijoz uchun "Mening buyurtmalarim"
⚙️ Admin panel: mahsulot qo'shish, mahsulotlar/buyurtmalar ro'yxati, umumiy xabar yuborish
1-qadam: Bot yaratish
Telegramda @BotFather ga o'ting, /newbot yozing.
Bot nomi va username so'raladi (username bot bilan tugashi kerak, masalan OziqDokonBot).
Sizga token beriladi (masalan 123456:AAExxxxx) — uni saqlab qo'ying, hech kimga bermang.
2-qadam: O'z Telegram ID'ingizni bilib olish
@userinfobot ga /start yozing — u sizga ID raqamingizni beradi (masalan 123456789).
Shu raqam — siz admin bo'lasiz.
3-qadam: Kodni GitHub'ga joylash
github.com'da hisob oching (agar yo'q bo'lsa).
New repository → nom bering (masalan oziq-bot) → Create repository.
Upload files (yoki "Add file → Upload files") bo'limiga o'ting, shu papkadagi barcha fayl va papkalarni (bot.py, config.py, database.py, requirements.txt, Procfile, webapp/ papkasi) sudrab tashlang (drag & drop) — bu birma-bir fayl yaratishdan tezroq.
Pastda Commit changes tugmasini bosing.
4-qadam: Railway'da deploy qilish
railway.app saytiga o'ting, GitHub hisobingiz orqali kiring.
New Project → Deploy from GitHub repo → yaratgan oziq-bot repongizni tanlang.
Railway avtomatik Python loyihasini aniqlaydi va o'rnatadi.
Variables bo'limiga o'ting va quyidagilarni qo'shing:
BOT_TOKEN = BotFather'dan olgan tokeningiz
ADMIN_IDS = sizning Telegram ID'ingiz (bir nechta bo'lsa vergul bilan: 12345,67890)
WEBAPP_URL = hozircha bo'sh qoldiring, keyingi qadamda to'ldiramiz
Settings → Networking → Generate Domain tugmasini bosing — sizga masalan oziq-bot-production.up.railway.app kabi manzil beradi.
Shu manzilni oling va WEBAPP_URL qiymatini quyidagicha yangilang: https://oziq-bot-production.up.railway.app/webapp/ (oxirida /webapp/ bo'lishi shart).
Loyiha qayta deploy bo'ladi (Railway buni environment o'zgarganda avtomatik qiladi).
5-qadam: Botni tekshirish
Telegramda botingizga o'ting, /start bosing.
"🛒 Do'kon" tugmasini bosing — mini-ilova ochiladi (boshida mahsulotlar bo'sh bo'ladi, chunki hali qo'shilmagan).
"⚙️ Admin panel → ➕ Mahsulot qo'shish" orqali bir nechta mahsulot qo'shing.
Mini-ilovada mahsulot tanlab, "Buyurtma berish" tugmasini bosing.
Admin (siz) darhol yangi buyurtma haqida xabar olasiz, "✅ Qabul qilish" / "❌ Bekor qilish" tugmalari bilan.
Qabul qilgach, "🍳 Tayyor deb belgilash" tugmasi chiqadi — bosgach mijozga avtomatik "buyurtmangiz tayyor" xabari boradi.
Texnik eslatma
Mini-ilova foydalanuvchi ma'lumotini Telegram'ning initDataUnsafe orqali oladi — bu MVP uchun yetarli, lekin haqiqiy production loyihada initData'ni server tomonda hash orqali tekshirish tavsiya etiladi (soxta buyurtmalarning oldini olish uchun).
Keyinroq qo'shsa bo'ladigan funksiyalar
Mahsulot rasmlarini yuklash
Click/Payme orqali onlayn to'lov
Yetkazib berish manzili so'rash
Mahsulotni admin panelidan tahrirlash/o'chirish
Savol yoki qo'shimcha funksiya kerak bo'lsa — shu suhbatda so'rashingiz mumkin.
