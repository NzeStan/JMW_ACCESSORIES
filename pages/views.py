from django.shortcuts import render
from django.views.generic import TemplateView
from measurement.models import Measurement
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Max
from measurement.models import Measurement
from django.utils import timezone
from datetime import timedelta
from .models import Testimonial, VideoMessage
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from .forms import TestimonialForm
from django.shortcuts import get_object_or_404, redirect
import random
from django.contrib import messages
from django.db.models import Q
from django.core.mail import send_mail
from order.models import BaseOrder
from django.utils.decorators import method_decorator
from cached.decorators import monitored_cache_page
import logging


logger = logging.getLogger(__name__)


class HomePageView(TemplateView):
    template_name = "pages/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get all active testimonials in a single query and cache the result
        all_testimonials = list(
            Testimonial.objects.select_related("user")  # Add select_related
            .filter(is_active=True)
            .order_by("created_at")  # Add explicit ordering
        )
        if all_testimonials:
            random.shuffle(all_testimonials)

        # Single query for video message
        video_message = VideoMessage.objects.filter(active=True).first()
        context["video_message"] = video_message or {
            "title": "Watch!!!",
            "video": "https://www.youtube.com/embed/WQ1XaDY5QQQ",
        }

        # Use the cached testimonials list
        context["testimonials"] = all_testimonials[:6]
        context["has_more"] = len(all_testimonials) > 6
        context["remaining_testimonials"] = (
            all_testimonials[6:12] if len(all_testimonials) > 6 else []
        )

        # Optimize authenticated user check
        if self.request.user.is_authenticated:
            # Use the cached testimonials to find user's testimonial
            user_testimonial = next(
                (t for t in all_testimonials if t.user_id == self.request.user.id), None
            )
            context["user_testimonial"] = user_testimonial
            if not user_testimonial:
                context["testimonial_form"] = TestimonialForm()

        return context


@login_required
def create_testimonial(request):
    if request.method == "POST":
        # Check if user already has a testimonial
        existing_testimonial = Testimonial.objects.filter(user=request.user).first()
        if existing_testimonial:
            messages.error(
                request,
                "You already have an active testimonial. Please edit or delete it first.",
            )
            return redirect("pages:home")

        form = TestimonialForm(request.POST)
        if form.is_valid():
            testimonial = form.save(commit=False)
            testimonial.user = request.user
            testimonial.save()
            messages.success(request, "Your testimonial has been successfully created!")
            return redirect("pages:home")
        else:
            messages.error(request, "Please correct the errors below.")

    return redirect("pages:home")


@login_required
def edit_testimonial(request, pk):
    testimonial = get_object_or_404(Testimonial, pk=pk, user=request.user)

    if request.method == "POST":
        form = TestimonialForm(request.POST, instance=testimonial)
        if form.is_valid():
            form.save()
            messages.success(request, "Your testimonial has been updated successfully!")
            return redirect("pages:home")

    form = TestimonialForm(instance=testimonial)
    return render(request, "pages/partials/edit_testimonial.html", {"form": form})


@login_required
def delete_testimonial(request, pk):
    testimonial = get_object_or_404(Testimonial, pk=pk, user=request.user)
    if request.method == "POST":
        testimonial.delete()
        messages.success(request, "Your testimonial has been deleted successfully!")
    return redirect("pages:home")


def toggle_testimonials(request):
    """Handle showing more/less testimonials"""
    show_more = request.GET.get("show_more") == "true"

    # Add select_related to reduce queries
    all_testimonials = list(
        Testimonial.objects.select_related("user")
        .filter(is_active=True)
        .order_by("created_at")
    )
    if all_testimonials:
        random.shuffle(all_testimonials)

    testimonials = all_testimonials[:12] if show_more else all_testimonials[:6]

    context = {"testimonials": testimonials, "show_more": show_more}
    return render(request, "pages/partials/testimonial_list.html", context)


@method_decorator(monitored_cache_page, name="dispatch")
class AboutPageView(TemplateView):
    template_name = "pages/about.html"


class ContactPageView(TemplateView):
    template_name = "pages/contact.html"

    def post(self, request, *args, **kwargs):
        try:
            # Get form data
            name = request.POST.get("name")
            email = request.POST.get("email")
            subject = request.POST.get("subject")
            message = request.POST.get("message")

            # Validate required fields
            if not all([name, email, subject, message]):
                messages.error(request, "All fields are required.")
                return HttpResponse(status=400)

            # Compose email
            email_message = f"""
            New Contact Form Submission:
            
            Name: {name}
            Email: {email}
            Subject: {subject}
            Message: {message}
            """

            # Send email
            send_mail(
                subject=f"Contact Form: {subject}",
                message=email_message,
                from_email=email,
                recipient_list=["contact@jumemegawears.com"],
                fail_silently=False,
            )

            messages.success(request, "Message sent successfully!")
            return HttpResponse(status=204)

        except Exception as e:
            # Log the error for debugging
            logger.error(f"Contact form error: {str(e)}")
            messages.error(request, "Failed to send message. Please try again.")
            return HttpResponse(status=400)


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "pages/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user_measurement = (
            Measurement.objects.filter(user=self.request.user)
            .select_related("user")
            .order_by("-created_at")
            .first()
        )

        context.update(
            {
                "measurement": user_measurement,
                "has_measurements": user_measurement is not None,
                "measurement_date": (
                    user_measurement.created_at if user_measurement else None
                ),
            }
        )

        if user_measurement:
            time_difference = timezone.now() - user_measurement.created_at
            days = time_difference.days

            # Create a more readable "days ago" text
            if days == 0:
                context["days_since_update"] = "Today"
            elif days == 1:
                context["days_since_update"] = "Yesterday"
            else:
                context["days_since_update"] = f"{days} days ago"

            # Add needs_update flag if measurements are older than 90 days
            context["needs_update"] = time_difference > timedelta(days=90)
            context["order"] = BaseOrder.objects.filter(email=self.request.user.email)

        return context
