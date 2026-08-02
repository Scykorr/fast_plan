# Настройка почты (SMTP) в Fast Plan

Источник истины для credentials — файл **`.env`** (или переменные окружения Docker).  
В UI (Settings → **Почта / SMTP**) можно только **посмотреть статус** и **отправить тест**; пароль SMTP через API не задаётся.

См. также checklist в [`STAGING.md`](../STAGING.md) § SMTP и API:

- `GET /api/workspace/email/status/`
- `POST /api/workspace/email/test/` `{ "to": "optional@mail" }`

---

## 1. Быстрый старт

1. Скопируйте `.env.example` → `.env` (если ещё нет).
2. Заполните блок Email (ниже — пример для mail.ru).
3. Перезапустите backend / `docker compose up -d backend`.
4. Войдите как **owner** workspace → **Settings** → **Почта / SMTP** → **Отправить тест**.
5. Убедитесь, что письмо в **Входящих** (и проверьте Спам).
6. Только после зелёного теста включите проверку email:

```env
REQUIRE_EMAIL_VERIFICATION=true
```

Пока SMTP не проверен, оставляйте `REQUIRE_EMAIL_VERIFICATION=false` — иначе регистрация/вход сломаются без доставки писем.

---

## 2. Переменные окружения

| Переменная | Назначение | Пример |
|------------|------------|--------|
| `EMAIL_BACKEND` | Класс бэкенда Django | `django.core.mail.backends.smtp.EmailBackend` |
| `EMAIL_HOST` | SMTP-хост | `smtp.mail.ru` |
| `EMAIL_PORT` | Порт | `587` (STARTTLS) или `465` (SSL) |
| `EMAIL_HOST_USER` | Логин SMTP (обычно полный email) | `you@mail.ru` |
| `EMAIL_HOST_PASSWORD` | Пароль приложения / SMTP | *(секрет)* |
| `EMAIL_USE_TLS` | STARTTLS | `true` для 587 |
| `EMAIL_USE_SSL` | Implicit SSL | `true` для 465; тогда TLS обычно `false` |
| `DEFAULT_FROM_EMAIL` | From (должен быть разрешён провайдером) | `Fast Plan <you@mail.ru>` |
| `FRONTEND_BASE_URL` | База ссылок в письмах | `https://your-domain` или `http://localhost:8080` |
| `REQUIRE_EMAIL_VERIFICATION` | Требовать confirm перед логином | `false` → `true` после теста |

В **DEBUG** без явного `EMAIL_BACKEND` Django часто использует **console** (письма в лог, не в сеть). Для реальной отправки задайте SMTP-backend явно.

В Docker Compose переменные `EMAIL_*` и `REQUIRE_EMAIL_VERIFICATION` пробрасываются в сервис `backend` (см. `docker-compose.yml`).

---

## 3. Пример: mail.ru

1. В настройках mail.ru включите доступ по SMTP и создайте **пароль приложения** (не основной пароль ящика, если включена 2FA).
2. В `.env`:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.mail.ru
EMAIL_PORT=465
EMAIL_USE_SSL=true
EMAIL_USE_TLS=false
EMAIL_HOST_USER=you@mail.ru
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=Fast Plan <you@mail.ru>
FRONTEND_BASE_URL=http://localhost:8080
REQUIRE_EMAIL_VERIFICATION=false
```

Альтернатива на порту 587:

```env
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_USE_SSL=false
```

3. Перезапуск backend → Settings → тест на свой ящик.

---

## 4. Пример: Gmail

Нужен пароль приложения Google (аккаунт с 2FA):

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_USE_SSL=false
EMAIL_HOST_USER=you@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=Fast Plan <you@gmail.com>
```

---

## 5. Какие письма зависят от SMTP

| Сценарий | Когда уходит |
|----------|----------------|
| Подтверждение email | Регистрация / resend — если `REQUIRE_EMAIL_VERIFICATION=true` |
| Сброс пароля | `POST /api/auth/password/forgot/` |
| Приглашение в workspace | Settings → приглашения (+ resend) |
| Дайджест напоминаний | Celery / `send_reminders` |
| Тест SMTP | Settings → «Отправить тест» |

Шаблоны: `backend/templates/email/*.txt|*.html`.

---

## 6. Deliverability (чтобы не уходило в спам)

- `DEFAULT_FROM_EMAIL` — ящик/домен, с которого реально шлёте.
- Для своего домена: **SPF**, **DKIM**, **DMARC** у DNS-провайдера.
- Сначала тест на тот же ящик, что `EMAIL_HOST_USER`, потом внешний.
- Проверьте папку «Спам» у mail.ru / Gmail.

---

## 7. Диагностика

| Симптом | Что проверить |
|---------|----------------|
| Settings: `console` / не `configured` | `EMAIL_BACKEND`, `EMAIL_HOST`, перезапуск контейнера |
| Тест `ok: false` | хост/порт/TLS-SSL, пароль приложения, firewall |
| Письмо не пришло | Спам, From ≠ разрешённый ящик, лимиты провайдера |
| Логин «email не подтверждён» | SMTP ещё не работает, а `REQUIRE_EMAIL_VERIFICATION=true` — верните `false` или почините SMTP |

Локально без SMTP:

```env
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
REQUIRE_EMAIL_VERIFICATION=false
```

Письма появятся в логе backend.

---

## 8. Порядок на staging / production

1. Прописать `EMAIL_*` + `FRONTEND_BASE_URL` на реальный URL.  
2. Owner → Settings → тест → inbox.  
3. Forgot-password + invite (см. `STAGING.md`).  
4. `REQUIRE_EMAIL_VERIFICATION=true` → register → письмо → `/verify-email` → login.  
5. Не коммитьте `.env` с паролями в git.
