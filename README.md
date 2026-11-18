# Weather Universe

A database-driven weather monitoring and alert system built with **Django** (templates for the front end) and **SQLite** / soon to use **PostgreSQL/Supabase**. IM2 project, CSIT327-G1.

**Phase 1 (this commit range): Account feature**
- Registration with validation (required fields, email format, unique email, matching password confirmation) and hashed passwords
- Login / logout with error and success messages; protected pages redirect logged-out visitors to the login page
- Two roles, `USER` and `ADMIN`, each with its own dashboard; opening the other role's dashboard URL returns 403
- Profile page and edit form (name, email, contact number, profile photo); users can only see and edit their own profile

## Setup

```bash
python -m venv venv
venv\Scripts\activate          # Windows   (macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt

copy .env.example .env         # macOS/Linux: cp .env.example .env
# edit .env: SECRET_KEY and your PostgreSQL or Supabase credentials
```

Create an empty PostgreSQL database named `weather_universe` (or point `.env` at your Supabase project:
host `db.<project>.supabase.co`, port `5432`, user `postgres`, `DB_SSLMODE=require`). Then:

```bash
python manage.py migrate
python manage.py createsuperuser     # creates an ADMIN account (asks for email, full name, password)
python manage.py runserver
python manage.py test accounts       # runs the test suite (needs a PostgreSQL user that can create databases)
```

Open http://127.0.0.1:8000/. New sign-ups are always `USER`; administrators are created with `createsuperuser` or by changing a user's role in the Django admin (`/admin/`).

## Notes
- Secrets live in `.env`, which is git-ignored. Never commit it.
- The `users` table matches the SDD (`user_id` primary key, unique `email`, CHECK on `role`). Django stores the hashed password in the `password` column.
