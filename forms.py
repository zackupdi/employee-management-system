from django import forms
from .models import Employee, SalaryRequest, Attendance
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['name', 'department', 'salary']

    def clean_salary(self):
        salary = self.cleaned_data.get('salary')
        if salary is None or salary == 0:
            raise forms.ValidationError("Salary is required and must be greater than 0.")
        return salary

class SalaryRequestForm(forms.ModelForm):
    class Meta:
        model = SalaryRequest
        fields = ['request_type']

class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['employee', 'date', 'status']

class SignUpForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'password1', 'password2']
