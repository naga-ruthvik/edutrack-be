from celery import shared_task
from django.conf import settings

@shared_task
def process_certificate_verification(name, email):
    print(f"task is successfully received with name as {name}, email as {email}")
    return name