# 🎮 GameVoicesBot

**GameVoicesBot** — PC, PlayStation, Xbox va Android platformalari uchun eng
so'nggi o'yin yangiliklarini avtomatik ravishda o'zbek tilida Telegram
kanaliga joylashtiruvchi bot.

Har **6 soatda** bot [RAWG.io](https://rawg.io/apidocs) o'yinlar
bazasidan yangi/yaqinda chiqqan o'yinlarni tekshiradi, sarlavha, rasm va
tavsifni oladi, matnni o'zbek tiliga tarjima qiladi va kanalga chiroyli
formatlangan post sifatida joylaydi. Har bir o'yin faqat bir marta post
qilinishi SQLite bazasi orqali kafolatlanadi.

---

## ✨ Asosiy imkoniyatlar

- ⏱ Har 6 soatda avtomatik o'yin yangiliklari posti (interval sozlanadi)
- 🖥 PC, 🎮 PlayStation, 🟢 Xbox, 📱 Android platformalarini qo'llab-quvvatlaydi
- 🖼 Sarlavha, tavsif va rasmni avtomatik oladi (RAWG.io API)
- 🇺🇿 Tavsiflarni o'zbek tiliga avtomatik tarjima qiladi
- 🚫 SQLite yordamida takroriy postlarning oldini oladi
- 👮 Admin buyruqlari: `/start`, `/post`, `/history`, `/stats`, `/help`
- 📝 To'liq logging tizimi (konsol + fayl)
- ⚠️ Barcha xatoliklar uchun markazlashgan error handling
- ☁️ Render.com'ga deploy qilishga tayyor (`render.yaml` bilan)

---

## 📁 Loyiha tuzilishi

```
GameVoicesBot/
│
├── main.py           # Bot kirish nuqtasi, komandalar va scheduler ulanishi
├── config.py         # Barcha sozlamalar (.env orqali)
├── games.py          # RAWG.io API bilan ishlash va post formatlash
├── scheduler.py       # APScheduler orqali avtomatik post
├── history.py         # /history va /stats uchun formatlash
├── database.py        # SQLite bilan ishlash (duplicate oldini olish)
├── utils.py            # Logging, tarjima, matn yordamchi funksiyalari
├── requirements.txt
├── render.yaml
├── .env.example
├── README.md
└── data/               # SQLite baza va log fayllar shu yerda saqlanadi
```

---

## ⚙️ O'rnatish (lokal)

### 1. Talablar

- Python **3.13+**
- Telegram bot tokeni ([@BotFather](https://t.me/BotFather) orqali oling)
- RAWG.io API kaliti ([rawg.io/apidocs](https://rawg.io/apidocs) - bepul ro'yxatdan o'tish)
- Bot qo'shilgan Telegram kanal (bot admin bo'lishi va post qilish huquqiga ega bo'lishi kerak)

### 2. Repozitoriyani klonlash va muhitni tayyorlash

```bash
git clone <your-repo-url> GameVoicesBot
cd GameVoicesBot

python3.13 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Environment o'zgaruvchilarini sozlash

```bash
cp .env.example .env
```

`.env` faylini oching va quyidagilarni to'ldiring:

```env
BOT_TOKEN=123456789:AAExampleTokenReplaceThis
CHANNEL_ID=@your_channel_username
ADMIN_IDS=111111111,222222222
RAWG_API_KEY=your_rawg_api_key_here
```

> 💡 O'z Telegram ID'ingizni bilish uchun [@userinfobot](https://t.me/userinfobot)
> ga yozing.

### 4. Botni ishga tushirish

```bash
python main.py
```

Konsolda quyidagiga o'xshash log ko'rinishi kerak:

```
2026-07-24 12:00:00 | INFO     | gamevoices | Database initialized at .../data/gamevoices.db
2026-07-24 12:00:00 | INFO     | gamevoices | GameVoicesBot starting (polling mode)...
2026-07-24 12:00:01 | INFO     | gamevoices | Scheduler configured: job will run every 6 hour(s).
2026-07-24 12:00:01 | INFO     | gamevoices | APScheduler started; automatic posting is active.
```

---

## 🤖 Buyruqlar

| Buyruq      | Tavsif                                                              | Ruxsat        |
|-------------|----------------------------------------------------------------------|---------------|
| `/start`    | Botni tanishtirish xabari                                            | Hamma         |
| `/help`     | Barcha buyruqlar ro'yxati                                             | Hamma         |
| `/post`     | Yangi o'yinlarni qo'lda qidirib, darhol kanalga joylash               | Faqat admin   |
| `/history`  | Oxirgi 10 ta joylangan post tarixi                                   | Faqat admin   |
| `/stats`    | Umumiy statistika (jami postlar, platformalar bo'yicha taqsimot)      | Faqat admin   |

Adminlar ro'yxati `.env` faylidagi `ADMIN_IDS` orqali belgilanadi.

---

## ☁️ Render.com'ga deploy qilish

1. Loyihani GitHub/GitLab repozitoriyasiga push qiling.
2. Render Dashboard'da **New +** → **Blueprint** ni tanlang va repozitoriyangizni ulang.
3. Render `render.yaml` faylini avtomatik o'qiydi va **Background Worker** turidagi
   xizmat yaratadi (bot polling rejimida ishlaydi, HTTP port kerak emas).
4. Render sizdan quyidagi environment o'zgaruvchilarini so'raydi (`sync: false`
   deb belgilangan):
   - `BOT_TOKEN`
   - `CHANNEL_ID`
   - `ADMIN_IDS`
   - `RAWG_API_KEY`
   - `LIBRETRANSLATE_API_KEY` (ixtiyoriy)
5. **Apply** tugmasini bosing — Render avtomatik ravishda build qilib, botni ishga tushiradi.
6. `data/` papkasi uchun Render'da persistent disk (`render.yaml`da allaqachon
   sozlangan) ma'lumotlar bazasi qayta deploylardan keyin ham saqlanishini
   ta'minlaydi.

---

## 🧩 Qo'shimcha sozlamalar

| O'zgaruvchi           | Standart qiymat                          | Tavsif                                              |
|------------------------|-------------------------------------------|------------------------------------------------------|
| `POST_INTERVAL_HOURS`  | `6`                                        | Avtomatik post oralig'i (soat)                       |
| `GAMES_LOOKBACK_DAYS`  | `3`                                        | Nechi kunlik yangi o'yinlarni qidirish                |
| `GAMES_PER_RUN`        | `4`                                        | Har bir avtomatik ishga tushishda joylanadigan max soni |
| `TRANSLATE_ENABLED`    | `true`                                     | O'zbek tiliga tarjimani yoqish/o'chirish              |
| `LIBRETRANSLATE_URL`   | `https://libretranslate.com/translate`     | Tarjima xizmati manzili                              |
| `TIMEZONE`             | `Asia/Tashkent`                            | Scheduler uchun vaqt zonasi                          |
| `LOG_LEVEL`            | `INFO`                                     | Logging darajasi (`DEBUG`, `INFO`, `WARNING`, ...)   |

---

## 🛠 Texnologiyalar

- [python-telegram-bot](https://docs.python-telegram-bot.org/) v22+ — Telegram Bot API bilan ishlash
- [APScheduler](https://apscheduler.readthedocs.io/) — davriy vazifalarni rejalashtirish
- [Requests](https://requests.readthedocs.io/) — RAWG.io va tarjima API bilan HTTP so'rovlar
- [SQLite](https://www.sqlite.org/) (stdlib `sqlite3`) — takroriy postlarni oldini olish va tarix
- [python-dotenv](https://pypi.org/project/python-dotenv/) — `.env` fayllarni yuklash

---

## 🐞 Muammolarni bartaraf etish

- **Bot javob bermayapti** — `BOT_TOKEN` to'g'riligini va botning ishga tushganini
  (`python main.py` konsolidagi loglarni) tekshiring.
- **Kanalga post tushmayapti** — bot kanalga **admin** sifatida qo'shilganini va
  "Post Messages" huquqiga ega ekanini tekshiring; `CHANNEL_ID` to'g'ri formatda
  bo'lishi kerak (`@username` yoki `-100...` raqamli ID).
- **"RAWG_API_KEY is not set" xatosi** — [rawg.io/apidocs](https://rawg.io/apidocs)
  sahifasidan bepul API kalit oling va `.env` fayliga qo'shing.
- **Tarjima ishlamayapti** — bu tanqidiy xato emas: tarjima xizmati ishlamasa,
  bot original (odatda inglizcha) matnni ishlatishda davom etadi. Loglarda
  ogohlantirish ko'rinadi.
- **Loglarni ko'rish** — `data/gamevoices.log` fayli yoki konsol chiqishini tekshiring.

---

## 📄 Litsenziya

Ushbu loyiha shaxsiy va tijorat maqsadlarida erkin foydalanish uchun taqdim etilgan.
