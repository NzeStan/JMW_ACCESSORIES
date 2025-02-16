# email_tracking/models.py
from django.db import models


class EmailEvent(models.Model):
    message_id = models.CharField(max_length=100)
    event_type = models.CharField(max_length=50)
    recipient = models.EmailField()
    timestamp = models.DateTimeField()
    raw_data = models.JSONField()

    class Meta:
        indexes = [
            models.Index(fields=["message_id"]),
            models.Index(fields=["event_type"]),
            models.Index(fields=["timestamp"]),
        ]


class Bounce(models.Model):
    email_event = models.OneToOneField(EmailEvent, on_delete=models.CASCADE)
    bounce_type = models.CharField(max_length=50)
    bounce_subtype = models.CharField(max_length=50)


class Complaint(models.Model):
    email_event = models.OneToOneField(EmailEvent, on_delete=models.CASCADE)
    complaint_type = models.CharField(max_length=50, null=True)
    feedback_id = models.CharField(max_length=100, null=True)



