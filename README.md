# QIWI Wallet API Test Task - Pytest version

Решение тестового задания по QIWI Wallet API.
По условию тестового задания сервис не является рабочим. Также реальные токены не передаются в репозиторий. Поэтому тесты спроектированы на основе документации и могут падать при запуске без валидного токена, кошелька и доступного API.

## Структура проекта

```text
qiwi_api_test_task_pytest/
├── postman/
│   ├── qiwi-wallet-tests.postman_collection.json
│   └── qiwi-wallet-local.postman_environment.json
├── tests/
│   └── test_qiwi_api.py
├── .env
├── .gitignore
├── README.md
└── requirements.txt
```

## Покрытые сценарии

### 1. Проверка доступности сервиса

```http
GET /payment-history/v2/persons/{wallet}/payments?rows=1
```

Проверяется:

- статус ответа `200 OK`;
- ответ в формате JSON;
- наличие поля `data`;
- `data` является массивом;
- количество элементов не превышает `rows=1`.

### 2. Проверка баланса

```http
GET /funding-sources/v2/persons/{wallet}/accounts
```

Проверяется:

- статус ответа `200 OK`;
- наличие массива `accounts`;
- наличие рублёвого кошелька `qw_wallet_rub`;
- наличие баланса;
- `balance.amount` является числом;
- `balance.amount > 0`;
- валюта баланса равна `643`.

### 3. Создание платежа на 1 рубль

```http
POST /sinap/api/v2/terms/99/payments
```

Проверяется:

- статус ответа `200 OK`;
- id платежа в ответе совпадает с id из запроса;
- сумма платежа равна `1`;
- валюта равна `643`;
- получатель совпадает с переданным в запросе;
- есть объект `transaction`;
- есть `transaction.id`;
- `transaction.state.code = Accepted`.

### 4. Исполнение платежа

Проверяется:

- созданный ранее `payment_id` сохранён;
- `transaction_id` сохранён;
- история платежей возвращает массив `data`;
- созданный платёж находится в истории по `transaction_id` или `payment_id`;
- сумма платежа равна `1`;
- валюта равна `643`.

## Установка и запуск Pytest-тестов

### 1. Создать виртуальное окружение

```bash
python -m venv .venv
```

### 2. Активировать окружение

Windows PowerShell:

```powershell
.\.venv\Scripts\activatee
```

### 3. Установить зависимости

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Создать `.env`

Скопировать `.env.example` в `.env`:

Windows PowerShell:

```powershell
copy .env.example .env
```

Заполнить при наличии реальных данных:

```env
BASE_URL=https://edge.qiwi.com
QIWI_WALLET=79999999999
QIWI_RECEIVER_WALLET=+79999999999
QIWI_TOKEN=PLACEHOLDER_TOKEN
```

### 5. Запустить тесты

```bash
pytest -v
```

Или с подробным выводом ошибок:

```bash
pytest -v -s
```

## Запуск Postman-коллекции

1. Открыть Postman.
2. Нажать `Import`.
3. Импортировать файл `postman/qiwi-wallet-tests.postman_collection.json`.
4. Импортировать файл `postman/qiwi-wallet-local.postman_environment.json`.
5. Выбрать environment `QIWI Wallet Local`.
6. Запустить запросы вручную или через Collection Runner.

## Ожидаемое поведение без реальных данных

Тесты падают с ошибкой авторизации `401 Unauthorized`, либо с ошибкой недоступности сервиса, так как нет токена, вместо него заглушка `QIWI_TOKEN=PLACEHOLDER_TOKEN`.
Это ожидаемо, потому что по условию задания сервис не является рабочим, а реальные токены не предоставлены.
