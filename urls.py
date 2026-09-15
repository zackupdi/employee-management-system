from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('attendance/', views.attendance, name='attendance'),
    path('employees/', views.employee_list, name='employee_list'),
    path('employees/add/', views.employee_create, name='employee_create'),
    path('employees/<int:pk>/update/', views.employee_update, name='employee_update'),
    path('employees/<int:pk>/delete/', views.employee_delete, name='employee_delete'),
    path('employees/<int:pk>/', views.employee_detail, name='employee_detail'),
    path('home/', views.home, name='home'),
    path('request-salary/', views.submit_salary_request, name='request_salary'),
    path('attendance-report/', views.attendance_report, name='attendance_report'),
    path('absent_today/', views.absent_today, name='absent_today'),
    path('clear_attendance/', views.clear_attendance, name='clear_attendance'),
    path('delete_all_employees/', views.delete_all_employees, name='delete_all_employees'),
    path('export-today-attendance/', views.export_today_attendance, name='export_today_attendance'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('salary/requests/', views.salary_requests_list, name='salary_requests_list'),
    path('salary/requests/<int:pk>/delete/', views.delete_salary_request, name='delete_salary_request'),
]
