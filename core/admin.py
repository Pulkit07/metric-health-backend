from django.contrib import admin
from watch_sdk.models import WatchConnection,UserApp

# Register your models here.
admin.site.register(WatchConnection)
admin.site.register(UserApp)
