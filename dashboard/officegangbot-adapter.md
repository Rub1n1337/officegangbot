# OfficeGangBot Dashboard Adapter Plan

## Цель
Интегрировать Next.js-дэшборд ([fuma-nama/discord-bot-dashboard-next](https://github.com/fuma-nama/discord-bot-dashboard-next)) с функциями и API вашего OfficeGangBot.

---

## Основные шаги интеграции

1. **API Layer:**
   - Реализовать REST API (или FastAPI/Flask backend) для связи дашборда с ботом.
   - Эндпоинты: получение/изменение настроек (префикс, правила, welcome, reaction roles и др.), авторизация через Discord OAuth2.

2. **Адаптация UI:**
   - Добавить панели для управления:
     - Каналом и текстом правил
     - Welcome-сообщением
     - Ролями по реакции
     - Модерацией, логами и др.
   - Перевести/локализовать UI при необходимости

3. **Discord OAuth2:**
   - Настроить Discord OAuth2 для авторизации владельцев/админов сервера.

4. **Документация:**
   - Описать, какие endpoints нужны для дашборда и как они соотносятся с функциями бота.

---

## Пример API (backend для dashboard)

- `GET /api/guilds` — список серверов, где есть бот
- `GET /api/guilds/:id/settings` — получить настройки
- `POST /api/guilds/:id/settings` — изменить настройки
- `POST /api/guilds/:id/rules` — изменить правила
- `POST /api/guilds/:id/welcome` — welcome-сообщение
- `POST /api/guilds/:id/reaction-role` — настроить роль по реакции

---

## Следующие шаги
1. Скопировать исходники dashboard-next внутрь папки `dashboard/`
2. Переписать/адаптировать компоненты под OfficeGangBot API
3. Реализовать backend API (Flask/FastAPI или встроенный в Next.js)
4. Протестировать локально

---

**Если хочешь — могу сразу скопировать структуру dashboard-next и начать адаптацию.**
