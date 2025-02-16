from django.urls import path
from .views import CreateMeasurementView, UpdateMeasurementView

app_name = "measurement"

urlpatterns = [
    path(
        "create/",
        CreateMeasurementView.as_view(),
        name="create_measurement",
    ),
    path(
        "update/<uuid:pk>/", 
        UpdateMeasurementView.as_view(),
        name="update_measurement",
    ),
]
