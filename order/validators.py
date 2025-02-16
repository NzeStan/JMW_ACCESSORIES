from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
import re


validate_phone_number = RegexValidator(
    regex=r"^\d{11}$", message="Phone number must be 11 digits"
)


def validate_state_code(value):
    # Convert to uppercase first
    value = value.upper()

    # Pattern now allows for varying number length
    pattern = r"^[A-Za-z]{2}/\d{2}[A-Za-z]/\d+$"

    if not re.match(pattern, value):
        raise ValidationError(
            "Enter a valid NYSC state code (e.g., AB/22C/1234). "
            "Format: XX/YYB/ZZZZ where XX is state code, YY is year, "
            "B is batch letter, ZZZZ is your number."
        )
    return value
