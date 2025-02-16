# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from .models import PaymentTransaction
# from order.utils import generate_receipt_pdf, send_receipt_email
# import logging

# logger = logging.getLogger(__name__)


# @receiver(post_save, sender=PaymentTransaction)
# def handle_successful_payment(sender, instance, created, **kwargs):
#     """
#     Handle successful payment by generating and sending receipt
#     when payment status changes to 'success'
#     """
#     if not created and instance.status == "success":
#         try:
#             # Generate and send receipt
#             pdf = generate_receipt_pdf(instance.orders.all(), instance)
#             send_receipt_email(instance.email, pdf, instance.reference)

#             logger.info(f"Receipt sent for payment {instance.reference}")
#         except Exception as e:
#             logger.error(
#                 f"Error sending receipt for payment {instance.reference}: {str(e)}"
#             )
