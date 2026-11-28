# Workout and Fitness Planner — منظم التمارين اللياقة

A web application for planning and tracking strength / cardio training: build an exercise
library, create reusable workout plans, run and log training sessions, and follow your
progress through personal records, improvement metrics and analytics dashboards.

**Stack:** Django (MVT) + SQLite + plain HTML/CSS and a small vanilla-JS layer with Chart.js.
Bilingual interface (English / Arabic with full RTL layout), responsive, built on Django's auth
system with a custom user model.

---

## What the app does

| Area | What you get |
|---|---|
| Accounts | Email registration, username or email login, optional Google login, and fitness profile |
| Exercise library | Browse, search and filter exercises by muscle group, equipment, type and difficulty |
| Workout programs | Build custom programs from freely named and ordered workout days; add exercises, sets, reps, weight, duration and rest |
| Training sessions | Start a session from a plan, log each set live, finish with duration / rating / notes |
| Personal records | Every logged set is checked against your best `max_weight`, `max_reps`, `max_volume`, `max_duration` |
| Analytics | Summary cards, weekly training volume chart, improvement metrics (first value vs. current best), training streak |
| Administration | Admin CRUD for muscle groups, equipment and the exercise library (soft delete via `Is_Active`) |
| Language | Switch between English and Arabic at any time (`/i18n/setlang/`), Arabic renders right-to-left |

---

## Prerequisites

Only **[uv](https://docs.astral.sh/uv/)** is required. uv is a fast Python package manager that can
also download and manage Python itself, so you do not need to install Python separately.
Python **3.12+** is used (uv will fetch it automatically if it is missing).

### Install uv

**Windows (PowerShell)**

```powershell
winget install --id astral-sh.uv -e
# or:
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**macOS (or Linux) via the official installer**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**macOS via Homebrew**

```bash
brew install uv
```

**Linux via your package manager / pipx** (or just use the `curl` installer above)

```bash
pipx install uv        # or: pip install --user uv
```

Then restart the terminal and check it works:

```bash
uv --version
```

---

## Quick start (Windows, macOS and Linux)

All commands below are identical on every OS except the shell you type them in
(PowerShell / `cmd` on Windows, `bash` / `zsh` on macOS and Linux).

```bash
# 1. Get the code
git clone https://github.com/nashamri-uni/fitness.git
cd fitness/app            # the Django project lives in app/

# 2. Create a virtual environment (uv downloads Python 3.12 if needed)
uv venv .venv --python 3.12

# 3. Install the dependencies
uv pip install -r requirements.txt

# 4. Create the database and fill the exercise library
uv run python manage.py migrate
uv run python manage.py seed_data     # 12 muscle groups, 24 equipment items, 128 catalog entries (111 active)

# 5. Optional: demo user with several weeks of logged sessions
uv run python manage.py seed_demo     # login: demo / demo12345678
#    other options: uv run python manage.py seed_demo --user nasser --password 123123

# 6. Create your own admin account
uv run python manage.py createsuperuser

# 7. Run it
uv run python manage.py runserver
```

The optional root `exercise_dataset/` folder is ignored by Git. The seed command
uses only the selected, rights-cleared local exercise images under `app/static/exercises/`.

Open <http://127.0.0.1:8000/> — register an account or log in with the demo user.
The Django admin is at <http://127.0.0.1:8000/admin/>.

> `uv run` finds `.venv` automatically, so activating it is optional. If you prefer the classic
> workflow, activate it first and then run the plain `python manage.py …` commands:
>
> | OS | Activate the environment |
> |---|---|
> | Windows PowerShell | `.venv\Scripts\Activate.ps1` |
> | Windows `cmd` | `.venv\Scripts\activate.bat` |
> | macOS / Linux | `source .venv/bin/activate` |

### Other useful commands

```bash
uv run python manage.py test          # run the test suite
uv run python manage.py changepassword <username>
uv run python manage.py shell         # Django shell inside the environment
```

### Email and Google authentication

Password registration requires a unique username and a valid email address. You can sign in
with either identifier. Existing users with blank or shared legacy addresses can still use
their unambiguous usernames. Password hashing and admin sessions use Django authentication.

#### Set up Google for local development

1. Create or select a Google Cloud project and open **Google Auth Platform**. In **Branding**,
   configure the FitPlanner app name, support email and developer contact details.
2. In **Audience**, choose **External** and use **Testing** for local trials. Add the Google
   accounts that will test the integration under **Test users**. For a workspace-restricted
   app, choose the audience allowed by your organization instead.
3. In **Data Access**, use `openid`, `email`, and `profile` as the identity scopes.
4. In **Clients**, create an OAuth client of type **Web application**. Add this exact
   **Authorized redirect URI**.

   ```text
   http://127.0.0.1:8000/accounts/google/login/callback/
   ```

   To use `localhost`, also register `http://localhost:8000/accounts/google/login/callback/`
   and use that host for the entire browser flow.
5. From `app/`, copy `.env.example` to `.env` and set `GOOGLE_CLIENT_ID` and
   `GOOGLE_CLIENT_SECRET` locally. Exported environment variables take precedence.
   Keep the client secret out of source control, browsers and logs.
6. Install `requirements.txt`, back up any existing database, and run
   `uv run python manage.py migrate`. Start `uv run python manage.py runserver`.
7. Visit `http://127.0.0.1:8000/accounts/login/` and choose **Continue with Google**.
   A new Google user completes their profile before going to the dashboard. To connect an
   existing account, first sign in with its password and use **Profile → Account security**.

The Google button appears when both environment variables are set. The OAuth callback checks
state, PKCE, the signed Google identity token and its verified email. Connections use Google's
stable subject identifier. The existing FitPlanner password is required to connect or disconnect
Google from a password account. A Google-only account can set a password after a recent Google
login, then confirm that password to disconnect Google.

[Google Auth Platform setup](https://support.google.com/cloud/answer/15544987) ·
[Google OAuth web-server flow](https://developers.google.com/identity/protocols/oauth2/web-server) ·
[Google branding guidelines](https://developers.google.com/identity/branding-guidelines) ·
[django-allauth Google provider](https://docs.allauth.org/en/latest/socialaccount/providers/google.html)

#### Existing email addresses and database migration

`accounts.0003_authentication_identity` keeps all user IDs and stored emails. On SQLite it
adds a profile-completion flag and an indexed email guard for inserts and changed addresses.
Existing blank or duplicate rows are grandfathered, and an occupied legacy address stays
reserved. Its owners can keep signing in by username. Email login refuses an identifier when
it matches more than one account. The query below identifies duplicate groups by account ID.

```sql
SELECT group_concat(id) AS account_ids, COUNT(*) AS accounts
FROM accounts_user
WHERE trim(email) <> ''
GROUP BY lower(trim(email))
HAVING COUNT(*) > 1;
```

To resolve a group, identify the legitimate address owner and let the other authenticated
users confirm distinct addresses in **Account security → Change email address**. The flow
requires the current password and a 15-minute link sent to the new address. Configure the SMTP
variables from `.env.example` to enable it. For a user whose username is itself an ambiguous
identifier, use an administrator-assisted ownership check before updating the relevant email.
The migration reports IDs for any legacy internationalized addresses stored in non-ASCII form.
Verify those addresses and normalize their domains to ASCII IDNA values before migrating.
Future migrations that rebuild the SQLite user table must reinstall its email triggers and index.

#### Deployment

Use HTTPS and configure the corresponding HTTPS OAuth redirect URI on a separate production
Google client. Set `DJANGO_DEBUG=false`, a private `DJANGO_SECRET_KEY`, and exact
`DJANGO_ALLOWED_HOSTS`. That enables HTTPS redirects and secure session and CSRF cookies.
If a trusted TLS proxy overwrites the incoming header, set
`SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")` in production settings.
Set `ALLAUTH_TRUSTED_PROXY_COUNT` to the number of trusted forwarding hops if that proxy
controls the forwarded IP chain, so rate limits use the real client address.
Use a shared cache across workers for login rate limits. The optional `DJANGO_CACHE_LOCATION`
accepts a Redis URL when the production environment has the `redis` Python client installed.
Configure an authenticated SMTP service for email verification. Exclude OAuth callback
query strings and email confirmation URLs from access logs.

### Rebuilding the Arabic translations (optional)

The compiled Arabic catalog (`app/locale/ar/LC_MESSAGES/django.mo`) is committed, so translation
works out of the box. Only if you change UI strings you need GNU **gettext** installed
(`apt install gettext`, `brew install gettext`, `choco install gettext`):

```bash
uv run python manage.py makemessages -l ar
uv run python manage.py compilemessages
```

---

## Project layout

```
fitness/
├── app/                Django project
│   ├── manage.py
│   ├── config/         settings, root URLs (incl. /i18n/setlang/), WSGI/ASGI
│   ├── accounts/       User + UserProfile, register / login / logout / profile
│   ├── exercises/      MuscleGroup, Equipment, Exercise + library and admin CRUD, seed_data
│   ├── plans/          WorkoutProgram, WorkoutPlan (workout day), PlanExercise, PlanSet
│   ├── workouts/       WorkoutSession, SessionExercise, SessionSet, PersonalRecord, seed_demo
│   ├── analytics/      summary, weekly volume, improvement metrics, dashboard / progress views
│   ├── templates/      base.html + per-app templates + form field partial
│   ├── static/         css/style.css, css/rtl.css, js/app.js (Chart.js from CDN)
│   ├── locale/ar/      Arabic translation catalog (.po / .mo)
│   └── requirements.txt
├── README.md          this file: what the app does + how to run it with uv
└── AGENTS.md          contributor guide (conventions, domain model, route map, workflow)
```

Database tables and columns mirror the schema in Chapter 3 of the design report (kept through
`db_column` / `db_table`, e.g. `User_ID`, `Session_Exercise_ID`, `Is_Personal_Record`).

---

## Main URLs

| Area | URL |
|---|---|
| Auth | `/accounts/register/`, `/accounts/login/`, `/accounts/logout/`, `/accounts/profile/` |
| Exercise library | `/exercises/` (search + filters), `/exercises/<id>/` |
| Exercise administration | `/exercises/manage/` (administrators only) + `/admin/` |
| Plans | `/plans/`, `/plans/new/`, `/plans/<id>/` (builder), save program, edit / delete |
| Sessions | `/sessions/`, `/sessions/start/<plan>/`, `/sessions/<id>/`, log set, complete |
| Personal records | `/sessions/records/` |
| Analytics | `/analytics/`, `/analytics/progress/` |
| Language | `/i18n/setlang/` |

---

## Key logic

- **Workout Builder** (`app/plans/`): `WorkoutProgram` groups the existing `WorkoutPlan` day records.
  The migration groups existing plans per owner without changing plan, exercise, set, or session IDs.
  Builder edits are validated and saved atomically; exercise/set order is generated automatically, and
  removed workout days do not erase recorded session history.
- **Personal records** (`app/workouts/services.py:evaluate_personal_record`): every logged set is
  compared with the user's stored best for `max_weight`, `max_reps`, `max_volume` and `max_duration`;
  an improved metric updates `PersonalRecord` and flags `SessionSet.Is_Personal_Record`.
- **Improvement metrics** (`app/analytics/services.py`): first logged value vs. current best per
  exercise, weekly volume buckets and the weekly training streak.
- **Sessions** (`app/workouts/services.py`): starting a session copies the plan's exercises into
  `SessionExercise`; finishing computes `Duration_Minutes` from `Started_At` / `Ended_At` and stores
  the rating and notes.
- **Ownership and safety**: every user-scoped object is fetched with `user=request.user`, views are
  `login_required`, mutating actions are POST-only with `{% csrf_token %}`, and admin pages are
  guarded by the `admin_required` decorator (`is_project_admin` or `is_staff`).

## Language (English / Arabic)

- `LocaleMiddleware` + `LANGUAGES = [("en", "English"), ("ar", "العربية")]` in `app/config/settings.py`.
- The switcher in `app/templates/base.html` posts to Django's built-in `set_language` view
  (`/i18n/setlang/`) and submits itself when the selection changes (`app/static/js/app.js`), so the
  language applies immediately and the user stays on the current page; the Switch button is the
  no-JavaScript fallback.
- `<html lang="…" dir="…">` comes from `{% get_current_language %}` and `{% get_current_language_bidi %}`;
  `app/static/css/rtl.css` is loaded only for RTL languages (mirrored layout, RTL Chart.js axes).
- Every UI string uses `{% trans %}` / `{% blocktrans %}` or `gettext_lazy` / `gettext`. **Data names**
  are stored, not translated: `MuscleGroup`, `Equipment` and `Exercise` have an optional `Name_Ar`
  column plus a `display_name()` helper, and `seed_data` fills both languages. Chart labels are passed
  to JS through `data-*` attributes rendered with `{% trans %}`. Text the user typed is shown exactly
  as stored.

## Tests

```bash
uv run python manage.py test
```

The suite covers registration/authentication, library filtering and ownership, plan and set editing,
live session logging, personal-record detection, improvement metrics and streaks, the dashboard and
progress pages, and language switching (including Arabic data names).

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `uv: command not found` | Install uv (see above), then restart the terminal so PATH is reloaded. |
| `ModuleNotFoundError: No module named 'django'` | Run the commands from `fitness/app` so uv sees `.venv`, or activate the environment (see the table above). |
| `Another process with pid … is using port 8000` | Stop the other server or run `uv run python manage.py runserver 8001`. |
| Arabic labels stay in English after editing strings | Install gettext and run `makemessages -l ar` + `compilemessages` (see above). |
| Empty exercise library | Run `uv run python manage.py seed_data`. |
| Charts do not render | Chart.js is loaded from a CDN; offline the dashboard falls back to the table view. |

---

## Notes

- `DEBUG = True` and the committed secret key are development defaults — use environment values and
  `DEBUG = False` before deploying.
- CSRF protection, `login_required` views and per-user ownership checks are enabled everywhere;
  mutating actions are POST-only.
- Out of scope for now: nutrition tracking, social features, real-time coaching and wearable
  integration.
