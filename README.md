# Trader-Cab Worker Bot — Railway

## 🚀 Деплой

1. Загрузи эту папку на GitHub
2. Зайди на https://railway.app → New Project → Deploy from GitHub repo
3. В Variables добавь:
   - TRADERCAB_MKEY=mkey_ВАШ_КЛЮЧ
   - WEBHOOK_SECRET=вставь_сюда_webhook_secret
4. Railway сам даст HTTPS-домен — бот подхватит автоматически

## 🧠 Как работает

- 💳 Карта / 📲 СБП → создаёт заявку → выдаёт реквизиты
- 📋 Мои заявки → история + обновление статусов
- 💰 Баланс → USDT в trader-cab
- Вебхук → уведомления об оплате в реальном времени
