import json
import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def get_paystack_keys():
    if settings.DEBUG:
        return settings.PAYSTACK_TEST_SECRET_KEY, settings.PAYSTACK_TEST_PUBLIC_KEY
    return settings.PAYSTACK_LIVE_SECRET_KEY, settings.PAYSTACK_LIVE_PUBLIC_KEY


def initialize_payment(amount, email, reference, callback_url, metadata=None):
    secret_key, _ = get_paystack_keys()

    url = "https://api.paystack.co/transaction/initialize"
    headers = {
        "Authorization": f"Bearer {secret_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "amount": int(amount * 100),  # Convert to kobo
        "email": email,
        "reference": reference,
        "callback_url": callback_url,
        "metadata": metadata or {},
    }

    logger.info(
        f"Initializing Paystack payment with payload: {json.dumps(payload, indent=2)}"
    )

    try:
        response = requests.post(url, headers=headers, json=payload)
        response_data = response.json()
        logger.info(f"Paystack response: {json.dumps(response_data, indent=2)}")

        if not response.ok:
            logger.error(
                f"Paystack error: {response_data.get('message', 'Unknown error')}"
            )
            return None

        return response_data

    except Exception as e:
        logger.error(f"Error initializing Paystack payment: {str(e)}")
        return None


def verify_payment(reference):
    secret_key, _ = get_paystack_keys()

    url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {
        "Authorization": f"Bearer {secret_key}",
        "Content-Type": "application/json",
    }

    response = requests.get(url, headers=headers)
    return response.json()
