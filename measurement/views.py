from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.urls import reverse_lazy
from .models import Measurement
from .forms import MeasurementForm
from django.views.generic.edit import CreateView, UpdateView


class CreateMeasurementView(LoginRequiredMixin, CreateView):
    model = Measurement
    form_class = MeasurementForm
    template_name = "measurement/create_measurement.html"
    success_url = reverse_lazy("products:product_detail")

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, "Measurement Created Successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        # Redirect to the newly created measurement
        return reverse_lazy(
            "measurement:update_measurement", kwargs={"pk": self.object.id}
        )


class UpdateMeasurementView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Measurement
    form_class = MeasurementForm
    template_name = "measurement/update_measurement.html"
    success_url = reverse_lazy("pages:dashboard")

    def get_queryset(self):
        # Override get_queryset to use select_related and filter by user
        return (
            super().get_queryset().select_related("user").filter(user=self.request.user)
        )

    def test_func(self):
        # Cache the object to avoid duplicate queries
        if not hasattr(self, "_measurement_object"):
            self._measurement_object = self.get_object()
        return self._measurement_object.user == self.request.user

    def get_object(self, queryset=None):
        # Cache the object if not already cached
        if not hasattr(self, "_measurement_object"):
            self._measurement_object = super().get_object(queryset)
        return self._measurement_object

    def form_valid(self, form):
        messages.success(self.request, "Measurement Updated Successfully.")
        return super().form_valid(form)

    def handle_no_permission(self):
        messages.error(
            self.request, "You cannot edit measurements that don't belong to you."
        )
        return super().handle_no_permission()
