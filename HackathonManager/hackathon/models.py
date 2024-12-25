from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class AdminUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(email, password, **extra_fields)


class AdminUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = AdminUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

class Participant(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    skills = models.TextField()
    registration_date = models.DateTimeField(auto_now_add=True)

class Theme(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()

class Submission(models.Model):
    team_name = models.CharField(max_length=255)
    project_name = models.CharField(max_length=255)
    github_link = models.URLField()
    summary_details = models.FileField(upload_to='summary_details/', blank=True, null=True)
    other_docs = models.FileField(upload_to='other_docs/', blank=True, null=True)
    theme = models.ForeignKey('Theme', on_delete=models.CASCADE)  # Link submission to theme
    timestamp = models.DateTimeField(auto_now_add=True)
