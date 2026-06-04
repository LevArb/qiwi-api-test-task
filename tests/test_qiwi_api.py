import os
import time
from typing import Any, Dict

import pytest
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("BASE_URL", "https://edge.qiwi.com")
QIWI_WALLET = os.getenv("QIWI_WALLET", "79999999999")
QIWI_RECEIVER_WALLET = os.getenv("QIWI_RECEIVER_WALLET", "+79999999999")
QIWI_TOKEN = os.getenv("QIWI_TOKEN", "PLACEHOLDER_TOKEN")


@pytest.fixture(scope="session")
def auth_headers() -> Dict[str, str]:
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {QIWI_TOKEN}",
    }


@pytest.fixture(scope="session")
def payment_context() -> Dict[str, Any]:
    """Shared context for payment creation and execution checks."""
    return {}


def assert_json_response(response: requests.Response) -> Any:
    content_type = response.headers.get("Content-Type", "")
    assert "application/json" in content_type, (
        f"Expected JSON response, got Content-Type: {content_type}"
    )
    return response.json()


def test_service_availability_by_payment_history_contract(auth_headers: Dict[str, str]) -> None:
    """
    Проверка доступности сервиса через бизнес-метод истории платежей.
    Если сервис доступен и работает по контракту, он должен вернуть JSON
    с полем data, где data является массивом. rows=1 ограничивает количество
    элементов в ответе.
    """
    response = requests.get(
        f"{BASE_URL}/payment-history/v2/persons/{QIWI_WALLET}/payments",
        headers=auth_headers,
        params={"rows": 1},
        timeout=15,
    )

    assert response.status_code == 200, (
        f"Expected 200 OK, got {response.status_code}. Response: {response.text}"
    )

    body = assert_json_response(response)

    assert "data" in body, "Response should contain 'data' field"
    assert isinstance(body["data"], list), "'data' should be a list"
    assert len(body["data"]) <= 1, "'data' length should not exceed rows=1"


def test_balance_should_be_greater_than_zero(auth_headers: Dict[str, str]) -> None:
    """
    Проверка баланса.
    Ключевое условие тестового задания: баланс всегда должен быть больше 0.
    Дополнительно проверяется наличие рублёвого кошелька и валюта 643.
    """
    response = requests.get(
        f"{BASE_URL}/funding-sources/v2/persons/{QIWI_WALLET}/accounts",
        headers=auth_headers,
        timeout=15,
    )

    assert response.status_code == 200, (
        f"Expected 200 OK, got {response.status_code}. Response: {response.text}"
    )

    body = assert_json_response(response)

    assert "accounts" in body, "Response should contain 'accounts' field"
    assert isinstance(body["accounts"], list), "'accounts' should be a list"

    rub_wallet = next(
        (account for account in body["accounts"] if account.get("alias") == "qw_wallet_rub"),
        None,
    )

    assert rub_wallet is not None, "RUB wallet account with alias 'qw_wallet_rub' should exist"
    assert rub_wallet.get("hasBalance") is True, "RUB wallet should have balance"
    assert rub_wallet.get("balance") is not None, "Balance object should not be null"

    balance = rub_wallet["balance"]

    assert isinstance(balance.get("amount"), (int, float)), "Balance amount should be a number"
    assert balance["amount"] > 0, "Balance amount should be greater than 0"
    assert str(balance.get("currency")) == "643", "Balance currency should be RUB / 643"


def test_create_payment_for_one_ruble(
    auth_headers: Dict[str, str],
    payment_context: Dict[str, Any],
) -> None:
    """
    Создание платежа на сумму 1 рубль.
    Платёж создаётся с уникальным id. После успешного ответа проверяется,
    что API вернул тот же id, сумму 1 RUB, получателя и состояние Accepted.
    """
    payment_id = str(int(time.time() * 1000))

    payload = {
        "id": payment_id,
        "sum": {
            "amount": 1,
            "currency": "643",
        },
        "paymentMethod": {
            "type": "Account",
            "accountId": "643",
        },
        "comment": "Test payment 1 RUB",
        "fields": {
            "account": QIWI_RECEIVER_WALLET,
        },
    }

    response = requests.post(
        f"{BASE_URL}/sinap/api/v2/terms/99/payments",
        headers=auth_headers,
        json=payload,
        timeout=15,
    )

    assert response.status_code == 200, (
        f"Expected 200 OK, got {response.status_code}. Response: {response.text}"
    )

    body = assert_json_response(response)

    assert str(body.get("id")) == payment_id, "Response payment id should match request id"
    assert float(body.get("sum", {}).get("amount")) == 1, "Payment amount should be 1"
    assert str(body.get("sum", {}).get("currency")) == "643", "Payment currency should be RUB / 643"
    assert body.get("fields", {}).get("account") == QIWI_RECEIVER_WALLET, (
        "Receiver wallet should match request payload"
    )
    assert body.get("transaction") is not None, "Response should contain transaction object"
    assert body["transaction"].get("id"), "Transaction id should exist"
    assert body["transaction"].get("state", {}).get("code") == "Accepted", (
        "Payment should be accepted by processing"
    )

    payment_context["payment_id"] = payment_id
    payment_context["transaction_id"] = body["transaction"]["id"]


def test_created_payment_should_be_available_in_payment_history(
    auth_headers: Dict[str, str],
    payment_context: Dict[str, Any],
) -> None:
    """
    Проверка исполнения созданного платежа.
    Под исполнением здесь понимается проверка, что созданный платёж был принят
    процессингом и доступен в истории платежей.
    """
    payment_id = payment_context.get("payment_id")
    transaction_id = payment_context.get("transaction_id")

    assert payment_id, "Payment id should be saved from create payment test"
    assert transaction_id, "Transaction id should be saved from create payment test"

    response = requests.get(
        f"{BASE_URL}/payment-history/v2/persons/{QIWI_WALLET}/payments",
        headers=auth_headers,
        params={"rows": 50, "operation": "OUT"},
        timeout=15,
    )

    assert response.status_code == 200, (
        f"Expected 200 OK, got {response.status_code}. Response: {response.text}"
    )

    body = assert_json_response(response)

    assert "data" in body, "Response should contain 'data' field"
    assert isinstance(body["data"], list), "'data' should be a list"

    payment = next(
        (
            item
            for item in body["data"]
            if str(item.get("txnId")) == str(transaction_id)
            or str(item.get("id")) == str(payment_id)
        ),
        None,
    )

    assert payment is not None, "Created payment should be found in payment history"
    assert float(payment.get("sum", {}).get("amount")) == 1, "Payment amount should be 1"
    assert str(payment.get("sum", {}).get("currency")) == "643", "Payment currency should be RUB / 643"
