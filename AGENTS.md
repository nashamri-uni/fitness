# AGENTS.md — Workout and Fitness Planner

## What this project is

A graduation project: a **web-based Workout and Fitness Planner** where users register, browse an
exercise library, build reusable workout plans (exercises + sets/reps/weight/duration/rest), log
completed training sessions, and see progress through personal-record detection, improvement
metrics and analytics dashboards. It is bilingual (English / Arabic with RTL) and responsive.

- **Backend:** Django (MVT), SQLite, Django auth with a custom user model.
- **Frontend:** plain HTML/CSS + a small vanilla JS layer (`static/js/app.js`) using Chart.js from a CDN.
- **Design document / source of truth:** the `report/` folder (Typst sources + `report/main.pdf`).
  When a requirement is ambiguous, read the report before changing behaviour.

## Layout

```
report/        Typst report: Chapter1 (overview), Chapter2 (analysis, FREQ/NREQ tables,
               use cases UC-1..UC-33, sequence diagrams), Chapter3 (schema + UI + tech)
app/           the Django implementation
├── manage.py
├── config/    settings, root urls (incl. /i18n/setlang/), wsgi/asgi
├── accounts/  User + UserProfile, register/login/logout/profile
├── exercises/ MuscleGroup, Equipment, Exercise + link tables, library + admin CRUD
├── plans/     WorkoutPlan, PlanExercise, PlanSet
├── workouts/  WorkoutSession, SessionExercise, SessionSet, PersonalRecord, services.py
├── analytics/ services.py (summary, weekly volume, improvement metrics), dashboard/progress views
├── templates/ base.html + per-app templates + templates/partials/form_fields.html
├── static/    css/style.css, css/rtl.css, js/app.js
└── locale/ar/ django.po / django.mo translations
shell.nix      dev shell (python3 + django + gettext + git)
```

## Domain model (as defined in Chapter 3 of the report)

`User → UserProfile` (fitness preferences), `Exercise` ↔ `MuscleGroup` / `Equipment` through
`Exercise_Muscle_Group` (with primary/secondary `Role`) and `Exercise_Equipment`.
`WorkoutPlan → PlanExercise → PlanSet` (the planned routine),
`WorkoutSession → SessionExercise → SessionSet` (what was actually performed).
`PersonalRecord` keeps the best value per user/exercise/type
(`max_weight`, `max_reps`, `max_volume`, `max_duration`).

Business rules that must keep working:

- **Session lifecycle:** starting a session copies the plan's exercises into `SessionExercise`
  (`workouts/services.py:start_session`); finishing computes `Duration_Minutes` from
  `Started_At`/`Ended_At` (`finish_session`).
- **Personal records (FREQ-11):** every logged set is evaluated by
  `workouts/services.py:evaluate_personal_record` against the stored best per metric; an improved
  metric updates `PersonalRecord` and flags `SessionSet.Is_Personal_Record`.
- **Improvement metrics (FREQ-10):** first logged value vs. current best per exercise, weekly
  volume buckets, weekly training streak (`analytics/services.py`).
- **Soft delete:** `Exercise.Is_Active` — the library lists active exercises only.

## Conventions to preserve

- **Column names mirror the report schema** via `db_column` (`User_ID`, `Session_Exercise_ID`,
  `Is_Personal_Record`, ...) and `db_table` (`User_Profile`, `Exercise_Muscle_Group`, ...). Keep them
  when adding fields; changes need a migration.
- Enums are `models.TextChoices` with `gettext_lazy` labels; verbose names are `gettext_lazy`.
- **Ownership:** every user-scoped object is fetched with `user=request.user`; administrators are
  checked by the `admin_required` decorator in `exercises/views.py` (`is_project_admin` or `is_staff`).
  Views are `login_required`, mutating actions are POST-only, forms include `{% csrf_token %}`.
- **Forms and validation** live in each app's `forms.py` (RPE 1–10, rating 1–5, non-negative values);
  views stay thin and `services.py` holds the calculation logic.
- **i18n:** every user-facing string uses `{% trans %}`/`{% blocktrans %}` or `gettext(_lazy)`.
  Data names are *not* UI text: `MuscleGroup`/`Equipment`/`Exercise` carry `Name_Ar` +
  `display_name()` (see `exercises/models.py:NameMixin`). Chart labels are passed to JS through
  `data-*` attributes rendered with `{% trans %}`. After editing any string:
  `python manage.py makemessages -l ar && python manage.py compilemessages` (needs gettext).
- **Tests:** each app has `tests.py`; keep them green, and add coverage for new endpoints/logic
  (ownership, filtering, PR detection, language switching).

## Running

```bash
nix-shell                                   # or any env with Django + gettext
cd app && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python manage.py migrate
python manage.py seed_data                  # exercise library (muscle groups, equipment, exercises)
python manage.py seed_demo                  # optional demo user, demo/demo12345678
python manage.py createsuperuser
python manage.py runserver                  # http://127.0.0.1:8000/
python manage.py test
```

## Requirement → route map

| Area | URL | Requirement |
|---|---|---|
| Auth | `/accounts/register/`, `/login/`, `/logout/`, `/profile/` | FREQ-1, 2, 13 |
| Exercise library | `/exercises/` (search + filters), `/exercises/<id>/` | FREQ-3, 14 |
| Admin CRUD | `/exercises/manage/` + Django admin | FREQ-15, 16 |
| Plans | `/plans/`, `/plans/new/`, `/plans/<id>/`, edit/delete, sets | FREQ-4–7 |
| Sessions | `/sessions/`, `/sessions/<id>/`, `/sessions/start/<plan>/`, log set, complete | FREQ-8 |
| Records | `/sessions/records/` | FREQ-11 |
| Analytics | `/analytics/`, `/analytics/progress/` | FREQ-9, 10, 12 |
| Language | `/i18n/setlang/` (English / Arabic, RTL) | i18n, NREQ-4/10 |

## Development workflow

Git + GitHub, branch per feature/fix, pull request review before merging to `main`, GitHub Issues for
the backlog (Chapter 3). `DEBUG = True` and the committed secret key are development defaults — use
environment values for anything deployable. Out of scope for now: nutrition tracking, social features,
real-time coaching, wearable integration; reserved for later work by NREQ-11.
