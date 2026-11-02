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
| Accounts | Register / login / logout, fitness profile (date of birth, height, weight, fitness goal) |
| Exercise library | Browse, search and filter exercises by muscle group, equipment, type and difficulty |
| Workout plans | Create plans of exercises with target sets, reps, weight, duration and rest time |
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
uv run python manage.py seed_data     # 11 muscle groups, 10 equipment items, 33 exercises

# 5. Optional: demo user with several weeks of logged sessions
uv run python manage.py seed_demo     # login: demo / demo12345678
#    other options: uv run python manage.py seed_demo --user nasser --password 123123

# 6. Create your own admin account
uv run python manage.py createsuperuser

# 7. Run it
uv run python manage.py runserver
```

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
│   ├── plans/          WorkoutPlan, PlanExercise, PlanSet
│   ├── workouts/       WorkoutSession, SessionExercise, SessionSet, PersonalRecord, seed_demo
│   ├── analytics/      summary, weekly volume, improvement metrics, dashboard / progress views
│   ├── templates/      base.html + per-app templates + form field partial
│   ├── static/         css/style.css, css/rtl.css, js/app.js (Chart.js from CDN)
│   ├── locale/ar/      Arabic translation catalog (.po / .mo)
│   └── requirements.txt
└── app/README.md       detailed developer notes (models, routes, business rules, i18n)
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
| Plans | `/plans/`, `/plans/new/`, `/plans/<id>/`, edit / delete, set editing |
| Sessions | `/sessions/`, `/sessions/start/<plan>/`, `/sessions/<id>/`, log set, complete |
| Personal records | `/sessions/records/` |
| Analytics | `/analytics/`, `/analytics/progress/` |
| Language | `/i18n/setlang/` |

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
