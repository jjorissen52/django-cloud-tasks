from rest_framework import permissions


class DjangoModelPermissionsWithRead(permissions.DjangoModelPermissions):
    perms_map = {
        'GET': ['%(app_label)s.view_%(model_name)s'],
        'OPTIONS': [],
        'HEAD': [],
        'POST': ['%(app_label)s.add_%(model_name)s'],
        'PUT': ['%(app_label)s.change_%(model_name)s'],
        'PATCH': ['%(app_label)s.change_%(model_name)s'],
        'DELETE': ['%(app_label)s.delete_%(model_name)s'],
    }


class IsTimekeeper(permissions.BasePermission):
    message = "Only timekeepers can access this endpoint."

    def has_permission(self, request, view):
        user = request.user
        return user.is_authenticated and user.has_perm('tasks.timekeeper')


class MultiPerm(permissions.BasePermission):
    any_of = ["tasks.timekeeper"]

    @property
    def message(self):
        return f"Users with one of the permissions {self.any_of} can access this endpoint."

    def has_permission(self, request, view):
        user = request.user
        return user.is_authenticated and any(user.has_perm(perm) for perm in self.any_of)


class TaskExecutor(MultiPerm):
    any_of = ["tasks.timekeeper", "tasks.run_taskschedule", "tasks.execute_task"]


class StepExecutor(permissions.BasePermission):
    any_of = ["tasks.timekeeper", "tasks.run_taskschedule", "tasks.execute_task", "tasks.execute_step"]
