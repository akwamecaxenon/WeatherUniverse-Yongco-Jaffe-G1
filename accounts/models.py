from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models


class UserManager(BaseUserManager):
    """Creates users that log in with their email address."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra):
        if not email:
            raise ValueError('An email address is required.')
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra)
        user.set_password(password)  # hashes the password; never stored as plain text
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault('role', User.Role.USER)
        extra.setdefault('is_staff', False)
        extra.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra['role'] = User.Role.ADMIN
        extra['is_staff'] = True
        extra['is_superuser'] = True
        return self._create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    """Weather Universe account (SDD table: users)."""

    class Role(models.TextChoices):
        USER = 'USER', 'Registered User'
        ADMIN = 'ADMIN', 'Administrator'

    user_id = models.AutoField(primary_key=True)
    email = models.EmailField('email address', max_length=100, unique=True)
    full_name = models.CharField(max_length=100)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.USER)
    contact_number = models.CharField(
        max_length=20, blank=True,
        validators=[RegexValidator(r'^\+?[0-9 ()-]{7,20}$', 'Enter a valid contact number.')],
    )
    profile_photo = models.ImageField(upload_to='profile_photos/', blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']

    class Meta:
        db_table = 'users'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(role__in=['USER', 'ADMIN']),
                name='users_role_valid',
            ),
        ]

    def __str__(self):
        return self.email

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN

    def get_full_name(self):
        return self.full_name

    def get_short_name(self):
        return self.full_name.split(' ')[0] if self.full_name else self.email
