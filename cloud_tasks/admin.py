import json

from pygments import highlight
from pygments.formatters.html import HtmlFormatter
from pygments.lexers.data import JsonLexer

from django.contrib import admin, messages
from django.contrib.admin import register
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from cloud_tasks.models import Clock, TaskExecution, TaskSchedule, Task, Step
from cloud_tasks.constants import \
    RUNNING, PAUSED, BROKEN, UNKNOWN, \
    START, PAUSE, FIX, SYNC, \
    GCP, MANUAL


@register(Step)
class StepAdmin(admin.ModelAdmin):
    list_display = ('name', 'task', 'action', 'success_pattern',)


class StepInline(admin.TabularInline):
    model = Step


@register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('name', '_actions')
    inlines = (
        StepInline,
    )

    def _actions(self, obj):
        url = reverse("cloud_tasks:task_execute", kwargs={'pk': obj.id})
        return format_html('<a href="{url}" class="button">Execute</a>', url=url)

    _actions.allow_tags = True
    _actions.short_description = 'Actions'


@register(TaskSchedule)
class TaskScheduleAdmin(admin.ModelAdmin):
    list_display = ('name', 'task', 'clock', 'enabled', 'status', '_actions')

    def _actions(self, obj):
        url = reverse("cloud_tasks:taskschedule_run", kwargs={'pk': obj.id})
        return format_html('<a href="{url}" class="button">Run</a>', url=url)

    _actions.allow_tags = True
    _actions.short_description = 'Actions'


class TaskScheduleInline(admin.TabularInline):
    model = TaskSchedule


@register(Clock)
class ClockAdmin(admin.ModelAdmin):
    list_display = ('name', 'timezone', 'cron', 'management', 'status_info', '_actions')
    fieldsets = (
        (None, {
            'fields': ('name', 'timezone', 'cron', 'management', 'status', )
        }),
        ('Metadata', {
            'fields': ('gcp_name', 'gcp_service_account', )
        })
    )

    inlines = (
        TaskScheduleInline,
    )

    actions = ['sync_selected', ]

    def get_readonly_fields(self, request, obj=None):
        if not obj or obj.management != MANUAL:
            return ['status', 'gcp_name', 'gcp_service_account', ]
        return tuple()

    def sync_selected(self, request, queryset):
        for clock in queryset:
            success, message = clock.sync_clock()
            messages.success(request, message) if success else messages.error(request, message)

    def get_actions(self, request):
        actions = super().get_actions(request)
        # prevent user from using bulk delete, which circumvents Clock.delete()
        if 'delete_selected' in actions:
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
            action = SYNC
        else:
            assert False, f"Status must be one of {tuple(Clock._status_choices.keys())}, got {obj.status}"
        action_html = format_html('')
        if obj.status != UNKNOWN:
            action_html += format_html(
                '<a href="{url}" class="button">{text}</a>&nbsp;',
                url=reverse("cloud_tasks:clock_actions", kwargs={'pk': obj.id, 'action': action}),
                text=action.title()
            )
        action_html += format_html(
            '<a href="{url}" class="button">{text}</a>',
            url=reverse("cloud_tasks:clock_actions", kwargs={'pk': obj.id, 'action': SYNC}),
            text=SYNC.title()
        )
        return action_html

    _actions.allow_tags = True
    _actions.short_description = 'Actions'


@register(TaskExecution)
class TaskExecutionAdmin(admin.ModelAdmin):
    list_display = ('task', 'status', 'queued_time', 'start_time', 'finish_time', )
    exclude = ('results', )
    readonly_fields = ('task', 'status', 'execution_result', 'queued_time', 'start_time', 'finish_time')

    @staticmethod
    def execution_result(obj):
        _results = json.dumps(obj.results, indent=2)
        # limit the size of the output to 3000 lines
        _results = '\n'.join(_results.split('\n')[:3000])
        html_formatter = HtmlFormatter(style='friendly')
        _results = highlight(_results, JsonLexer(), html_formatter)
        return mark_safe(f'<style>{html_formatter.get_style_defs()}</style></br>{_results}')

    execution_result.short_description = 'Task Execution Results'
