from django.contrib import admin

# Register your models here.
from watch_sdk.models import *

admin.site.register(User)
admin.site.register(UserApp)