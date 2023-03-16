import os
from azure.communication.email import EmailClient
from celery import shared_task
from watch_sdk.models import UserApp

connection_string = os.getenv("AZURE_COMMUNICATION_SERVICES_CONNECTION_STRING")
client = EmailClient.from_connection_string(connection_string)


@shared_task
def send_email_on_new_app(user_app_id):
    app = UserApp.objects.get(id=user_app_id)
    send_email.delay(
        to=os.getenv("ADMIN_EMAIL_ADDRESS"),
        subject="New app",
        body=f"New app has been created by {app.user.email}",
    )


@shared_task
def send_email(to, subject, body):
    message = {
        "content": {
            "subject": subject,
            "plainText": body,
            "html": body,
        },
        "recipients": {
            "to": [
                {
                    "address": to,
                    "displayName": "Watch",
                },
            ],
        },
        "senderAddress": os.getenv("AZURE_COMMUNICATION_SERVICES_SENDER_EMAIL"),
    }

    poller = client.begin_send(message)
    result = poller.result()
