from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Employee, SalaryRequest, Attendance
from .forms import EmployeeForm, SalaryRequestForm, AttendanceForm, SignUpForm
from django.utils import timezone
from django.db.models import Max
from django.views.decorators.csrf import csrf_exempt
from django.db import connection
import csv
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required
from datetime import datetime

def signup_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password1']
        if len(password) < 4:
            messages.error(request, 'Password must be at least 4 characters.')
            return render(request, 'employees/signup.html')
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return render(request, 'employees/signup.html')
        User.objects.create_user(username=username, password=password)
        messages.success(request, 'Account created successfully. Please login.')
        return redirect('login')
    return render(request, 'employees/signup.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            return redirect('home')  # bedel 'home' url haddii loo baahdo
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'employees/login.html')

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def home(request):
    return render(request, 'employees/home.html')

@login_required
def employee_list(request):
    employees = Employee.objects.all()
    return render(request, 'employees/employee_list.html', {'employees': employees})

@staff_member_required
def employee_create(request):
    form = EmployeeForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('employee_list')
    return render(request, 'employees/employee_form.html', {'form': form})

@staff_member_required
def employee_update(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    form = EmployeeForm(request.POST or None, instance=employee)
    if form.is_valid():
        form.save()
        return redirect('employee_list')
    return render(request, 'employees/employee_form.html', {'form': form})

@staff_member_required
def employee_delete(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        employee.delete()
        return redirect('employee_list')
    return render(request, 'employees/employee_confirm_delete.html', {'employee': employee})

@login_required
def submit_salary_request(request):
    today = datetime.today()
    if today.day != 1:
        messages.error(request, " You can only request salary on the 1st day of the month.")
        return redirect('home')
    if request.method == 'POST':
        form = SalaryRequestForm(request.POST)
        if form.is_valid():
            salary_req = form.save(commit=False)
            salary_req.employee = request.user
            salary_req.save()
            messages.success(request, "Salary time is now!")
            return render(request, 'employees/salary_time.html')
    else:
        form = SalaryRequestForm()
    return render(request, 'employees/salary_request_form.html', {'form': form})

@login_required
@staff_member_required
def attendance(request):
    employees = Employee.objects.all()
    today = timezone.now().date()
    if request.method == 'POST':
        for emp_id in request.POST.getlist('employee_ids'):
            status = request.POST.get(f'attendance_{emp_id}')
            if status:
                att, created = Attendance.objects.get_or_create(
                    employee_id=emp_id,
                    date=today,
                    defaults={'status': status}
                )
                if not created:
                    att.status = status
                    att.save()
        return redirect('absent_today')
    return render(request, 'employees/attendance.html', {'employees': employees})

def attendance_report(request):
    # Hel dhammaan xogta attendance ee la kaydiyay
    reports = Attendance.objects.all().order_by('-date')  # Sort by date in descending order
    return render(request, 'employees/attendance_report.html', {'reports': reports})




@login_required
def mark_attendance(request):
    if request.method == 'POST':
        for employee in Employee.objects.all():
            # Get status and employee ID from the form
            employee_id = request.POST.get(f'attendance_{employee.id}_status')
            status = request.POST.get(f'attendance_{employee.id}_status')
            
            if employee_id and status:
                try:
                    # Ensure employee exists
                    employee = Employee.objects.get(id=employee_id)
                    Attendance.objects.create(employee=employee, status=status, date=timezone.now().date())
                except Employee.DoesNotExist:
                    # Handle case where employee is not found
                    messages.error(request, f"Employee with ID {employee_id} does not exist.")
                    return redirect('attendance')  # Redirect back to the attendance page if error occurs
            else:
                messages.error(request, "Missing attendance data. Please try again.")
                return redirect('attendance')  # Redirect back to the attendance page

        return redirect('absent_today')  # Redirect to the page showing today's absents after submit

    employees = Employee.objects.all()
    return render(request, 'employees/attendance.html', {'employees': employees})

def absent_today(request):
    today = timezone.now().date()
    # Get the latest attendance record for each employee for today
    latest_attendance_ids = (
        Attendance.objects
        .filter(date=today)
        .values('employee')
        .annotate(latest_id=Max('id'))
        .values_list('latest_id', flat=True)
    )
    latest_attendance = Attendance.objects.filter(id__in=latest_attendance_ids)

    absents = latest_attendance.filter(status='Absent')
    presents = latest_attendance.filter(status='Present')
    return render(request, 'employees/absent_today.html', {'absents': absents, 'presents': presents})

@login_required
@csrf_exempt  # Only if you have CSRF issues; otherwise, not needed
def clear_attendance(request):
    if request.method == 'POST':
        status = request.POST.get('status')
        today = timezone.now().date()
        Attendance.objects.filter(date=today, status=status).delete()
    return redirect('absent_today')

@login_required
def delete_all_employees(request):
    if request.method == 'POST':
        Employee.objects.all().delete()
        # Reset the auto-incrementing ID for SQLite
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='employees_employee';")
    return redirect('employee_list')

@login_required
def export_today_attendance(request):
    today = timezone.now().date()
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="attendance_{today}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Name', 'Department', 'Salary', 'Attendance'])

    employees = Employee.objects.all()
    for employee in employees:
        attendance = Attendance.objects.filter(employee=employee, date=today).first()
        status = attendance.status if attendance else 'Absent'
        writer.writerow([employee.name, employee.department, employee.salary, status])

    return response

@login_required
def employee_detail(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    # Haddii aad rabto attendance ama xog kale, waxaad ku dari kartaa halkan
    attendance_records = Attendance.objects.filter(employee=employee).order_by('-date')
    return render(request, 'employees/employee_detail.html', {
        'employee': employee,
        'attendance_records': attendance_records,
    })

def about(request):
    return render(request, 'employees/about.html')

def contact(request):
    return render(request, 'employees/contact.html')

@staff_member_required
def salary_requests_list(request):
    if request.user.is_staff:
        requests = SalaryRequest.objects.all().order_by('-created_at')
    else:
        requests = SalaryRequest.objects.filter(employee=request.user).order_by('-created_at')
    return render(request, 'employees/salary_requests_list.html', {'requests': requests})

@login_required
def delete_salary_request(request, pk):
    req = get_object_or_404(SalaryRequest, pk=pk)
    # Kaliya admin ama qofka iska leh request-ka ayaa tirtiri kara
    if request.user == req.employee or request.user.is_staff:
        if request.method == 'POST':
            req.delete()
            messages.success(request, "Salary request deleted.")
            return redirect('salary_requests_list')
        return render(request, 'employees/confirm_delete_salary.html', {'req': req})
    else:
        messages.error(request, "You are not allowed to delete this request.")
        return redirect('salary_requests_list')