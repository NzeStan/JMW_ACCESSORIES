from django import forms


class CartAddProductForm(forms.Form):
    quantity = forms.TypedChoiceField(
        choices=[(i, str(i)) for i in range(1, 51)],
        coerce=int,
        widget=forms.Select(attrs={"class": "select select-bordered w-full"}),
    )
    override = forms.BooleanField(
        required=False, initial=False, widget=forms.HiddenInput
    )
