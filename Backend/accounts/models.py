from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = email.lower().strip()

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        # Ensure email is normalized here as well
        if email:
            email = email.lower().strip()
            
        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('developer', 'Developer'),
        ('standard', 'Standard User'),
    ]

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='standard')
    
    # Token tracking
    tokens_allocated = models.IntegerField(default=2)  # Free tier default
    tokens_used = models.IntegerField(default=0)
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    def save(self, *args, **kwargs):
        # Exclusive Developer role for Kaashifameen32@gmail.com
        if self.email.lower().strip() == 'kaashifameen32@gmail.com':
            self.role = 'developer'
            self.tokens_allocated = 999999999  # Unlimited tokens
            self.is_staff = True
            self.is_superuser = True
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.email)

    @property
    def has_free_tokens(self):
        if self.role == 'developer':
            return True
        return self.tokens_used < self.tokens_allocated

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
