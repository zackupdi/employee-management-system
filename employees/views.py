from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from .models import Employee, SalaryRequest, LeaveRequest, SalaryPayment, Attendance, Notification
from .models import Business, BusinessMembership, FaceEnrollment
from .forms import EmployeeForm, EmployeeSelfForm, SalaryRequestForm, LeaveRequestForm, AttendanceForm, SignUpForm
from django.utils import timezone
from django.db.models import Count, Max, Sum
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.http import require_POST
from django.db import connection, transaction
from django.conf import settings
import csv
import base64
import json
import os
from io import BytesIO
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.models import User
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
from decimal import Decimal, InvalidOperation
import re

import numpy as np
from PIL import Image
from . import face_service
from .decorators import employee_required, management_required

UserModel = get_user_model()


def _businesses_for_user(user):
    if user.is_superuser:
        return Business.objects.filter(is_active=True)
    return BusinessMembership.objects.filter(
        user=user, is_active=True,
    ).values_list('business_id', flat=True)


def _employees_for_user(user):
    if user.is_superuser:
        return Employee.objects.all()
    business_ids = _businesses_for_user(user)
    return Employee.objects.filter(business_id__in=business_ids)


def _attendance_timing(now, schedule):
    status = 'Present'
    late_minutes = 0
    if schedule:
        zone = ZoneInfo(schedule.timezone)
        checkin_end = datetime.combine(
            now.date(), schedule.checkin_window_end, tzinfo=zone,
        )
        if now > checkin_end:
            status = 'Late'
            late_minutes = max(0, int((now - checkin_end).total_seconds() // 60))
    return status, late_minutes


def _decode_image(data_url):
    if not data_url or ',' not in data_url:
        raise ValueError('Invalid image data.')
    _, encoded = data_url.split(',', 1)
    return np.array(Image.open(BytesIO(base64.b64decode(encoded))).convert('RGB'))

def signup_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        if not username:
            messages.error(request, 'Username is required.')
            return render(request, 'employees/signup.html')

        if len(password1) < 4:
            messages.error(request, 'Password must be at least 4 characters.')
            return render(request, 'employees/signup.html')

        if password1 != password2:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'employees/signup.html')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return render(request, 'employees/signup.html')

        User.objects.create_user(username=username, password=password1)
        messages.success(request, 'Account created successfully. Please login.')
        return redirect('login')
    return render(request, 'employees/signup.html')


def demo_mode_enabled():
    return os.environ.get('DEMO_MODE', '').lower() == 'true'


def _demo_user(role):
    username = f'demo_{role}'
    user, _ = UserModel.objects.get_or_create(username=username)
    user.first_name = 'Demo'
    user.last_name = 'Admin' if role == 'admin' else 'Staff'
    user.is_active = True
    user.is_staff = True
    user.is_superuser = role == 'admin'
    user.set_unusable_password()
    user.save(update_fields=['first_name', 'last_name', 'is_active', 'is_staff', 'is_superuser', 'password'])

    if role == 'staff':
        Employee.objects.get_or_create(
            user=user,
            defaults={
                'name': 'Demo Staff',
                'department': 'Demonstration',
                'position': 'Staff Member',
                'salary': Decimal('0.00'),
            },
        )
    return user


def login_view(request):
    # Demo mode = no normal login
    if demo_mode_enabled():
        return redirect("demo_login")

    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('dashboard')
        return redirect('staff_dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            request.session.pop('demo_mode', None)
            request.session.pop('demo_role', None)
            request.session.pop('demo_user', None)
            if user.is_superuser:
                return redirect('dashboard')
            return redirect('staff_dashboard')
        messages.error(request, 'Invalid username or password.')

    return render(request, 'employees/login.html')


def demo_login(request):
    """
    Direct demo login.

    /demo/?role=admin
    /demo/?role=staff
    """

    if not demo_mode_enabled():
        return redirect("login")

    User = get_user_model()
    role = request.GET.get("role", "admin").strip().lower()

    if role == "admin":
        user, created = User.objects.get_or_create(
            username="demo_admin"
        )

        user.first_name = "Demo"
        user.last_name = "Admin"
        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.set_unusable_password()
        user.save()

        auth_login(request, user)
        request.session["demo_mode"] = True
        request.session["demo_role"] = "admin"
        request.session.modified = True
        return redirect("/employees/dashboard/")

    if role == "staff":
        user, created = User.objects.get_or_create(
            username="demo_staff"
        )

        user.first_name = "Demo"
        user.last_name = "Staff"
        user.is_active = True
        user.is_staff = True
        user.is_superuser = False
        user.set_unusable_password()
        user.save()

        auth_login(request, user)
        request.session["demo_mode"] = True
        request.session["demo_role"] = "staff"
        request.session.modified = True
        return redirect("/employees/staff/dashboard/")

    return redirect("/employees/demo/?role=admin")


def demo_logout(request):
    logout(request)
    request.session.flush()

    if demo_mode_enabled():
        return redirect("/employees/demo/")
    return redirect("/employees/login/")


def logout_view(request):
    request.session.pop('demo_mode', None)
    request.session.pop('demo_role', None)
    request.session.pop('demo_user', None)
    logout(request)
    return redirect('login')


@login_required
def dashboard(request):
    return render(request, 'employees/dashboard.html')


@login_required
def home(request):
    if not request.user.is_staff:
        return redirect('staff_dashboard')
    employees = _employees_for_user(request.user)
    today = timezone.localdate()
    attendance_today = Attendance.objects.filter(employee__in=employees, date=today)
    return render(request, 'employees/dashboard.html', {
        'employees_count': employees.count(),
        'present_count': attendance_today.filter(status__in=['Present', 'Late']).count(),
        'absent_count': attendance_today.filter(status='Absent').count(),
        'department_count': employees.values('department').distinct().count(),
    })


@login_required
def staff_dashboard(request):
    return render(
        request,
        'employees/staff_dashboard.html'
    )


@employee_required
def my_attendance(request):
    employee = request.user.employee_profile
    records = list(Attendance.objects.filter(employee=employee).order_by('-date'))
    for record in records:
        record.working_minutes = 0
        if record.check_in_at and record.check_out_at:
            record.working_minutes = max(
                0,
                int((record.check_out_at - record.check_in_at).total_seconds() // 60),
            )
    return render(request, 'employees/my_attendance.html', {
        'employee': employee,
        'attendance_records': records,
    })


@employee_required
def my_schedule(request):
    employee = request.user.employee_profile
    return render(request, 'employees/my_schedule.html', {
        'employee': employee,
        'schedule': employee.assigned_schedule,
    })


@employee_required
def change_password(request):
    form = PasswordChangeForm(request.user, request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Your password was changed successfully.')
        return redirect('staff_dashboard')
    return render(request, 'employees/change_password.html', {'form': form})

@login_required
def employee_list(request):
    if not request.user.is_staff:
        messages.error(request, 'Only admins can view employee records.')
        return redirect('request_salary')
    employees = _employees_for_user(request.user).select_related('business', 'assigned_schedule')
    return render(request, 'employees/employee_list.html', {'employees': employees})

@management_required
def employee_create(request):
    form = EmployeeForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        employee = form.save()
        if not employee.business_id:
            business_id = _businesses_for_user(request.user).values_list('id', flat=True).first() if request.user.is_superuser else _businesses_for_user(request.user).first()
            employee.business_id = business_id
        employee.save()
        face_service.register_employee_face(employee)
        return redirect('employee_list')
    return render(request, 'employees/employee_form.html', {'form': form})

@management_required
def employee_update(request, pk):
    employee = get_object_or_404(_employees_for_user(request.user), pk=pk)
    form = EmployeeForm(request.POST or None, request.FILES or None, instance=employee)
    if form.is_valid():
        employee = form.save()
        face_service.register_employee_face(employee)
        return redirect('employee_list')
    return render(request, 'employees/employee_form.html', {'form': form})

@management_required
def employee_delete(request, pk):
    employee = get_object_or_404(_employees_for_user(request.user), pk=pk)
    if request.method == 'POST':
        employee.delete()
        return redirect('employee_list')
    return render(request, 'employees/employee_confirm_delete.html', {'employee': employee})

@employee_required
def submit_salary_request(request):
    if request.method == 'POST':
        form = SalaryRequestForm(request.POST)
        if form.is_valid():
            salary_req = form.save(commit=False)
            salary_req.employee = request.user
            employee = request.user.employee_profile
            salary_req.business = employee.business
            salary_req.save()
            managers = UserModel.objects.filter(
                is_staff=True,
                business_memberships__business=employee.business,
                business_memberships__is_active=True,
            ).distinct()
            if request.user.is_superuser:
                managers = UserModel.objects.filter(is_staff=True)
            message = f'{employee.name} submitted a {salary_req.request_type} request.'
            Notification.objects.bulk_create([
                Notification(
                    recipient=manager,
                    business=employee.business,
                    salary_request=salary_req,
                    message=message,
                )
                for manager in managers
                if manager.pk != request.user.pk
            ])
            messages.success(request, 'Your request was submitted and is pending review.')
            return redirect('salary_requests_list')
    else:
        form = SalaryRequestForm()
    return render(request, 'employees/request_salary.html', {'form': form})


@employee_required
def employee_salary(request):
    return render(request, 'employees/empaloyee_salary.html')


@employee_required
def my_salary(request):
    employee = Employee.objects.filter(user=request.user).first()
    if employee is None:
        messages.error(
            request,
            "No employee profile is linked to your account. Contact an administrator.",
        )
        return render(request, 'employees/my_salary.html', {
            'employee': None,
            'payments': [],
        })

    payments = SalaryPayment.objects.filter(employee=employee).order_by('-period')
    current = payments.first()
    total_earned = sum((payment.amount_paid for payment in payments), Decimal('0.00'))
    return render(request, 'employees/my_salary.html', {
        'employee': employee,
        'payments': payments,
        'current': current,
        'total_earned': total_earned,
    })


@management_required
def payroll(request):
    period = request.GET.get('period') or timezone.localdate().strftime('%Y-%m')
    if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', period):
        period = timezone.localdate().strftime('%Y-%m')

    employees = _employees_for_user(request.user).order_by('name')
    rows = [
        SalaryPayment.objects.get_or_create(
            employee=employee,
            period=period,
            defaults={'amount_paid': Decimal('0.00')},
        )[0]
        for employee in employees
    ]
    total_due = sum((row.salary_due for row in rows), Decimal('0.00'))
    total_paid = sum((row.amount_paid for row in rows), Decimal('0.00'))
    return render(request, 'employees/payroll.html', {
        'rows': rows,
        'period': period,
        'total_due': total_due,
        'total_paid': total_paid,
        'total_remaining': max(Decimal('0.00'), total_due - total_paid),
        'paid_count': sum(row.status == 'paid' for row in rows),
        'partial_count': sum(row.status == 'partial' for row in rows),
        'not_paid_count': sum(row.status == 'not_paid' for row in rows),
    })


@management_required
@require_POST
def record_payment(request, payment_id):
    payment = get_object_or_404(SalaryPayment.objects.select_related('employee'), pk=payment_id)
    if not _employees_for_user(request.user).filter(pk=payment.employee_id).exists():
        return JsonResponse({'success': False, 'message': 'You cannot edit this payroll record.'}, status=403)
    try:
        amount = Decimal(request.POST.get('amount', '0').strip())
    except (InvalidOperation, AttributeError):
        messages.error(request, 'Invalid amount entered.')
        return redirect(f'/employees/payroll/?period={payment.period}')
    if amount <= 0:
        messages.error(request, 'Amount must be greater than zero.')
    else:
        payment.amount_paid = min(payment.salary_due, payment.amount_paid + amount)
        payment.date_paid = timezone.localdate()
        payment.save(update_fields=['amount_paid', 'date_paid', 'updated_at'])
        messages.success(request, f'Payment recorded for {payment.employee.name}.')
    return redirect(f'/employees/payroll/?period={payment.period}')


@management_required
def reports(request):
    today = timezone.localdate()
    period = today.strftime('%Y-%m')
    employees = _employees_for_user(request.user)
    recent_attendance = Attendance.objects.filter(
        employee__in=employees,
        date__gte=today - timedelta(days=30),
    )
    present_count = recent_attendance.filter(status__in=['Present', 'Late']).count()
    absent_count = recent_attendance.filter(status='Absent').count()
    total_marks = present_count + absent_count
    daily_trend = []
    for offset in range(13, -1, -1):
        day = today - timedelta(days=offset)
        day_records = Attendance.objects.filter(employee__in=employees, date=day)
        daily_trend.append({
            'date': day.strftime('%b %d'),
            'present': day_records.filter(status__in=['Present', 'Late']).count(),
            'absent': day_records.filter(status='Absent').count(),
        })
    payments = SalaryPayment.objects.filter(employee__in=employees, period=period)
    total_due = sum((payment.salary_due for payment in payments), Decimal('0.00'))
    total_paid = payments.aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')
    requests = SalaryRequest.objects.filter(employee__in=User.objects.filter(employee_profile__in=employees))
    requests_this_month = requests.filter(created_at__date__gte=today.replace(day=1)).count()
    by_department = list(
        employees.values('department').annotate(count=Count('id')).order_by('-count')
    )
    attendance_by_employee = (
        recent_attendance.filter(status__in=['Present', 'Late'])
        .values('employee__name')
        .annotate(days_present=Count('id'))
        .order_by('-days_present')[:5]
    )
    payroll_trend = list(reversed(list(
        SalaryPayment.objects.filter(employee__in=employees)
        .values('period').annotate(paid=Sum('amount_paid')).order_by('-period')[:6]
    )))
    return render(request, 'employees/reports.html', {
        'today': today,
        'period': period,
        'total_employees': employees.count(),
        'by_department': by_department,
        'attendance_rate': round((present_count / total_marks) * 100, 1) if total_marks else 0,
        'present_count': present_count,
        'absent_count': absent_count,
        'today_present': Attendance.objects.filter(employee__in=employees, date=today, status__in=['Present', 'Late']).count(),
        'today_absent': Attendance.objects.filter(employee__in=employees, date=today, status='Absent').count(),
        'daily_trend': daily_trend,
        'attendance_by_employee': attendance_by_employee,
        'total_due': total_due,
        'total_paid': total_paid,
        'total_remaining': total_due - total_paid,
        'paid_count': sum(payment.status == 'paid' for payment in payments),
        'partial_count': sum(payment.status == 'partial' for payment in payments),
        'not_paid_count': max(
            0,
            employees.count()
            - sum(payment.status == 'paid' for payment in payments)
            - sum(payment.status == 'partial' for payment in payments),
        ),
        'payroll_trend': payroll_trend,
        'total_requests': requests.count(),
        'requests_this_month': requests_this_month,
    })


@management_required
def manage_users(request):
    users = UserModel.objects.all().order_by('-date_joined')
    employee_map = {
        employee.user_id: employee
        for employee in Employee.objects.exclude(user__isnull=True)
    }
    rows = [{'user': user, 'employee': employee_map.get(user.id)} for user in users]
    return render(request, 'employees/manage_users.html', {
        'rows': rows,
        'total_users': users.count(),
        'admin_count': users.filter(is_staff=True).count(),
        'staff_count': users.filter(is_staff=False).count(),
        'active_count': users.filter(is_active=True).count(),
    })


@management_required
@require_POST
def toggle_user_role(request, user_id):
    target = get_object_or_404(UserModel, pk=user_id)
    if target == request.user:
        messages.error(request, "You can't change your own role.")
    else:
        target.is_staff = not target.is_staff
        target.save(update_fields=['is_staff'])
        messages.success(request, f"{target.username} is now {'Admin' if target.is_staff else 'Staff'}.")
    return redirect('manage_users')


@management_required
@require_POST
def toggle_user_active(request, user_id):
    target = get_object_or_404(UserModel, pk=user_id)
    if target == request.user:
        messages.error(request, "You can't deactivate your own account.")
    else:
        target.is_active = not target.is_active
        target.save(update_fields=['is_active'])
        messages.success(request, f"{target.username} has been {'activated' if target.is_active else 'deactivated'}.")
    return redirect('manage_users')


@management_required
@require_POST
def delete_user(request, user_id):
    target = get_object_or_404(UserModel, pk=user_id)
    if target == request.user:
        messages.error(request, "You can't delete your own account.")
    else:
        username = target.username
        target.delete()
        messages.success(request, f'{username} has been deleted.')
    return redirect('manage_users')

@login_required
@management_required
def attendance(request):
    today = timezone.now().date()
    presents = Attendance.objects.filter(
        employee__in=_employees_for_user(request.user),
        date=today,
        status__in=['Present', 'Late'],
    ).select_related('employee')
    return render(request, 'employees/attendance.html', {'presents': presents, 'today': today})


@login_required
@require_POST
@csrf_protect
def mark_attendance_face(request):
    try:
        payload = json.loads(request.body)
        image_data = payload.get('images') or [payload.get('image', '')]
        if len(image_data) < 3:
            return JsonResponse({'success': False, 'message': 'Hold still while three frames are verified.'}, status=400)
        matches = []
        for data_url in image_data[:3]:
            frame = _decode_image(data_url)
            match, score = face_service.identify(frame)
            if match:
                matches.append((match, score))
        if len(matches) < 2 or len({match.pk for match, _ in matches}) != 1:
            return JsonResponse({'success': False, 'message': 'Face is not stable or not recognized. Please center your face and try again.'})
        employee = matches[0][0]
        score = sum(match_score for _, match_score in matches) / len(matches)
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({'success': False, 'message': 'Invalid image data.'}, status=400)
    except RuntimeError as error:
        return JsonResponse({'success': False, 'message': str(error)}, status=503)

    if not employee:
        return JsonResponse({'success': False, 'message': 'Face not recognized. Are you registered?'})

    if not request.user.is_superuser and not _employees_for_user(request.user).filter(pk=employee.pk).exists():
        return JsonResponse({'success': False, 'message': 'This employee is outside your business.'}, status=403)

    business = employee.business
    schedule = employee.assigned_schedule or (business.schedules.filter(is_active=True).first() if business else None)
    zone = ZoneInfo((schedule or business).timezone if (schedule or business) else settings.TIME_ZONE)
    now = timezone.now().astimezone(zone)
    today = now.date()
    status, late_minutes = _attendance_timing(now, schedule)
    with transaction.atomic():
        record, created = Attendance.objects.select_for_update().get_or_create(
            employee=employee, date=today,
            defaults={
                'check_in': now.time(), 'status': status, 'business': business,
                'attendance_date': today, 'check_in_at': now,
                'late_minutes': late_minutes, 'schedule': schedule,
                'verification_method': 'face', 'verification_score': score,
            },
        )
        if not created:
            changed_fields = []
            if record.status != status:
                record.status = status
                changed_fields.append('status')
            if record.check_in is None:
                record.check_in = now.time()
                changed_fields.append('check_in')
            if record.attendance_date is None:
                record.attendance_date = today
                changed_fields.append('attendance_date')
            if record.check_in_at is None:
                record.check_in_at = now
                changed_fields.append('check_in_at')
            if record.business_id is None and business:
                record.business = business
                changed_fields.append('business')
            if record.schedule_id is None and schedule:
                record.schedule = schedule
                changed_fields.append('schedule')
            if record.late_minutes != late_minutes:
                record.late_minutes = late_minutes
                changed_fields.append('late_minutes')
            if changed_fields:
                changed_fields.append('updated_at')
                record.save(update_fields=changed_fields)
    checkout_ready = (
        record.check_in is not None
        and now.time() >= (
            datetime.combine(today, record.check_in) +
            timedelta(minutes=settings.MIN_CHECKOUT_MINUTES)
        ).time()
    )
    if not created and record.check_out is None and checkout_ready:
        record.check_out = now.time()
        record.check_out_at = now
        record.save(update_fields=['check_out', 'check_out_at', 'updated_at'])
        message = 'Check-out recorded successfully.'
        event = 'checkout'
    elif not created and record.check_out is None:
        message = 'Already checked in. Check-out will be available later.'
        event = 'already_checked_in'
    elif not created:
        message = 'Attendance already completed today.'
        event = 'completed'
    else:
        message = 'Check-in recorded successfully.'
        event = 'checkin'

    check_in_at = record.check_in_at or now
    check_out_at = record.check_out_at
    working_minutes = 0
    if check_out_at:
        working_minutes = max(0, int((check_out_at - check_in_at).total_seconds() // 60))

    return JsonResponse({
        'success': True,
        'name': employee.name,
        'employee_id': employee.employee_number or employee.pk,
        'time': now.strftime('%I:%M %p'),
        'message': message,
        'event': event,
        'created': created,
        'check_in': check_in_at.strftime('%I:%M %p'),
        'check_out': check_out_at.strftime('%I:%M %p') if check_out_at else None,
        'status': record.status,
        'late_minutes': record.late_minutes,
        'checkout_available': record.check_out is None and checkout_ready,
        'working_minutes': working_minutes,
    })


def _attendance_status(check_in):
    start = time.fromisoformat(settings.WORK_START)
    grace = (datetime.combine(datetime.today(), start) + timedelta(minutes=settings.GRACE_MINUTES)).time()
    return 'Present' if check_in <= grace else 'Late'


@management_required
@csrf_protect
def register_face(request, pk):
    employee = get_object_or_404(_employees_for_user(request.user), pk=pk)
    if request.method == 'GET':
        return render(request, 'employees/register_face.html', {'employee': employee})
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed.'}, status=405)
    try:
        payload = json.loads(request.body)
        image_data = payload.get('images', [])
        if len(image_data) < 3:
            return JsonResponse({'success': False, 'message': 'Three face images are required.'}, status=400)
        images = [_decode_image(data) for data in image_data[:3]]
        if not face_service.register_live_faces(employee, images):
            return JsonResponse({'success': False, 'message': 'Face not detected in all three images. Try again.'}, status=400)
        if employee.business_id and employee.face_encoding:
            FaceEnrollment.objects.filter(employee=employee, is_active=True).update(
                is_active=False,
                revoked_at=timezone.now(),
            )
            FaceEnrollment.objects.create(
                employee=employee,
                business_id=employee.business_id,
                embedding=employee.face_encoding,
                algorithm='dlib-embedding' if settings.USE_DLIB else 'opencv-lbph',
                enrolled_by=request.user,
            )
            employee.face_enrolled_at = timezone.now()
            employee.save(update_fields=['face_enrolled_at'])
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({'success': False, 'message': 'Invalid image data.'}, status=400)
    except RuntimeError as error:
        return JsonResponse({'success': False, 'message': str(error)}, status=503)
    return JsonResponse({'success': True, 'message': 'Face registered successfully.'})

@management_required
def attendance_report(request):
    # Hel dhammaan xogta attendance ee la kaydiyay
    reports = Attendance.objects.all().order_by('-date')  # Sort by date in descending order
    return render(request, 'employees/attendance_report.html', {'reports': reports})




@management_required
def mark_attendance(request):
    if request.method == 'POST':
        for employee in _employees_for_user(request.user):
            status = request.POST.get(f'attendance_{employee.id}')
            if status not in {'Present', 'Absent'}:
                messages.error(request, "Missing attendance data. Please try again.")
                return redirect('mark_attendance')
            Attendance.objects.update_or_create(
                employee=employee,
                date=timezone.now().date(),
                defaults={'status': status},
            )

        return redirect('absent_today')

    employees = _employees_for_user(request.user)
    today = timezone.now().date()
    presents = Attendance.objects.filter(date=today, status='Present').select_related('employee')
    return render(request, 'employees/submit_attendance.html', {'employees': employees, 'today': today, 'presents': presents})

@management_required
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
    presents = latest_attendance.filter(status__in=['Present', 'Late'])
    return render(request, 'employees/absent_today.html', {'absents': absents, 'presents': presents})

@management_required
@csrf_exempt  # Only if you have CSRF issues; otherwise, not needed
def clear_attendance(request, status=None):
    if request.method == 'POST':
        status = request.POST.get('status') or status
        today = timezone.now().date()
        if status:
            Attendance.objects.filter(date=today, status=status).delete()
        else:
            Attendance.objects.filter(date=today).delete()
    return redirect('absent_today')

@management_required
def delete_all_employees(request):
    if request.method == 'POST':
        Employee.objects.all().delete()
        # Reset the auto-incrementing ID for SQLite
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='employees_employee';")
    return redirect('employee_list')

@management_required
def export_today_attendance(request):
    today = timezone.now().date()
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="attendance_{today}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Name', 'Department', 'Salary', 'Attendance'])

    employees = _employees_for_user(request.user)
    for employee in employees:
        attendance = Attendance.objects.filter(employee=employee, date=today).first()
        status = attendance.status if attendance else 'Absent'
        writer.writerow([employee.name, employee.department, employee.salary, status])

    return response

@management_required
def employee_detail(request, pk):
    employee = get_object_or_404(_employees_for_user(request.user), pk=pk)
    # Haddii aad rabto attendance ama xog kale, waxaad ku dari kartaa halkan
    attendance_records = Attendance.objects.filter(employee=employee).order_by('-date')
    return render(request, 'employees/employee_detail.html', {
        'employee': employee,
        'attendance_records': attendance_records,
    })

@employee_required
def my_profile(request):
    employee = get_object_or_404(Employee, user=request.user)
    attendance_records = Attendance.objects.filter(employee=employee).order_by('-date')
    return render(request, 'employees/employee_detail.html', {
        'employee': employee,
        'attendance_records': attendance_records,
        'self_profile': True,
    })


@employee_required
def my_profile_edit(request):
    employee = get_object_or_404(Employee, user=request.user)
    form = EmployeeSelfForm(request.POST or None, request.FILES or None, instance=employee)
    if form.is_valid():
        form.save()
        messages.success(request, 'Your profile was updated.')
        return redirect('my_profile')
    return render(request, 'employees/employee_self_form.html', {'form': form, 'employee': employee})


def about(request):
    return render(request, 'employees/about.html')

def contact(request):
    return render(request, 'employees/contact.html')


@employee_required
def request_leave(request):
    employee = request.user.employee_profile
    form = LeaveRequestForm(request.POST or None)
    if form.is_valid():
        leave = form.save(commit=False)
        leave.employee = request.user
        leave.business = employee.business
        leave.save()
        managers = UserModel.objects.filter(
            is_staff=True,
            business_memberships__business=employee.business,
            business_memberships__is_active=True,
        ).distinct()
        if request.user.is_superuser:
            managers = UserModel.objects.filter(is_staff=True)
        Notification.objects.bulk_create([
            Notification(
                recipient=manager,
                business=employee.business,
                leave_request=leave,
                notification_type='leave_request',
                message=f'{employee.name} submitted a leave request for {leave.days_count} day(s).',
            )
            for manager in managers if manager.pk != request.user.pk
        ])
        messages.success(request, 'Your leave request has been submitted and is pending review.')
        return redirect('leave_requests_list')
    return render(request, 'employees/request_leave.html', {'form': form, 'my_leaves': LeaveRequest.objects.filter(employee=request.user)})


@login_required
def leave_requests_list(request):
    if request.user.is_staff:
        if request.user.is_superuser:
            leaves = LeaveRequest.objects.all()
        else:
            leaves = LeaveRequest.objects.filter(business_id__in=_businesses_for_user(request.user))
    else:
        leaves = LeaveRequest.objects.filter(employee=request.user)
    return render(request, 'employees/leave_requests_list.html', {'leaves': leaves.select_related('employee__employee_profile')})


@management_required
@require_POST
def review_leave_request(request, pk, decision):
    leave = get_object_or_404(LeaveRequest, pk=pk)
    if not request.user.is_superuser and leave.business_id not in _businesses_for_user(request.user):
        raise PermissionDenied
    if leave.status != LeaveRequest.PENDING or decision not in {LeaveRequest.APPROVED, LeaveRequest.REJECTED}:
        messages.error(request, 'Only pending leave requests can be reviewed.')
        return redirect('leave_requests_list')
    leave.status = decision
    leave.reviewed_by = request.user
    leave.reviewed_at = timezone.now()
    leave.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])
    if decision == LeaveRequest.APPROVED:
        message = f'Your leave request was approved. You have {leave.days_count} day(s) off from {leave.start_date} to {leave.end_date}.'
    else:
        message = f'Your leave request for {leave.days_count} day(s) was rejected.'
    Notification.objects.create(
        recipient=leave.employee,
        business=leave.business,
        leave_request=leave,
        notification_type='leave_review',
        message=message,
    )
    messages.success(request, f'Leave request {decision}.')
    return redirect('leave_requests_list')


@login_required
@require_POST
def delete_leave_request(request, pk):
    leave = get_object_or_404(LeaveRequest, pk=pk)
    allowed = request.user == leave.employee or (
        request.user.is_staff and (request.user.is_superuser or leave.business_id in _businesses_for_user(request.user))
    )
    if not allowed:
        raise PermissionDenied
    if leave.status != LeaveRequest.PENDING and not request.user.is_staff:
        messages.error(request, 'You can only delete pending requests.')
    else:
        leave.delete()
        messages.success(request, 'Leave request deleted.')
    return redirect('leave_requests_list')

@login_required
def salary_requests_list(request):
    if request.user.is_staff:
        if request.user.is_superuser:
            requests = SalaryRequest.objects.all()
        else:
            requests = SalaryRequest.objects.filter(
                business_id__in=_businesses_for_user(request.user),
            )
    else:
        requests = SalaryRequest.objects.filter(employee=request.user).order_by('-created_at')
    return render(request, 'employees/salary_requests_list.html', {'requests': requests})


@login_required
def notifications_inbox(request):
    if request.user.is_staff:
        if request.user.is_superuser:
            notifications = Notification.objects.all()
        else:
            notifications = Notification.objects.filter(
                recipient=request.user,
                business_id__in=_businesses_for_user(request.user),
            )
    else:
        notifications = Notification.objects.filter(recipient=request.user)
    return render(request, 'employees/notifications.html', {
        'notifications': notifications.select_related('salary_request__employee', 'leave_request__employee'),
        'unread_count': notifications.filter(is_read=False).count(),
    })


@login_required
@require_POST
def mark_notifications_read(request):
    Notification.objects.filter(
        recipient=request.user,
        notification_type='leave_review',
        is_read=False,
    ).update(is_read=True)
    return JsonResponse({'ok': True})


@login_required
def notification_detail(request, pk):
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.is_read = True
    notification.save(update_fields=['is_read'])
    return render(request, 'employees/notification_detail.html', {'notification': notification})


@management_required
@require_POST
def review_salary_request(request, pk, decision):
    salary_request = get_object_or_404(SalaryRequest, pk=pk)
    if not request.user.is_superuser and salary_request.business_id not in _businesses_for_user(request.user):
        raise PermissionDenied
    decision_map = {'Approved': SalaryRequest.ACCEPTED, 'Rejected': SalaryRequest.REJECTED}
    if decision not in decision_map:
        return JsonResponse({'success': False, 'message': 'Invalid decision.'}, status=400)
    if salary_request.status != SalaryRequest.PENDING:
        messages.error(request, 'Only pending requests can be reviewed.')
        return redirect('salary_requests_list')
    salary_request.status = decision_map[decision]
    salary_request.reviewed_by = request.user
    salary_request.reviewed_at = timezone.now()
    salary_request.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])
    Notification.objects.create(
        recipient=salary_request.employee,
        business=salary_request.business,
        salary_request=salary_request,
        notification_type='salary_request_review',
        message=f'Your {salary_request.request_type} request was {salary_request.get_status_display().lower()}.',
    )
    messages.success(request, f'Request {decision.lower()}.')
    return redirect('salary_requests_list')


@management_required
@require_POST
def process_salary_request(request, pk):
    salary_request = get_object_or_404(SalaryRequest, pk=pk)
    if not request.user.is_superuser and salary_request.business_id not in _businesses_for_user(request.user):
        raise PermissionDenied
    if salary_request.status != SalaryRequest.ACCEPTED:
        messages.error(request, 'Only accepted requests can be processed.')
        return redirect('salary_requests_list')
    employee = Employee.objects.filter(user=salary_request.employee).first()
    if employee is None:
        messages.error(
            request,
            'This request cannot be processed because the employee profile is not linked to the account.',
        )
        return redirect('salary_requests_list')
    period = timezone.localdate().strftime('%Y-%m')
    payment, _ = SalaryPayment.objects.get_or_create(
        employee=employee,
        period=period,
        defaults={'amount_paid': Decimal('0.00')},
    )
    payment.amount_paid = min(payment.salary_due, payment.amount_paid + (salary_request.amount or Decimal('0.00')))
    payment.date_paid = timezone.localdate()
    payment.save(update_fields=['amount_paid', 'date_paid', 'updated_at'])
    salary_request.status = SalaryRequest.PROCESSED
    salary_request.processed_at = timezone.now()
    salary_request.save(update_fields=['status', 'processed_at'])
    Notification.objects.create(
        recipient=salary_request.employee,
        business=salary_request.business,
        salary_request=salary_request,
        notification_type='salary_request_review',
        message=f'Your {salary_request.request_type} request has been processed and paid.',
    )
    messages.success(request, f'Payment processed for {employee.name}.')
    return redirect('salary_requests_list')

@login_required
def delete_salary_request(request, pk):
    req = get_object_or_404(SalaryRequest, pk=pk)
    # Kaliya admin ama qofka iska leh request-ka ayaa tirtiri kara
    if request.user == req.employee or (request.user.is_staff and (
        request.user.is_superuser or req.business_id in _businesses_for_user(request.user)
    )):
        if request.method == 'POST':
            req.delete()
            messages.success(request, "Salary request deleted.")
            return redirect('salary_requests_list')
        return render(request, 'employees/confirm_delete_salary.html', {'req': req})
    else:
        messages.error(request, "You are not allowed to delete this request.")
        return redirect('salary_requests_list')