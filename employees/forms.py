from django import forms
from .models import Employee, SalaryRequest, LeaveRequest, Attendance
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Business, WorkSchedule

class EmployeeForm(forms.ModelForm):
    username = forms.CharField(required=False, label='Username')
    password1 = forms.CharField(required=False, label='Password', widget=forms.PasswordInput(render_value=False))
    password2 = forms.CharField(required=False, label='Confirm password', widget=forms.PasswordInput(render_value=False))

    class Meta:
        model = Employee
        fields = [
            'name', 'employee_number', 'email', 'phone', 'position', 'workplace',
            'employment_start_date', 'employment_status', 'salary', 'photo',
            'business', 'assigned_schedule',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['business'].queryset = Business.objects.filter(is_active=True)
        self.fields['assigned_schedule'].queryset = WorkSchedule.objects.filter(is_active=True).select_related('business')
        self.fields['employee_number'].required = True
        self.fields['position'].required = True
        self.fields['employment_start_date'].widget = forms.DateInput(attrs={'type': 'date'})
        self.fields['photo'].label = 'Profile photo'
        self.fields['business'].label = 'Business'
        self.fields['assigned_schedule'].label = 'Work schedule'
        if self.instance.pk and self.instance.user_id:
            self.fields['username'].initial = self.instance.user.username

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get('password1')
        password2 = cleaned.get('password2')
        if password1 or password2:
            if password1 != password2:
                raise forms.ValidationError('Passwords do not match.')
            if len(password1 or '') < 4:
                raise forms.ValidationError('Password must be at least 4 characters.')
        username = cleaned.get('username', '').strip()
        if not self.instance.pk and not username:
            self.add_error('username', 'Username is required for a new employee.')
        if not self.instance.pk and not password1:
            self.add_error('password1', 'Password is required for a new employee.')
        if not self.instance.pk and not password2:
            self.add_error('password2', 'Please confirm the password.')
        if username:
            users = User.objects.filter(username=username)
            if self.instance.user_id:
                users = users.exclude(pk=self.instance.user_id)
            if users.exists():
                self.add_error('username', 'That username is already in use.')
        return cleaned

    def save(self, commit=True):
        employee = super().save(commit=False)
        position = self.cleaned_data.get('position', '').strip()
        employee.department = position
        username = self.cleaned_data.get('username', '').strip()
        password = self.cleaned_data.get('password1')
        if username:
            user = employee.user or User(username=username)
            user.username = username
            if password:
                user.set_password(password)
            user.save()
            employee.user = user
        if commit:
            employee.save()
        return employee

    def clean_salary(self):
        salary = self.cleaned_data.get('salary')
        if salary is None or salary == 0:
            raise forms.ValidationError("Salary is required and must be greater than 0.")
        return salary

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if photo:
            if photo.size > 5 * 1024 * 1024:
                raise forms.ValidationError('Profile photo must be 5 MB or smaller.')
            content_type = getattr(photo, 'content_type', None) or getattr(photo.file, 'content_type', None)
            if content_type and content_type not in {'image/jpeg', 'image/png', 'image/webp'}:
                raise forms.ValidationError('Use a JPEG, PNG, or WebP image.')
            if content_type is None:
                name = (photo.name or '').lower()
                allowed = ('.jpg', '.jpeg', '.png', '.webp')
                if not any(name.endswith(ext) for ext in allowed):
                    raise forms.ValidationError('Use a JPEG, PNG, or WebP image.')
        return photo


class EmployeeSelfForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['email', 'phone', 'workplace', 'photo']

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if photo:
            if photo.size > 5 * 1024 * 1024:
                raise forms.ValidationError('Profile photo must be 5 MB or smaller.')
            content_type = getattr(photo, 'content_type', None) or getattr(photo.file, 'content_type', None)
            if content_type and content_type not in {'image/jpeg', 'image/png', 'image/webp'}:
                raise forms.ValidationError('Use a JPEG, PNG, or WebP image.')
            if content_type is None:
                name = (photo.name or '').lower()
                allowed = ('.jpg', '.jpeg', '.png', '.webp')
                if not any(name.endswith(ext) for ext in allowed):
                    raise forms.ValidationError('Use a JPEG, PNG, or WebP image.')
        return photo

class SalaryRequestForm(forms.ModelForm):
    class Meta:
        model = SalaryRequest
        fields = ['request_type', 'amount', 'reason']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['amount'].required = True

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= 0:
            raise forms.ValidationError('Requested amount must be greater than zero.')
        return amount


class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ['start_date', 'end_date', 'reason']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'reason': forms.Textarea(attrs={'rows': 3}),
        }

    def clean(self):
        cleaned = super().clean()
        start_date = cleaned.get('start_date')
        end_date = cleaned.get('end_date')
        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError('End date cannot be before start date.')
        return cleaned

class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['employee', 'date', 'status']

class SignUpForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'password1', 'password2']
