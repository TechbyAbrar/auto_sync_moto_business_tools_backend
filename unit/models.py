from django.db import models
from django.conf import settings


class RegisterUnit(models.Model):
    registrar = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="registered_units"
    )

    vin = models.CharField(
        max_length=25,
        unique=True,
        db_index=True
    )

    brand = models.CharField(max_length=50)
    model = models.CharField(max_length=50)

    year = models.PositiveSmallIntegerField()  # Better than PositiveIntegerField

    purchase_date = models.DateField()

    store_location = models.CharField(max_length=100)

    additional_notes = models.TextField(blank=True, null=True)

    image = models.ImageField(
        upload_to='unit_images/',
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Registered Unit"
        verbose_name_plural = "Registered Units"

    def __str__(self):
        return f"{self.brand} {self.model} ({self.vin})"



class ScheduleService(models.Model):
    unit = models.ForeignKey(
        RegisterUnit,
        on_delete=models.CASCADE,
        related_name="service_schedules"
    )

    details = models.TextField()
    location = models.CharField(max_length=100)
    appointment_date = models.DateField()

    has_serviced_before = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-appointment_date"]
        verbose_name = "Service Schedule"
        verbose_name_plural = "Service Schedules"

    def __str__(self):
        return f"Service for {self.unit} on {self.appointment_date}"


# sell

class SellUnit(models.Model):
    unit = models.ForeignKey(
        RegisterUnit,
        on_delete=models.CASCADE,
        related_name="sell_listings"
    )

    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="units_for_sale"
    )

    additional_details = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Sell Unit"
        verbose_name_plural = "Sell Units"

    def __str__(self):
        return f"{self.unit} for sale by {self.seller}"