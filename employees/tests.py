from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Attendance, Business, BusinessMembership, Employee, WorkSchedule
from .views import _attendance_timing


class AttendanceRulesTests(TestCase):
	def setUp(self):
		self.business = Business.objects.create(name='Acme', timezone='Africa/Nairobi')
		self.schedule = WorkSchedule.objects.create(
			business=self.business,
			timezone='Africa/Nairobi',
			work_start='08:00',
			checkin_window_end='08:30',
			work_end='16:00',
		)

	def test_arrival_inside_window_is_present(self):
		now = datetime(2026, 9, 17, 8, 20, tzinfo=ZoneInfo('Africa/Nairobi'))
		self.assertEqual(_attendance_timing(now, self.schedule), ('Present', 0))

	def test_arrival_after_window_is_late_by_minutes(self):
		now = datetime(2026, 9, 17, 8, 42, tzinfo=ZoneInfo('Africa/Nairobi'))
		self.assertEqual(_attendance_timing(now, self.schedule), ('Late', 12))


class AccessControlTests(TestCase):
	def setUp(self):
		self.manager = User.objects.create_user('manager', password='password')
		self.other_user = User.objects.create_user('other', password='password')
		self.business = Business.objects.create(name='Owned business')
		self.other_business = Business.objects.create(name='Other business')
		BusinessMembership.objects.create(
			user=self.manager, business=self.business, role=BusinessMembership.MANAGER,
		)
		self.employee = Employee.objects.create(
			name='Owned employee', department='Operations', business=self.business,
		)
		self.other_employee = Employee.objects.create(
			name='Other employee', department='Operations', business=self.other_business,
		)

	def test_manager_cannot_open_other_business_employee(self):
		self.client.force_login(self.manager)
		response = self.client.get(reverse('employee_detail', args=[self.other_employee.pk]))
		self.assertEqual(response.status_code, 404)

	def test_face_attendance_requires_login(self):
		response = self.client.post(reverse('mark_attendance_face'), {})
		self.assertEqual(response.status_code, 302)

	@patch('employees.views.face_service.identify')
	@patch('employees.views._decode_image')
	def test_face_attendance_does_not_cross_businesses(self, decode_image, identify):
		identify.return_value = (self.other_employee, 0.1)
		decode_image.return_value = object()
		self.client.force_login(self.manager)
		response = self.client.post(
			reverse('mark_attendance_face'),
			data='{"images":["data:image/jpeg;base64,test","data:image/jpeg;base64,test","data:image/jpeg;base64,test"]}',
			content_type='application/json',
		)
		self.assertEqual(response.status_code, 403)
		self.assertFalse(Attendance.objects.exists())
