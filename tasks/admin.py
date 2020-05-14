from django.contrib import admin
from django.contrib.admin import register

from tasks.models import Clock, TaskExecution, TaskSchedule, Task, Step


@register(Step)
class StepAdmin(admin.ModelAdmin):
    list_display = ('task', 'name', 'action', 'success_pattern',)

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
    list_display = ('name', 'cron', 'enabled', 'management', )
    inlines = (
        TaskScheduleInline,
    )

@register(TaskExecution)
class TaskExecutionAdmin(admin.ModelAdmin):
    list_display = ('task', 'status', )
