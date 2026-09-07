import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

ADMIN_IDS = {
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip()
}

WEBAPP_URL = os.getenv(
    "WEBAPP_URL",
    "https://oziq-bot-production-83af.up.railway.app/webapp/"
).strip()

# Railway uchun
PORT = int(os.getenv("PORT", "8080"))
