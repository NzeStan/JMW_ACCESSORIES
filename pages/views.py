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
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from django.conf import settings
from smtplib import SMTPException


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
        """Handle contact form submission with comprehensive error handling and validation."""

        try:
            # Get form data with basic cleaning
            name = request.POST.get("name", "").strip()
            email = request.POST.get("email", "").strip().lower()
            subject = request.POST.get("subject", "").strip()
            message = request.POST.get("message", "").strip()

            # Validate required fields
            if not all([name, email, subject, message]):
                messages.error(request, "All fields are required.")
                return HttpResponse(status=400)

            # Validate name length
            if len(name) < 2:
                messages.error(request, "Please enter a valid name.")
                return HttpResponse(status=400)

            # Validate email format
            try:
                validate_email(email)
            except ValidationError:
                messages.error(request, "Please enter a valid email address.")
                return HttpResponse(status=400)

            # Validate message length
            if len(message) < 10:
                messages.error(request, "Message must be at least 10 characters long.")
                return HttpResponse(status=400)

            # Test email connection first
            try:
                connection = get_connection()
                connection.open()
                logger.info("Email connection test successful")
                connection.close()
            except Exception as conn_error:
                logger.error(
                    f"Email connection test failed: {str(conn_error)}", exc_info=True
                )
                messages.error(
                    request,
                    "Unable to connect to email server. Please try again later.",
                )
                return HttpResponse(status=503)

            # Prepare email content
            context = {
                "name": name,
                "email": email,
                "subject": subject,
                "message": message,
            }

            # Create text content
            text_content = f"""
            New Contact Form Submission

            Name: {name}
            Email: {email}
            Subject: {subject}
            Message:
            {message}
            """

            # Create HTML content using template
            html_content = render_to_string("pages/contact_form.html", context)

            try:
                # Create email message
                email_message = EmailMultiAlternatives(
                    subject=f"Contact Form: {subject}",
                    body=text_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[settings.CONTACT_EMAIL],
                    reply_to=[email],
                    headers={"X-Contact-Form": "website"},
                )
                email_message.attach_alternative(html_content, "text/html")

                # Send email
                email_message.send(fail_silently=False)

                logger.info(f"Contact form email sent successfully from {email}")
                messages.success(
                    request, "Message sent successfully! We'll get back to you soon."
                )
                return HttpResponse(status=204)

            except SMTPException as smtp_error:
                logger.error(
                    f"SMTP error while sending contact form: {str(smtp_error)}",
                    exc_info=True,
                )
                messages.error(request, "Failed to send email. Please try again later.")
                return HttpResponse(status=503)

            except ConnectionRefusedError:
                logger.error("Email server connection refused", exc_info=True)
                messages.error(
                    request, "Email server connection failed. Please try again later."
                )
                return HttpResponse(status=503)

            except Exception as email_error:
                logger.error(
                    f"Unexpected error sending contact form email: {str(email_error)}",
                    exc_info=True,
                )
                messages.error(
                    request, "An unexpected error occurred. Please try again later."
                )
                return HttpResponse(status=500)

        except Exception as e:
            logger.error(f"Contact form processing error: {str(e)}", exc_info=True)
            messages.error(request, "Failed to process your request. Please try again.")
            return HttpResponse(status=500)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context["prefilled_email"] = (
                self.request.user.email
            )  # Get logged-in user's email
        return context


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
