from django.contrib import admin

from . import models

# Register your models here.

admin.site.register(models.ContentCategory)
admin.site.register(models.Content)

