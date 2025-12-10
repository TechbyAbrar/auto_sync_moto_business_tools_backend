from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from account.models import UserAuth
from unit.models import ScheduleService, SellUnit



@receiver([post_save, post_delete], sender=UserAuth)
@receiver([post_save, post_delete], sender=ScheduleService)
@receiver([post_save, post_delete], sender=SellUnit)
def invalidate_dashboard_cache(sender, **kwargs):
    cache.delete('dashboard_stats')
