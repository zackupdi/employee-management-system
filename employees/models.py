from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator


class Business(models.Model):
    name = models.CharField(max_length=150, unique=True)
    location = models.CharField(max_length=255, blank=True)
    timezone = models.CharField(max_length=64, default='UTC')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class BusinessMembership(models.Model):
    SUPER_ADMIN = 'SUPER_ADMIN'
    MANAGER = 'MANAGER'
    EMPLOYEE = 'EMPLOYEE'
    ROLE_CHOICES = (
        (SUPER_ADMIN, 'Super Admin'),
        (MANAGER, 'Manager'),
        (EMPLOYEE, 'Employee'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='business_memberships')
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=EMPLOYEE)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'business'], name='unique_business_membership'),
        ]


class WorkSchedule(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='schedules')
    name = models.CharField(max_length=100, default='Default schedule')
    work_start = models.TimeField(default='08:00')
    checkin_window_end = models.TimeField(default='08:30')
    work_end = models.TimeField(default='16:00')
    grace_minutes = models.PositiveIntegerField(default=0)
    timezone = models.CharField(max_length=64, default='UTC')
    workdays = models.CharField(max_length=20, default='0,1,2,3,4')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.business} - {self.name}'


class KioskDevice(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='kiosks')
    name = models.CharField(max_length=100)
    device_id = models.CharField(max_length=100, unique=True)
    token_hash = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.business} - {self.name}'

class Employee(models.Model):
    name = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # or IntegerField
    photo = models.ImageField(upload_to='employee_photos/', blank=True, null=True)
    face_encoding = models.BinaryField(blank=True, null=True)
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='employee_profile')
    business = models.ForeignKey(Business, on_delete=models.SET_NULL, null=True, blank=True, related_name='employees')
    employee_number = models.CharField(max_length=50, null=True, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    position = models.CharField(max_length=100, blank=True)
    workplace = models.CharField(max_length=255, blank=True)
    employment_start_date = models.DateField(null=True, blank=True)
    employment_status = models.CharField(max_length=30, default='Active')
    assigned_schedule = models.ForeignKey(WorkSchedule, on_delete=models.SET_NULL, null=True, blank=True, related_name='employees')
    face_enrolled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['business', 'employee_number'], name='unique_business_employee_number'),
        ]

    def __str__(self):
        return self.name

class Attendance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    date = models.DateField()
    check_in = models.TimeField(blank=True, null=True)
    check_out = models.TimeField(blank=True, null=True)
    status = models.CharField(max_length=10, default='Present')
    business = models.ForeignKey(Business, on_delete=models.SET_NULL, null=True, blank=True, related_name='attendance_records')
    attendance_date = models.DateField(null=True, blank=True)
    check_in_at = models.DateTimeField(null=True, blank=True)
    check_out_at = models.DateTimeField(null=True, blank=True)
    late_minutes = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    schedule = models.ForeignKey(WorkSchedule, on_delete=models.SET_NULL, null=True, blank=True, related_name='attendance_records')
    kiosk = models.ForeignKey(KioskDevice, on_delete=models.SET_NULL, null=True, blank=True, related_name='attendance_records')
    verification_method = models.CharField(max_length=30, default='face')
    verification_score = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['employee', 'date'], name='unique_employee_attendance_day'),
        ]

    def __str__(self):
        return f"{self.employee.name} - {self.date} - {self.status}"


class FaceEnrollment(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='face_enrollments')
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='face_enrollments')
    embedding = models.BinaryField()
    algorithm = models.CharField(max_length=50, default='opencv-lbph')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    enrolled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    revoked_at = models.DateTimeField(null=True, blank=True)


class AttendanceAuditLog(models.Model):
    business = models.ForeignKey(Business, on_delete=models.SET_NULL, null=True, blank=True)
    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True)
    attendance = models.ForeignKey(Attendance, on_delete=models.SET_NULL, null=True, blank=True)
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=50)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class SalaryRequest(models.Model):
    PENDING = 'pending'
    ACCEPTED = 'accepted'
    REJECTED = 'rejected'
    PROCESSED = 'processed'
    STATUS_CHOICES = (
        (PENDING, 'Pending Review'),
        (ACCEPTED, 'Accepted'),
        (REJECTED, 'Rejected'),
        (PROCESSED, 'Processed'),
    )

    employee = models.ForeignKey(User, on_delete=models.CASCADE)
    request_type = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    business = models.ForeignKey(Business, on_delete=models.SET_NULL, null=True, blank=True, related_name='salary_requests')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_salary_requests')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def step_number(self):
        return {
            self.PENDING: 1,
            self.ACCEPTED: 2,
            self.PROCESSED: 3,
            self.REJECTED: 0,
        }.get(self.status, 1)

    def __str__(self):
        return f"{self.employee.username} - {self.request_type}"


class LeaveRequest(models.Model):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    STATUS_CHOICES = (
        (PENDING, 'Pending Review'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
    )

    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leave_requests')
    business = models.ForeignKey(Business, on_delete=models.SET_NULL, null=True, blank=True, related_name='leave_requests')
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_leave_requests')

    class Meta:
        ordering = ['-created_at']

    @property
    def days_count(self):
        return (self.end_date - self.start_date).days + 1

    def __str__(self):
        return f'{self.employee.username} - {self.start_date} to {self.end_date}'


class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    business = models.ForeignKey(Business, on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    salary_request = models.ForeignKey(SalaryRequest, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    leave_request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    notification_type = models.CharField(max_length=40, default='salary_request')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class SalaryPayment(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='salary_payments')
    period = models.CharField(max_length=7, help_text='Format: YYYY-MM, e.g. 2026-09')
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    date_paid = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['employee', 'period'], name='unique_employee_salary_period'),
        ]
        ordering = ['-period']

    def __str__(self):
        return f'{self.employee.name} - {self.period}'

    @property
    def salary_due(self):
        return self.employee.salary or 0

    @property
    def remaining(self):
        remaining = self.salary_due - self.amount_paid
        return remaining if remaining > 0 else 0

    @property
    def status(self):
        if self.amount_paid <= 0:
            return 'not_paid'
        if self.amount_paid >= self.salary_due:
            return 'paid'
        return 'partial'
