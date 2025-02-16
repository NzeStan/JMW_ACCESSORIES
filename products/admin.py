from django.contrib import admin
from django.utils.text import slugify
from django import forms
from .models import Category, NyscKit, NyscTour, Church
from .constants import (
    NYSC_KIT_PRODUCT_NAME,
    STATES,
    CHURCH_PRODUCT_NAME,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "product_type"]
    list_filter = ["product_type"]
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ["name", "description"]


class BaseProductAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "price", "available", "out_of_stock", "created"]
    list_filter = ["available", "out_of_stock", "created", "updated"]
    list_editable = ["price", "available", "out_of_stock"]
    search_fields = ["name", "description"]
    date_hierarchy = "created"
    readonly_fields = ["created", "updated"]

    def get_fields(self, request, obj=None):
        if obj:
            return [
                "name",
                "slug",
                "category",
                "description",
                "price",
                "image",
                "image_1",
                "image_2",
                "image_3",
                "available",
                "out_of_stock",
                "created",
                "updated",
            ]
        return [
            "name",
            "category",
            "description",
            "price",
            "image",
            "image_1",
            "image_2",
            "image_3",
            "available",
            "out_of_stock",
        ]

    def get_readonly_fields(self, request, obj=None):
        fields = list(self.readonly_fields)
        if obj:  # editing existing object
            fields.append("slug")
        return fields


@admin.register(NyscKit)
class NyscTourAdmin(BaseProductAdmin):
    list_display = BaseProductAdmin.list_display + [
        "type",
        "slug",
    ]
    list_filter = BaseProductAdmin.list_filter

    def get_fields(self, request, obj=None):
        base_fields = super().get_fields(request, obj)
        return base_fields + ["type"]

    def formfield_for_dbfield(self, db_field, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, **kwargs)
        if db_field.name == "name":
            formfield.widget = forms.Select(choices=NYSC_KIT_PRODUCT_NAME)
        return formfield


@admin.register(NyscTour)
class NyscTourAdmin(BaseProductAdmin):
    list_display = BaseProductAdmin.list_display + [
        "slug",
    ]
    list_filter = BaseProductAdmin.list_filter

    def get_fields(self, request, obj=None):
        base_fields = super().get_fields(request, obj)
        return base_fields

    def formfield_for_dbfield(self, db_field, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, **kwargs)
        if db_field.name == "name":
            formfield.widget = forms.Select(choices=STATES)
        return formfield


@admin.register(Church)
class ChurchAdmin(BaseProductAdmin):
    list_display = BaseProductAdmin.list_display + [
        "church",
        "slug",
    ]
    list_filter = BaseProductAdmin.list_filter + ["church"]

    def get_fields(self, request, obj=None):
        base_fields = super().get_fields(request, obj)
        return base_fields + ["church"]

    def formfield_for_dbfield(self, db_field, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, **kwargs)
        if db_field.name == "name":
            formfield.widget = forms.Select(choices=CHURCH_PRODUCT_NAME)
        return formfield
