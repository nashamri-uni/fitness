from django.db import migrations, models


def install_email_guards(apps, schema_editor):
    if schema_editor.connection.vendor != "sqlite":
        raise RuntimeError("The FitPlanner email guards require SQLite.")
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT id FROM accounts_user WHERE email GLOB '*[^ -~]*' ORDER BY id")
        ids = [str(pk) for (pk,) in cursor.fetchall()]
    if ids:
        raise RuntimeError(
            "Verify and normalize non-ASCII legacy email addresses before migrating. "
            f"Account IDs: {', '.join(ids)}."
        )

    schema_editor.execute("CREATE INDEX accounts_email_lookup ON accounts_user (LOWER(TRIM(email)))")
    for event, suffix, condition in (
        ("INSERT", "insert", ""),
        ("UPDATE OF email", "update", " AND NEW.email IS NOT OLD.email"),
    ):
        schema_editor.execute(
            f"""
            CREATE TRIGGER accounts_email_{suffix}
            BEFORE {event} ON accounts_user
            WHEN NEW.email <> ''{condition}
            BEGIN
              SELECT CASE
                WHEN NEW.email <> TRIM(NEW.email) OR NEW.email GLOB '*[^ -~]*'
                  THEN RAISE(ABORT, 'accounts_email_normalization')
                WHEN EXISTS (
                  SELECT 1 FROM accounts_user
                  WHERE LOWER(TRIM(email)) = LOWER(TRIM(NEW.email))
                    AND id IS NOT NEW.id
                ) THEN RAISE(ABORT, 'accounts_email_conflict')
              END;
            END
            """
        )


def remove_email_guards(apps, schema_editor):
    schema_editor.execute("DROP TRIGGER accounts_email_update")
    schema_editor.execute("DROP TRIGGER accounts_email_insert")
    schema_editor.execute("DROP INDEX accounts_email_lookup")


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_weeklyworkoutgoalhistory_and_more")]
    operations = [
        migrations.AddField(
            model_name="user",
            name="requires_google_profile",
            field=models.BooleanField(db_column="Requires_Google_Profile", default=False, db_default=False),
        ),
        migrations.RunPython(install_email_guards, remove_email_guards),
    ]
