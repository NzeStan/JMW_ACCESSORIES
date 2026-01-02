from django.urls import path
from .views import NyscKitPDFView, NyscTourPDFView, ChurchPDFView

urlpatterns = [
    path("kit_state_pdf/", NyscKitPDFView.as_view(), name="state_pdf"),
    path("tour_state_pdf/", NyscTourPDFView.as_view(), name="tour_state_pdf"),
    path("church_state_pdf/", ChurchPDFView.as_view(), name="church_pdf"),
]
