import io
import tempfile

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

User = get_user_model()
PASSWORD = 'Str0ng-Pass!word'


def make_user(email='user@example.com', role=User.Role.USER, **extra):
    extra.setdefault('full_name', 'Test Person')
    return User.objects.create_user(email=email, password=PASSWORD, role=role, **extra)


def png_bytes():
    buf = io.BytesIO()
    Image.new('RGB', (10, 10), 'teal').save(buf, 'PNG')
    return buf.getvalue()


class RegistrationTests(TestCase):
    url = reverse('accounts:register')

    def payload(self, **over):
        data = {'full_name': 'Juan Dela Cruz', 'email': 'juan@example.com',
                'password1': PASSWORD, 'password2': PASSWORD}
        data.update(over)
        return data

    def test_page_loads(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_successful_registration_hashes_password_and_shows_message(self):
        response = self.client.post(self.url, self.payload(), follow=True)
        self.assertRedirects(response, reverse('accounts:login'))
        self.assertContains(response, 'Your account was created')
        user = User.objects.get(email='juan@example.com')
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.password.startswith('pbkdf2_'))
        self.assertTrue(user.check_password(PASSWORD))
        self.assertEqual(user.role, User.Role.USER)

    def test_role_cannot_be_chosen_by_the_visitor(self):
        self.client.post(self.url, self.payload(role='ADMIN', is_staff='on', is_superuser='on'))
        user = User.objects.get(email='juan@example.com')
        self.assertEqual(user.role, User.Role.USER)
        self.assertFalse(user.is_staff or user.is_superuser)

    def test_required_fields(self):
        response = self.client.post(self.url, {})
        for field in ('full_name', 'email', 'password1', 'password2'):
            self.assertIn(field, response.context['form'].errors)
        self.assertContains(response, 'Registration failed')
        self.assertEqual(User.objects.count(), 0)

    def test_invalid_email_format(self):
        response = self.client.post(self.url, self.payload(email='not-an-email'))
        self.assertIn('email', response.context['form'].errors)
        self.assertEqual(User.objects.count(), 0)

    def test_duplicate_email_is_rejected_case_insensitively(self):
        make_user('juan@example.com')
        response = self.client.post(self.url, self.payload(email='JUAN@Example.com'))
        self.assertContains(response, 'already exists')
        self.assertEqual(User.objects.count(), 1)

    def test_password_confirmation_must_match(self):
        response = self.client.post(self.url, self.payload(password2='Different-Pass1!'))
        self.assertIn('password2', response.context['form'].errors)
        self.assertEqual(User.objects.count(), 0)

    def test_weak_password_is_rejected(self):
        response = self.client.post(self.url, self.payload(password1='12345678', password2='12345678'))
        self.assertIn('password2', response.context['form'].errors)

    def test_logged_in_user_is_redirected_away_from_register(self):
        self.client.force_login(make_user())
        self.assertRedirects(self.client.get(self.url), reverse('accounts:user_dashboard'))


class LoginLogoutTests(TestCase):
    login_url = reverse('accounts:login')

    def test_user_goes_to_user_dashboard(self):
        make_user('a@example.com')
        response = self.client.post(self.login_url, {'username': 'a@example.com', 'password': PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('accounts:user_dashboard'))
        self.assertContains(response, 'Welcome back')

    def test_admin_goes_to_admin_dashboard(self):
        make_user('admin@example.com', role=User.Role.ADMIN)
        response = self.client.post(self.login_url, {'username': 'admin@example.com', 'password': PASSWORD}, follow=True)
        self.assertRedirects(response, reverse('accounts:admin_dashboard'))

    def test_login_email_is_case_insensitive(self):
        make_user('a@example.com')
        response = self.client.post(self.login_url, {'username': 'A@Example.COM', 'password': PASSWORD})
        self.assertRedirects(response, reverse('accounts:redirect'), fetch_redirect_response=False)

    def test_invalid_credentials_show_error(self):
        make_user('a@example.com')
        response = self.client.post(self.login_url, {'username': 'a@example.com', 'password': 'wrong'})
        self.assertContains(response, 'Invalid email or password')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_unknown_account_shows_same_error(self):
        response = self.client.post(self.login_url, {'username': 'nobody@example.com', 'password': PASSWORD})
        self.assertContains(response, 'Invalid email or password')

    def test_inactive_account_cannot_log_in(self):
        make_user('off@example.com', is_active=False)
        response = self.client.post(self.login_url, {'username': 'off@example.com', 'password': PASSWORD})
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(response.status_code, 200)

    def test_logout_ends_session(self):
        self.client.force_login(make_user())
        response = self.client.post(reverse('accounts:logout'), follow=True)
        self.assertRedirects(response, self.login_url)
        self.assertContains(response, 'logged out')
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertRedirects(self.client.get(reverse('accounts:user_dashboard')),
                             f"{self.login_url}?next={reverse('accounts:user_dashboard')}")

    def test_logout_requires_post(self):
        self.client.force_login(make_user())
        self.assertEqual(self.client.get(reverse('accounts:logout')).status_code, 405)
        self.assertIn('_auth_user_id', self.client.session)

    def test_root_redirects_to_login_when_logged_out(self):
        response = self.client.get('/', follow=True)
        self.assertEqual(response.redirect_chain[-1][0].split('?')[0], self.login_url)


class ProtectedPageTests(TestCase):
    def test_logged_out_users_are_sent_to_login(self):
        for name in ('user_dashboard', 'admin_dashboard', 'profile', 'profile_edit', 'redirect'):
            url = reverse(f'accounts:{name}')
            response = self.client.get(url)
            self.assertRedirects(response, f"{reverse('accounts:login')}?next={url}", msg_prefix=name)


class RoleDashboardTests(TestCase):
    def setUp(self):
        self.member = make_user('member@example.com')
        self.admin = make_user('admin@example.com', role=User.Role.ADMIN, full_name='Admin Person')

    def test_user_sees_own_dashboard_and_nav(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse('accounts:user_dashboard'))
        self.assertContains(response, 'My locations')
        self.assertContains(response, 'My Dashboard')
        self.assertNotContains(response, 'Administrator dashboard')
        self.assertNotContains(response, 'Admin Dashboard')

    def test_admin_sees_own_dashboard_with_real_counts(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('accounts:admin_dashboard'))
        self.assertContains(response, 'Administrator dashboard')
        self.assertEqual(response.context['total_users'], 2)
        self.assertEqual(response.context['total_admins'], 1)
        self.assertContains(response, 'member@example.com')

    def test_user_cannot_open_admin_dashboard(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse('accounts:admin_dashboard'))
        self.assertEqual(response.status_code, 403)
        self.assertNotContains(response, 'member@example.com', status_code=403)

    def test_admin_cannot_open_user_dashboard(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('accounts:user_dashboard')).status_code, 403)

    def test_dashboard_redirect_follows_role(self):
        self.client.force_login(self.member)
        self.assertRedirects(self.client.get(reverse('accounts:redirect')), reverse('accounts:user_dashboard'))
        self.client.force_login(self.admin)
        self.assertRedirects(self.client.get(reverse('accounts:redirect')), reverse('accounts:admin_dashboard'))

    def test_next_parameter_cannot_bypass_role_check(self):
        admin_url = reverse('accounts:admin_dashboard')
        response = self.client.post(f"{reverse('accounts:login')}?next={admin_url}",
                                    {'username': 'member@example.com', 'password': PASSWORD}, follow=True)
        self.assertEqual(response.status_code, 403)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ProfileTests(TestCase):
    def setUp(self):
        self.user = make_user('me@example.com', full_name='Me Myself', contact_number='0917 123 4567')
        self.other = make_user('other@example.com', full_name='Other Person')
        self.client.force_login(self.user)

    def test_profile_shows_only_own_information(self):
        response = self.client.get(reverse('accounts:profile'))
        self.assertContains(response, 'Me Myself')
        self.assertContains(response, '0917 123 4567')
        self.assertNotContains(response, 'other@example.com')

    def test_update_profile(self):
        response = self.client.post(reverse('accounts:profile_edit'), {
            'full_name': 'New Name', 'email': 'new@example.com', 'contact_number': '+63 917 000 1111'}, follow=True)
        self.assertRedirects(response, reverse('accounts:profile'))
        self.assertContains(response, 'Your profile was updated')
        self.user.refresh_from_db()
        self.assertEqual((self.user.full_name, self.user.email, self.user.contact_number),
                         ('New Name', 'new@example.com', '+63 917 000 1111'))

    def test_cannot_take_another_users_email(self):
        response = self.client.post(reverse('accounts:profile_edit'), {
            'full_name': 'Me Myself', 'email': 'OTHER@example.com', 'contact_number': ''})
        self.assertContains(response, 'already uses this email')
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'me@example.com')

    def test_keeping_own_email_is_allowed(self):
        response = self.client.post(reverse('accounts:profile_edit'), {
            'full_name': 'Me Again', 'email': 'me@example.com', 'contact_number': ''})
        self.assertRedirects(response, reverse('accounts:profile'))

    def test_invalid_contact_number(self):
        response = self.client.post(reverse('accounts:profile_edit'), {
            'full_name': 'Me Myself', 'email': 'me@example.com', 'contact_number': 'abc'})
        self.assertIn('contact_number', response.context['form'].errors)

    def test_cannot_edit_someone_elses_profile(self):
        self.client.post(reverse('accounts:profile_edit'), {
            'user_id': self.other.pk, 'pk': self.other.pk,
            'full_name': 'Hacked', 'email': 'other@example.com', 'contact_number': ''})
        self.other.refresh_from_db()
        self.assertEqual(self.other.full_name, 'Other Person')

    def test_role_cannot_be_changed_from_profile(self):
        self.client.post(reverse('accounts:profile_edit'), {
            'full_name': 'Me Myself', 'email': 'me@example.com', 'contact_number': '', 'role': 'ADMIN'})
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, User.Role.USER)

    def test_upload_profile_photo(self):
        photo = SimpleUploadedFile('me.png', png_bytes(), content_type='image/png')
        response = self.client.post(reverse('accounts:profile_edit'), {
            'full_name': 'Me Myself', 'email': 'me@example.com', 'contact_number': '', 'profile_photo': photo})
        self.assertRedirects(response, reverse('accounts:profile'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.profile_photo.name.startswith('profile_photos/'))

    def test_rejects_non_image_upload(self):
        bad = SimpleUploadedFile('x.png', b'not an image', content_type='image/png')
        response = self.client.post(reverse('accounts:profile_edit'), {
            'full_name': 'Me Myself', 'email': 'me@example.com', 'contact_number': '', 'profile_photo': bad})
        self.assertIn('profile_photo', response.context['form'].errors)


class DatabaseConstraintTests(TestCase):
    def test_invalid_role_is_blocked_by_the_database(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(email='x@example.com', password=PASSWORD, full_name='X', role='HACKER')

    def test_duplicate_email_is_blocked_by_the_database(self):
        make_user('dup@example.com')
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(email='dup@example.com', password=PASSWORD, full_name='Y')

    def test_superuser_gets_admin_role(self):
        admin = User.objects.create_superuser(email='root@example.com', password=PASSWORD, full_name='Root')
        self.assertEqual(admin.role, User.Role.ADMIN)
        self.assertTrue(admin.is_staff and admin.is_superuser)
