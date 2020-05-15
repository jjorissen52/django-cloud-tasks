from django.contrib import admin
from django.contrib.admin import register
from django.urls import reverse
from django.utils.html import format_html

from tasks.models import Clock, TaskExecution, TaskSchedule, Task, Step
from tasks.constants import START, RUNNING, PAUSE, PAUSED, FIX, BROKEN, UNKNOWN


@register(Step)
class StepAdmin(admin.ModelAdmin):
    list_display = ('name', 'task', 'action', 'success_pattern',)


class StepInline(admin.TabularInline):
    model = Step


@register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('name', )
    inlines = (
        StepInline,
    )


@register(TaskSchedule)
class TaskScheduleAdmin(admin.ModelAdmin):
    list_display = ('name', 'task', 'clock', 'enabled', 'clock_active', 'active')


class TaskScheduleInline(admin.TabularInline):
    model = TaskSchedule


@register(Clock)
class ClockAdmin(admin.ModelAdmin):
    list_display = ('name', 'cron', 'management', 'status_info', '_actions')
    fieldsets = (
        (None, {
            'fields': ('name', 'cron', 'management')
        }),
        ('Metadata', {
            'fields': ('gcp_name', )
        })
    )

    inlines = (
        TaskScheduleInline,
    )

    def get_readonly_fields(self, request, obj=None):
        return ['gcp_name']

    def get_actions(self, request):
        actions = super().get_actions(request)
        # prevent user from using bulk delete, which circumvents Clock.delete()
        del actions['delete_selected']
        return actions

    def _actions(self, obj):
        if obj.status == RUNNING:
            action = PAUSE
        elif obj.status == PAUSED:
            action = START
        elif obj.status == BROKEN:
            action = FIX
        elif obj.status == UNKNOWN:
            raise NotImplementedError("Handle the case where we do not want to create clock on enable")
        else:
            assert False, f"Status must be one of {tuple(Clock._status_choices.keys())}, got {obj.status}"
        url = reverse("tasks:clock_actions", kwargs={'pk': obj.id, 'action': action})
        return format_html(
            """
            <!-- Don't want to use GET, but format_html removes form. -->
            <a href="{url}" class="button">{text}</a>
            """,
            url=url, text=action.title())

    _actions.allow_tags = True
    _actions.short_description = 'Actions'


@register(TaskExecution)
class TaskExecutionAdmin(admin.ModelAdmin):
    list_display = ('task', 'status', )
