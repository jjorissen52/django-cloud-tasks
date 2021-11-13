import http

from django.contrib.auth import get_user_model
from django.test import Client, LiveServerTestCase
from django.urls import reverse

from cloud_tasks import models, openid
from cloud_tasks.constants import SUCCESS, FAILURE

User = get_user_model()


class TestTaskExecution(LiveServerTestCase):

    def setUp(self) -> None:
        self.client = Client()
        audience = 'http://localhost:8000/'
        token = openid.create_token(audience)
        email = openid.decode_token(token, audience=audience)['email']
        self.service_account = User.objects.create(username=email, email=email)

    def _create_step(self, url, payload, success_pattern, task=None):
        if not task:
            task = models.Task.objects.create(name="Test Task")
        return models.Step.objects.create(
            task=task,
            name=f"Test Step {models.Step.objects.count() + 1}",
            action=f'{self.live_server_url}{url}',
            method="GET",
            payload=payload,
            success_pattern=success_pattern
        )

    def test_step_passes_without_success_pattern(self):
        step = self._create_step(reverse("tasks:test_openid_auth"), None, None)
        success, status, response_dict = step.execute()
        self.assertTrue(success, response_dict)

    def test_step_passes_with_success_pattern(self):
        step = self._create_step(reverse("tasks:test_openid_auth"), None, r'"ok":\s*"You did good\."')
        success, status, response_dict = step.execute()
        self.assertTrue(success, response_dict)

    def test_step_fails_bad_success_pattern(self):
        step = self._create_step(reverse("tasks:test_openid_auth"), None, r'"ok":\s*"You did bad!"')
        success, status, response_dict = step.execute()
        self.assertFalse(success, response_dict)

    def test_step_fails_http_error(self):
        step = self._create_step('/blarg/', None, r'"ok":\s*"You did bad!"')
        success, status, response_dict = step.execute()
        self.assertEqual(status, http.HTTPStatus.NOT_FOUND, "URL should not be available on server.")
        self.assertFalse(success, "Step should have failed.")

    def test_task_succeeds(self):
        task = models.Task.objects.create(name="Test Task")
        step1 = self._create_step(reverse("tasks:test_openid_auth"), None, None, task)
        step2 = self._create_step(reverse("tasks:test_openid_auth"), None, r'"ok":\s*"You did good\."', task)
        task_execution = task.execute()
        self.assertEqual(task_execution.status, SUCCESS, "Both steps should have succeeded.")

    def test_task_fails(self):
        task = models.Task.objects.create(name="Test Task")
        step1 = self._create_step(reverse("tasks:test_openid_auth"), None, None, task)
        step2 = self._create_step('/blarg/', None, r'"ok":\s*"You did bad!"', task)
        task_execution = task.execute()
        self.assertEqual(task_execution.status, FAILURE, "One of the steps should have failed, triggering a failure.")
