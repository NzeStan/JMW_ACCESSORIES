# forms.py
from django import forms
from .models import BaseOrder, NyscKitOrder, ChurchOrder, NyscTourOrder
from products.constants import STATES


class BaseOrderForm(forms.ModelForm):
    class Meta:
        model = BaseOrder
        fields = ["first_name", "middle_name", "last_name", "phone_number"]
        widgets = {
            "first_name": forms.TextInput(
                attrs={"class": "input input-bordered w-full"}
            ),
            "middle_name": forms.TextInput(
                attrs={"class": "input input-bordered w-full"}
            ),
            "last_name": forms.TextInput(
                attrs={"class": "input input-bordered w-full"}
            ),
            "phone_number": forms.TextInput(
                attrs={
                    "class": "input input-bordered w-full",
                    "placeholder": "08012345678",
                }
            ),
        }


class NyscKitOrderForm(forms.ModelForm):
    class Meta:
        model = NyscKitOrder
        fields = ["state_code", "state", "local_government"]
        widgets = {
            "state_code": forms.TextInput(
                attrs={
                    "class": "input input-bordered w-full uppercase",
                    "placeholder": "AB/22C/1234",
                }
            ),
            "state": forms.Select(attrs={"class": "select select-bordered w-full"}),
            "local_government": forms.Select(
                attrs={"class": "select select-bordered w-full"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Use the imported STATES directly, not as a class attribute
        self.fields["state"].choices = STATES


class ChurchOrderForm(forms.ModelForm):
    class Meta:
        model = ChurchOrder
        fields = ["pickup_on_camp", "delivery_state", "delivery_lga"]
        widgets = {
            "pickup_on_camp": forms.CheckboxInput(
                attrs={"class": "toggle toggle-primary", "data-delivery-toggle": True}
            ),
            "delivery_state": forms.Select(
                attrs={"class": "select select-bordered w-full", "disabled": True}
            ),
            "delivery_lga": forms.Select(
                attrs={"class": "select select-bordered w-full", "disabled": True}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Use the imported STATES directly instead of accessing it through NyscKitOrderForm
        self.fields["delivery_state"].choices = STATES


class NyscTourOrderForm(forms.ModelForm):
    class Meta:
        model = NyscTourOrder
        fields = []  # No additional fields needed
