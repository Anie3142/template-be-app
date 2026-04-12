from django.contrib import admin

from .models import ExampleChild, ExampleParent

admin.site.register(ExampleParent)
admin.site.register(ExampleChild)
