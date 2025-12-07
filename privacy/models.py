# models.py
from django.db import models

class BaseContent(models.Model):
    image = models.ImageField(upload_to="content/", null=True, blank=True)
    description = models.TextField()
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-last_updated"]

    def __str__(self):
        return self.description[:50]


class PrivacyPolicy(BaseContent):
    class Meta:
        verbose_name = "Privacy Policy"
        verbose_name_plural = "Privacy Policy"


class AboutUs(BaseContent):
    class Meta:
        verbose_name = "About Us"
        verbose_name_plural = "About Us"


class TermsConditions(BaseContent):
    class Meta:
        verbose_name = "Terms & Conditions"
        verbose_name_plural = "Terms & Conditions"


class SubmitQuery(models.Model):
    name = models.CharField(max_length=155, null=True, blank=True)
    email = models.EmailField(db_index=True)
    message = models.TextField(max_length=500, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.email} - {self.created_at.date()}"
