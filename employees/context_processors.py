import os

from .models import Notification


def notification_count(request):
    if not request.user.is_authenticated:
        return {'unread_notifications': 0, 'notif_count': 0, 'notif_items': []}
    notifications = Notification.objects.filter(recipient=request.user, is_read=False)
    leave_notifications = notifications.filter(
        notification_type='leave_review',
        leave_request__isnull=False,
    ).select_related('leave_request').order_by('-created_at')
    return {
        'unread_notifications': notifications.count(),
        'notif_count': leave_notifications.count(),
        'notif_items': leave_notifications[:6],
    }


def demo_mode(request):
    return {
        'demo_mode': os.environ.get('DEMO_MODE', '').lower() == 'true',
    }
