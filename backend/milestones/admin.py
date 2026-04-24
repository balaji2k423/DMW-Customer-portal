from django.contrib import admin
from .models import Milestone, Deliverable, SignOff


class DeliverableInline(admin.TabularInline):
    model   = Deliverable
    extra   = 1
    fields  = ['title', 'status', 'due_date', 'file']


class SignOffInline(admin.StackedInline):
    model     = SignOff
    extra     = 0
    fields    = ['signed_by', 'signed_at', 'remarks']
    readonly_fields = ['signed_at']


@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display    = ['title', 'project', 'status', 'planned_date', 'actual_date', 'order', 'is_delayed']
    list_filter     = ['status', 'project']
    search_fields   = ['title', 'description', 'project__name']
    ordering        = ['project', 'order', 'planned_date']
    readonly_fields = ['created_at', 'updated_at']
    inlines         = [DeliverableInline, SignOffInline]

    def is_delayed(self, obj):
        return obj.is_delayed
    is_delayed.boolean = True


@admin.register(Deliverable)
class DeliverableAdmin(admin.ModelAdmin):
    list_display  = ['title', 'milestone', 'status', 'due_date']
    list_filter   = ['status']
    search_fields = ['title', 'milestone__title']


@admin.register(SignOff)
class SignOffAdmin(admin.ModelAdmin):
    list_display  = ['milestone', 'signed_by', 'signed_at']
    search_fields = ['milestone__title', 'signed_by__email']
    readonly_fields = ['signed_at']