from django.urls import path
from .views import NyscKitPDFView, SelectNyscKitStateView, NyscTourPDFView, SelectNyscTourStateView, ChurchPDFView, SelectChurchStateView

urlpatterns = [
    path("kit_state_pdf/", NyscKitPDFView.as_view(), name="state_pdf"),
    path(
        "kit_select_state/",
        SelectNyscKitStateView.as_view(),
        name="select_state_nysckit",
    ),
    path("tour_state_pdf/", NyscTourPDFView.as_view(), name="tour_state_pdf"),
    path(
        "tour_select_state/",
        SelectNyscTourStateView.as_view(),
        name="select_state_nystour",
    ),
    path("church_state_pdf/", ChurchPDFView.as_view(), name="church_pdf"),
    path(
        "select_church/",
        SelectChurchStateView.as_view(),
        name="select_state_church",
    ),
]
