
from django.db import models

# a basic user model
class User(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=100)
    phone = models.CharField(max_length=100, blank=True, null=True)
    company_name = models.CharField(max_length=400, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.name

# a basic model for apps that user will create
class App(models.Model):
    name = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    play_store_url = models.CharField(max_length=100, blank=True, null=True)
    app_store_url = models.CharField(max_length=100, blank=True, null=True)
    website = models.CharField(max_length=100, blank=True, null=True)
    webhook_url = models.CharField(max_length=600, blank=True, null=True)

    def __str__(self):
        return self.name