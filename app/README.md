# Workout and Fitness Planner

Web application implementation of the graduation project described in `../report`.
Built with Django (MVT), SQLite, plain HTML/CSS/JavaScript and Chart.js.

## Running it

```bash
cd app
uv venv .venv && source .venv/bin/activate      # or: python -m venv .venv
pip install -r requirements.txt

python manage.py migrate
python manage.py seed_data        # exercise library (muscle groups, equipment, 33 exercises)
python manage.py seed_demo        # optional demo user with 10 weeks of logged sessions
python manage.py createsuperuser

python manage.py runserver
```

Then open http://127.0.0.1:8000/ and log in.

Demo credentials created by `seed_demo`: `demo / demo12345678`.

## Structure

```
app/
├── manage.py
├── config/            settings, root URLs, WSGI/ASGI
├── accounts/          User + UserProfile, registration, login, profile
├── exercises/         MuscleGroup, Equipment, Exercise + links, library views, admin CRUD
├── plans/             WorkoutPlan, PlanExercise, PlanSet
├── workouts/          WorkoutSession, SessionExercise, SessionSet, PersonalRecord + services
├── analytics/         dashboard, weekly volume chart, improvement metrics
├── templates/         base + per-app templates (responsive)
├── static/            css/style.css, css/rtl.css, js/app.js (Chart.js)
└── locale/            Arabic translations (django.po / django.mo)
```

Database tables follow the schema in Chapter 3 of the report (column names are kept
with `db_column`, e.g. `User_ID`, `Session_Exercise_ID`).

## Routes

| Area | URL | Requirement |
|---|---|---|
| Auth | `/accounts/register/`, `/accounts/login/`, `/accounts/logout/`, `/accounts/profile/` | FREQ-1, 2, 13 |
| Exercise library | `/exercises/` (search + filters), `/exercises/<id>/` | FREQ-3, 14 |
| Admin CRUD | `/exercises/manage/` (administrators only) + Django admin | FREQ-15 |
| Plans | `/plans/`, `/plans/new/`, `/plans/<id>/`, edit/delete, sets | FREQ-4–7 |
| Sessions | `/sessions/`, `/sessions/<id>/`, `/sessions/start/<plan>/`, log set, complete | FREQ-8 |
| Records | `/sessions/records/` | FREQ-11 |
| Analytics | `/analytics/`, `/analytics/progress/` | FREQ-9, 10, 12 |
| Language | `/i18n/setlang/` (English / Arabic, RTL) | i18n |

## Key logic

- **Personal records** (`workouts/services.py`): every logged set is compared with the
  user's stored best for `max_weight`, `max_reps`, `max_volume` and `max_duration`;
  improvements update `PersonalRecord` and flag `SessionSet.Is_Personal_Record`.
- **Improvement metrics** (`analytics/services.py`): first logged value vs. current best
  per exercise, weekly volume buckets, weekly training streak.
- **Sessions**: starting a session copies the plan's exercises into `SessionExercise`;
  finishing computes duration from `Started_At`/`Ended_At` and stores rating/notes.

## Tests

```bash
python manage.py test
```

35 tests cover registration/authentication, library filtering, plan building,
set logging, personal-record detection, improvement metrics, the dashboard pages
and language switching (including Arabic data names).

## Language (English / Arabic)

- `LocaleMiddleware` + `LANGUAGES = [("en", "English"), ("ar", "العربية")]` in `config/settings.py`.
- A language switcher in `templates/base.html` posts to Django's built-in
  `set_language` view (`/i18n/setlang/`); the choice is stored in the session.
  The dropdown submits itself when the selection changes (`static/js/app.js`), so the
  language is applied immediately and the user stays on the current page; the Switch
  button remains only as a no-JavaScript fallback.
- `<html lang="..." dir="...">` is set from `{% get_current_language %}` and
  `{% get_current_language_bidi %}`, and `static/css/rtl.css` is loaded only for RTL
  languages (mirrored layout, right-aligned text, RTL Chart.js axes).
- Every user-facing string in templates, model labels and view messages goes through
  `{% trans %}` / `{% blocktrans %}` or `gettext_lazy` / `gettext`.
- **Data names** are not UI strings, so they are stored, not translated: `Muscle_Group`,
  `Equipment` and `Exercise` have an optional `Name_Ar` column and a `display_name()`
  helper that returns the Arabic name when Arabic is active. `seed_data` fills both
  languages, so the library tags, filters and detail pages show Arabic names in Arabic mode.
  Chart labels are passed to `static/js/app.js` through `data-*` attributes rendered with
  `{% trans %}`.
- Text the user typed (plan names, session names, notes, descriptions, instructions) is
  shown exactly as stored — it is data, not interface text.

Translations live in `locale/ar/LC_MESSAGES/django.po`. After changing any string:

```bash
python manage.py makemessages -l ar   # needs the gettext package
python manage.py compilemessages      # builds locale/ar/LC_MESSAGES/django.mo
```

`shell.nix` already includes `gettext`, so both commands work inside the dev shell.

## Notes

- Passwords are stored hashed through Django's auth system (`AUTH_USER_MODEL = accounts.User`).
- CSRF protection, login-required views and per-user ownership checks are enabled.
- Chart.js is loaded from a CDN; if it is unavailable the dashboard falls back to the table view.
- `DEBUG = True` and the secret key are development defaults — change them before deploying.
