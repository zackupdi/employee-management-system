from django.contrib import admin
from .models import (
	Attendance,
	AttendanceAuditLog,
	Business,
	BusinessMembership,
	Employee,
	LeaveRequest,
	FaceEnrollment,
	KioskDevice,
	SalaryRequest,
	SalaryPayment,
	Notification,
	WorkSchedule,
)

admin.site.register(Business)
admin.site.register(BusinessMembership)
admin.site.register(WorkSchedule)
admin.site.register(KioskDevice)
admin.site.register(Employee)
admin.site.register(SalaryRequest)
admin.site.register(LeaveRequest)
admin.site.register(SalaryPayment)
admin.site.register(Notification)
admin.site.register(Attendance)
admin.site.register(FaceEnrollment)
admin.site.register(AttendanceAuditLog)
