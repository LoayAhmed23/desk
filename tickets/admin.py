from django.contrib import admin
from .models import Category, Ticket, Note, ActivityLog


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'created_at']
    search_fields = ['name']


class NoteInline(admin.TabularInline):
    model = Note
    extra = 0
    readonly_fields = ['author', 'created_at']


class ActivityLogInline(admin.TabularInline):
    model = ActivityLog
    extra = 0
    readonly_fields = ['user', 'action', 'timestamp']


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ['request_id', 'title', 'status', 'priority', 'category', 'submitter', 'assigned_to', 'created_at']
    list_filter = ['status', 'priority', 'category']
    search_fields = ['request_id', 'title', 'description']
    readonly_fields = ['request_id', 'created_at', 'updated_at', 'resolved_at']
    inlines = [NoteInline, ActivityLogInline]


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ['ticket', 'author', 'created_at']
    list_filter = ['created_at']


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ['ticket', 'user', 'action', 'timestamp']
    list_filter = ['timestamp']
