from django.contrib import admin
from .models import {{ agent_name_camel }}Request, {{ agent_name_camel }}Response


@admin.register({{ agent_name_camel }}Request)
class {{ agent_name_camel }}RequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'status', 'created_at', 'cost']
    list_filter = ['status', 'created_at']
    search_fields = ['user__email', 'user__username']
    readonly_fields = ['id', 'created_at', 'processed_at']
    ordering = ['-created_at']


@admin.register({{ agent_name_camel }}Response)
class {{ agent_name_camel }}ResponseAdmin(admin.ModelAdmin):
    list_display = ['id', 'request', 'success', 'created_at']
    list_filter = ['success', 'created_at']
    readonly_fields = ['id', 'created_at']
    ordering = ['-created_at']