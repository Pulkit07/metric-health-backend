import os
from azure.communication.email import EmailClient
from celery import shared_task
from watch_sdk.models import User, UserApp

connection_string = os.getenv("AZURE_COMMUNICATION_SERVICES_CONNECTION_STRING")
client = EmailClient.from_connection_string(connection_string)


@shared_task
def send_email_on_webhook_error(
    app_id, platform, user_uuid, fitness_data, response, status_code
):
    app = UserApp.objects.get(id=app_id)
    subject = f"[HEKA BACKEND] Webhook error for {app.name}: Received {status_code} from {app.webhook_url}"
    to = (app_id.user.email,)
    body = f"""
    Dear {app.user.name},

    We have received an error from your webhook. Please check your webhook and make sure it is working correctly.

    <p>Webhook error for {app.name}:</p>
    <p>Received {status_code} from {app.webhook_url}</p>
    <p>Platform: {platform}</p>
    <p>User UUID: {user_uuid}</p>
    <p>Fitness data: {fitness_data}</p>
    <p>Response: {response}</p>

    If you feel that the request was processed correctly, please make sure that you return a 200 status code.
    You can reach out to us at contact@hekahealth.co or reply to this email if you have any questions.

    Regards,
    Heka Team
    """
    send_email.delay(
        to=to,
        subject=subject,
        body=body,
        cc=(os.getenv("ADMIN_EMAIL_ADDRESS"),),
    )


@shared_task
def send_email_on_new_user(user_id):
    user = User.objects.get(id=user_id)
    send_email.delay(
        to=(os.getenv("ADMIN_EMAIL_ADDRESS"),),
        subject="[HEKA BACKEND] New user has joined the platform",
        body=f"New user has been created: {user.email} {user.email} {user.company_name} {user.country}",
    )


@shared_task
def send_email_on_new_app(user_app_id):
    app = UserApp.objects.get(id=user_app_id)
    send_email.delay(
        to=(os.getenv("ADMIN_EMAIL_ADDRESS"),),
        subject="[HEKA BACKEND] New app has been created",
        body=f"New app {app.name} has been created by {app.user.email}",
    )


@shared_task
def send_email(to, subject, body, cc=None):
    message = {
        "content": {
            "subject": subject,
            "plainText": body,
            "html": body,
        },
        "recipients": {
            "to": [{"address": t, "displayName": t} for t in to],
            "cc": [] if cc is None else [{"address": c, "displayName": c} for c in cc],
        },
        "senderAddress": os.getenv("AZURE_COMMUNICATION_SERVICES_SENDER_EMAIL"),
    }

    poller = client.begin_send(message)
    result = poller.result()
