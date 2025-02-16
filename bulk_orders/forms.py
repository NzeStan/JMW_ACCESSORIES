# bulk_orders/forms.py
from django import forms
from .models import BulkOrderLink, OrderEntry
from django.utils import timezone
import pytz

class BulkOrderLinkForm(forms.ModelForm):

    def clean_payment_deadline(self):
        payment_deadline = self.cleaned_data.get("payment_deadline")
        lagos_tz = pytz.timezone("Africa/Lagos")
        now = timezone.now().astimezone(lagos_tz)

        # Convert payment_deadline to Lagos timezone if it's not already timezone-aware
        if payment_deadline and not timezone.is_aware(payment_deadline):
            payment_deadline = lagos_tz.localize(payment_deadline)

        if payment_deadline and payment_deadline <= now:
            raise forms.ValidationError("Payment deadline must be in the future.")

        return payment_deadline

    class Meta:
        model = BulkOrderLink
        fields = [
            "organization_name",
            "price_per_item",
            "custom_branding_enabled",
            "payment_deadline",
        ]
        widgets = {
            "organization_name": forms.TextInput(
                attrs={
                    "class": "input input-bordered w-full",
                    "placeholder": "Enter organization name",
                }
            ),
            "price_per_item": forms.NumberInput(
                attrs={
                    "class": "input input-bordered w-full",
                    "min": "0",
                    "step": "0.01",
                }
            ),
            "payment_deadline": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local",
                    "class": "input input-bordered w-full",
                    "min": timezone.now().strftime(
                        "%Y-%m-%dT%H:%M"
                    ),  # Set minimum date to now
                }
            ),
            "custom_branding_enabled": forms.CheckboxInput(attrs={"class": "checkbox"}),
        }


class OrderEntryForm(forms.ModelForm):
    use_coupon = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": "checkbox checkbox-primary",
                "hx-get": "/bulk_orders/toggle-coupon/",
                "hx-target": "#coupon-field",
                "hx-swap": "outerHTML",
                "hx-trigger": "change",
                "hx-include": "this",
            }
        ),
    )
    coupon_code = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "input input-bordered w-full hidden",
                "placeholder": "Enter coupon code",
            }
        ),
    )

    class Meta:
        model = OrderEntry
        fields = ["email", "full_name", "size", "custom_name"]
        widgets = {
            "email": forms.EmailInput(
                attrs={
                    "class": "input input-bordered w-full",
                    "placeholder": "Enter your email",
                }
            ),
            "full_name": forms.TextInput(
                attrs={
                    "class": "input input-bordered w-full",
                    "placeholder": "Enter your full name",
                }
            ),
            "size": forms.Select(attrs={"class": "select select-bordered w-full"}),
            "custom_name": forms.TextInput(
                attrs={
                    "class": "input input-bordered w-full",
                    "placeholder": "Enter name for branding",
                }
            ),
        }
