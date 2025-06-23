from django.db import models
import uuid
from django.conf import settings
from django.contrib.auth.models import User

class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='%(class)s_created',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='%(class)s_updated',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        abstract = True

class Client(BaseModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='client_profile')
    email_id = models.EmailField(unique=True)
    company_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    company_type = models.CharField(max_length=100, blank=True, null=True)
    target_audience = models.CharField(max_length=255, blank=True, null=True)
    platforms = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.company_name} ({self.email_id})"

class Campaign(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    max_posts_per_day = models.IntegerField(default=5)

    def __str__(self):
        return f"{self.name} ({self.start_date} to {self.end_date})"
    
class CampaignPost(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='posts')
    date = models.DateField()
    platform = models.CharField(max_length=50)
    time = models.TimeField()
    content = models.TextField(blank=True, null=True)
    target_audience = models.CharField(max_length=255)
    keywords = models.CharField(max_length=255)
    tone = models.CharField(max_length=50)
    length = models.CharField(max_length=50)
    call_to_action = models.CharField(max_length=255)

    image_prompt = models.CharField(max_length=255, blank=True)
    text_prompt = models.TextField(blank=True, null=True)
    text = models.TextField(blank=True, null=True)
    image_url = models.URLField(blank=True, null=True)
    image_file = models.ImageField(
        upload_to="generated_images/",
        blank=True,
        null=True,
        help_text="Locally downloaded (and later edited) AI image"
    )

    is_prompt_generated = models.BooleanField(default=False)
    is_content_generated = models.BooleanField(default=False)
    posted = models.BooleanField(default=False)

    def scheduled_datetime(self):
        from datetime import datetime
        return datetime.combine(self.date, self.time)

class Post(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    image_url = models.URLField(
        blank=True,
        null=True,
        help_text="Remote URL returned by OpenAI (for reference/fallback)"
    )
    image_file = models.ImageField(
        upload_to="generated_images/",
        blank=True,
        null=True,
        help_text="Locally downloaded (and later edited) AI image"
    )
    text_prompt = models.TextField()
    image_prompt = models.TextField()
    platform = models.CharField(max_length=20, default='manual')
    text = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Post by {self.user.username} on {self.created_on:%Y-%m-%d}"

class ScheduledPost(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='posts')
    scheduled_time = models.DateTimeField()
    platform = models.CharField(max_length=30, choices=[
        ('facebook', 'Facebook'),
        ('instagram', 'Instagram'),
        ('twitter', 'Twitter'),
        ('reddit', 'Reddit'),
        ('linkedin', 'LinkedIn')
    ])
    caption = models.TextField(blank=True, null=True)
    media_url = models.URLField(blank=True, null=True)
    media_file = models.FileField(upload_to="media/", blank=True, null=True)
    posted = models.BooleanField(default=False)

    def __str__(self):
        return f"Scheduled for {self.scheduled_time.strftime('%Y-%m-%d %H:%M')} on {self.platform}"

class PromptLog(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    prompt_input = models.TextField()
    response_text = models.TextField(blank=True, null=True)
    response_image_prompt = models.TextField(blank=True, null=True)
    model_used = models.CharField(max_length=100, default='gpt-4o')

    def __str__(self):
        return f"Prompt by {self.user.username} on {self.created_on:%Y-%m-%d}"

class UserCredential(BaseModel):
    PLATFORM_CHOICES = [
        ('facebook', 'Facebook'),
        ('instagram', 'Instagram'),
        ('twitter', 'Twitter'),
        ('reddit', 'Reddit'),
        ('linkedin', 'LinkedIn'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="platform_credentials"
    )
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    api_data = models.JSONField(blank=True, null=True)

    class Meta:
        unique_together = ('user', 'platform')
        verbose_name = "User Credential"
        verbose_name_plural = "User Credentials"

    def __str__(self):
        return f"{self.user.username} - {self.platform}"