import os
from azure.communication.email import EmailClient
from celery import shared_task
from watch_sdk.models import PendingUserInvitation, User, UserApp

connection_string = os.getenv("AZURE_COMMUNICATION_SERVICES_CONNECTION_STRING")
client = EmailClient.from_connection_string(connection_string)

welcome_user_email_body = """
Dear {name},

Thank you for signing up for Metric! I am excited to have you on board and look forward to supporting your journey toward better health and fitness.

Our admin panel is under development and you might face issues while using it. Feel free to react out to me with any support or feature requests. Also, I will love to understand your use case and make sure we deliver what's required.

How about we jump on a call to discuss your use case and how we can help you? You can schedule a call with me here: https://calendly.com/metric-health/intro

Best regards,
Pulkit Goyal
Founder, Metric Health
"""


@shared_task
def send_email_on_webhook_error(
    app_id, platform, user_uuid, response, status_code, occurence_time
):
    app = UserApp.objects.get(id=app_id)
    access_users = app.access_users.all().values_list("email", flat=True)
    subject = f"[Metric Backend] Error while sending data to webhook"
    to = [app.user.email, *access_users]
    body = f"""
Dear {app.name} team,

We have received an error while sending data to your webhook. Please check your webhook and make sure it is working correctly.

Platform: {platform}
User UUID: {user_uuid}
Response: {response}
Ocurrence Time: {occurence_time}
Status Code: {status_code}
Webhook Url: {app.webhook_url}

If you feel that the request was processed correctly, please make sure that you return a 200 status code.
You can reach out to us at contact@metric.health or reply to this email if you have any questions.

Regards,
Metric Health Team
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
        subject="[Metric Backend] New user has joined the platform",
        body=f"New user has been created: {user.email} {user.email} {user.company_name} {user.country}",
    )

    send_email.apply_async(
        kwargs={
            "to": (user.email,),
            "subject": "Let's build a healthier world together!",
            "body": welcome_user_email_body.format(name=user.name),
            "senderEmail": os.getenv("AZURE_COMMUNICATION_SERVICES_ADMIN_SENDER_EMAIL"),
        },
        countdown=300,
    )


@shared_task
def send_email_on_new_app(user_app_id):
    app = UserApp.objects.get(id=user_app_id)
    send_email.delay(
        to=(os.getenv("ADMIN_EMAIL_ADDRESS"),),
        subject="[Metric Backend] New app has been created",
        body=f"New app {app.name} has been created by {app.user.email}",
    )


@shared_task
def send_email(to, subject, body, cc=None, senderEmail=None):
    message = {
        "content": {
            "subject": subject,
            "plainText": body,
        },
        "recipients": {
            "to": [{"address": t, "displayName": t} for t in to],
            "cc": [] if cc is None else [{"address": c, "displayName": c} for c in cc],
        },
        "senderAddress": senderEmail
        if senderEmail
        else os.getenv("AZURE_COMMUNICATION_SERVICES_SENDER_EMAIL"),
    }

    poller = client.begin_send(message)
    result = poller.result()


@shared_task
def send_email_on_new_invitation(invitation_id):
    invitation = PendingUserInvitation.objects.get(id=invitation_id)
    invitee_name = invitation.invited_by.name
    send_email.delay(
        to=(invitation.email,),
        subject=f"Invitation to join {invitation.app.name}",
        body=f"""
Dear {invitation.name},

You have been invited to join {invitation.app.name} by {invitee_name}.
Please go to app.metric.health and sign up to join.

Regards,
Metric Health Team""",
    )


@shared_task
def send_email_on_webhook_disabled(app_id, webhook_url):
    app = UserApp.objects.get(id=app_id)
    access_users = app.access_users.all().values_list("email", flat=True)
    subject = f"[Metric Backend] Webhook disabled due to 5 consecutive errors"
    to = [app.user.email, *access_users]
    body = f"""
Dear {app.name} team,

We have disabled your webhook due to 5 consecutive errors. Please check your webhook and make sure it is working correctly.

Webhook Url: {webhook_url}

If you have fixed the issue, you can re-enable the webhook by going to app.metric.health and updating the webhook url.

If you feel that the webhook is working correctly, please make sure that you return a 200 status code.
You can reach out to us at contact@metric.health or reply to this email if you have any questions.

Regards,
Metric Health Team"""
    send_email.delay(
        to=to,
        subject=subject,
        body=body,
        cc=(os.getenv("ADMIN_EMAIL_ADDRESS"),),
    )
