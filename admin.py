from django.contrib import admin
from .models import Employee, SalaryRequest, Attendance

admin.site.register(Employee)
admin.site.register(SalaryRequest)
admin.site.register(Attendance)
