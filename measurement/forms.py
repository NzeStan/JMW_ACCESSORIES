from django import forms
from .models import Measurement
from decimal import Decimal, InvalidOperation


class MeasurementForm(forms.ModelForm):
    class Meta:
        model = Measurement
        exclude = ["user", "created_at", "updated_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            # Create a more readable label by replacing underscores with spaces
            field.label = field_name.replace("_", " ").title()
            field.widget.attrs.update(
                {
                    "class": "input input-bordered w-full",
                    "placeholder": "0.00",
                    "step": "0.25",  # Allows quarter-inch increments
                }
            )

    def clean(self):
        cleaned_data = super().clean()
        for field_name, value in cleaned_data.items():
            if isinstance(value, str) and value.strip():
                try:
                    # Remove any spaces
                    value = value.replace(" ", "")

                    # Handle fractions like "32 1/2" or "32-1/2"
                    if "/" in value:
                        if "-" in value or " " in value:
                            whole, fraction = value.replace("-", " ").split()
                            num, denom = fraction.split("/")
                            value = float(whole) + float(num) / float(denom)
                        else:
                            num, denom = value.split("/")
                            value = float(num) / float(denom)

                    # Convert to Decimal with 2 decimal places
                    cleaned_data[field_name] = Decimal(str(float(value))).quantize(
                        Decimal("0.01")
                    )

                except (ValueError, InvalidOperation):
                    self.add_error(
                        field_name,
                        "Please enter a valid measurement (e.g., 32.5 or 32 1/2)",
                    )

        return cleaned_data
