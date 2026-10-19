"""Seed the exercise library with muscle groups, equipment and exercises (UC-32).

Names are stored in English (the canonical `Name` column) with an optional Arabic
name in `Name_Ar`, so the library can render either language.
"""
from django.core.management.base import BaseCommand

from exercises.models import Equipment, Exercise, ExerciseEquipment, ExerciseMuscleGroup, MuscleGroup

# name, body region, Arabic name
MUSCLE_GROUPS = [
    ("Chest", "upper", "الصدر"),
    ("Back", "upper", "الظهر"),
    ("Shoulders", "upper", "الكتف"),
    ("Biceps", "upper", "العضلة ذات الرأسين"),
    ("Triceps", "upper", "العضلة ثلاثية الرؤوس"),
    ("Forearms", "upper", "السواعد"),
    ("Quadriceps", "lower", "العضلة الرباعية"),
    ("Hamstrings", "lower", "أوتار الركبة"),
    ("Glutes", "lower", "العضلات المؤخرة"),
    ("Calves", "lower", "البطات"),
    ("Core", "core", "الجذع"),
]

# name, Arabic name
EQUIPMENT = [
    ("Barbell", "البار"),
    ("Dumbbell", "الدمبل"),
    ("Kettlebell", "الكيتل بيل"),
    ("Cable Machine", "جهاز الكابل"),
    ("Machine", "الجهاز"),
    ("Bodyweight", "وزن الجسم"),
    ("Resistance Band", "شريط المقاومة"),
    ("Pull-up Bar", "بار العقلة"),
    ("Bench", "المقعد"),
    ("Squat Rack", "رف السكوات"),
]

# name, Arabic name, type, difficulty, primary muscles, secondary muscles, equipment, instructions
EXERCISES = [
    ("Barbell Bench Press", "ضغط البار على المقعد", "strength", "intermediate", ["Chest"], ["Triceps", "Shoulders"], ["Barbell", "Bench"],
     "Lie on a flat bench with a grip slightly wider than shoulder width. Unrack the bar, lower it to the chest with control, then press it back up until the arms are extended."),
    ("Incline Dumbbell Press", "ضغط الدمبل على المقعد المائل", "strength", "intermediate", ["Chest"], ["Shoulders"], ["Dumbbell", "Bench"],
     "Set a bench to 30-45 degrees. Hold a dumbbell in each hand, press the arms up above the chest and lower them with control."),
    ("Push-up", "تمرين الضغط", "strength", "beginner", ["Chest"], ["Core", "Triceps"], ["Bodyweight"],
     "Start in a plank position with hands under the shoulders. Lower the chest until it is close to the floor, then push back up keeping the body rigid."),
    ("Dumbbell Fly", "فتح الدمبل", "strength", "beginner", ["Chest"], ["Shoulders"], ["Dumbbell", "Bench"],
     "Lie on a bench with a dumbbell in each hand above the chest. Open the arms outward in a wide arc and return to the starting position."),
    ("Pull-up", "تمرين العقلة", "strength", "intermediate", ["Back"], ["Biceps", "Core"], ["Pull-up Bar", "Bodyweight"],
     "Hang from the bar with hands slightly wider than the shoulders. Pull the chest toward the bar by driving the elbows down, then lower with control."),
    ("Barbell Row", "تجديف البار", "strength", "intermediate", ["Back"], ["Core", "Biceps"], ["Barbell"],
     "Hinge forward with a neutral spine, let the bar hang, then pull it toward the lower chest while squeezing the shoulder blades."),
    ("Lat Pulldown", "السحب العلوي", "strength", "beginner", ["Back"], ["Biceps"], ["Cable Machine"],
     "Sit at the pulldown machine, grab the bar, and pull it toward the upper chest while keeping the torso upright."),
    ("Seated Cable Row", "التجديف جالسًا على الكابل", "strength", "beginner", ["Back"], ["Core"], ["Cable Machine"],
     "Sit tall, pull the handle toward the abdomen by retracting the shoulder blades, then return with control."),
    ("Overhead Press", "الضغط فوق الرأس", "strength", "intermediate", ["Shoulders"], ["Triceps", "Core"], ["Barbell"],
     "Stand with the bar at shoulder height. Press it overhead until the arms are extended, then lower it back to the shoulders."),
    ("Lateral Raise", "الرفع الجانبي", "strength", "beginner", ["Shoulders"], [], ["Dumbbell"],
     "Hold a dumbbell in each hand at the sides. Raise the arms out to shoulder height with a slight bend in the elbow and lower slowly."),
    ("Face Pull", "سحب الوجه", "strength", "beginner", ["Shoulders"], ["Back"], ["Cable Machine", "Resistance Band"],
     "Pull the cable handle toward the face, externally rotating the shoulders, then return with control."),
    ("Barbell Curl", "الكيرل بالبار", "strength", "beginner", ["Biceps"], ["Forearms"], ["Barbell"],
     "Stand tall with the bar in front of the thighs. Curl the bar toward the chest without swinging the body, then lower it."),
    ("Hammer Curl", "الكيرل بالمطرقة", "strength", "beginner", ["Biceps"], ["Forearms"], ["Dumbbell"],
     "Hold dumbbells with a neutral grip. Curl both hands toward the shoulders keeping the elbows fixed."),
    ("Triceps Pushdown", "دفع العضلة ثلاثية الرؤوس", "strength", "beginner", ["Triceps"], [], ["Cable Machine"],
     "Stand at the cable machine with elbows at the sides. Extend the arms fully downward, then return to 90 degrees."),
    ("Overhead Triceps Extension", "تمديد العضلة ثلاثية الرؤوس فوق الرأس", "strength", "intermediate", ["Triceps"], ["Core"], ["Dumbbell"],
     "Hold a dumbbell overhead. Lower it behind the head by bending the elbows, then extend the arms again."),
    ("Back Squat", "السكوات الخلفي", "strength", "intermediate", ["Quadriceps"], ["Glutes", "Hamstrings", "Core"], ["Barbell", "Squat Rack"],
     "Place the bar on the upper back and brace the core. Lower the hips until the thighs are parallel, then drive back up through the floor."),
    ("Front Squat", "السكوات الأمامي", "strength", "advanced", ["Quadriceps"], ["Core", "Glutes"], ["Barbell", "Squat Rack"],
     "Rack the bar in front of the shoulders, keep the torso upright, squat to parallel and stand back up."),
    ("Romanian Deadlift", "الرفع الروماني", "strength", "intermediate", ["Hamstrings"], ["Glutes", "Back"], ["Barbell"],
     "Hold the bar at the hips. Hinge at the hips with soft knees until a stretch is felt in the hamstrings, then return to standing."),
    ("Conventional Deadlift", "الرفع التقليدي", "strength", "advanced", ["Hamstrings"], ["Back", "Glutes", "Core"], ["Barbell"],
     "Set the feet over the bar, brace, and lift the bar by extending the hips and knees, keeping the spine neutral."),
    ("Walking Lunge", "اللانج أثناء المشي", "strength", "beginner", ["Quadriceps"], ["Glutes", "Hamstrings"], ["Dumbbell", "Bodyweight"],
     "Step forward and lower the back knee toward the floor, then push off and continue stepping."),
    ("Bulgarian Split Squat", "السكوات البلغاري", "strength", "intermediate", ["Quadriceps"], ["Glutes"], ["Dumbbell", "Bench"],
     "Place the rear foot on a bench, lower the hips until the front thigh is parallel, then drive back up."),
    ("Hip Thrust", "دفع الورك", "strength", "beginner", ["Glutes"], ["Hamstrings"], ["Barbell", "Bench"],
     "Rest the upper back on a bench with the bar over the hips. Drive the hips up by squeezing the glutes, then lower with control."),
    ("Standing Calf Raise", "رفع البطات واقفًا", "strength", "beginner", ["Calves"], [], ["Bodyweight", "Machine"],
     "Rise onto the balls of the feet as high as possible, pause, then lower slowly for a full stretch."),
    ("Plank", "البلانك", "strength", "beginner", ["Core"], ["Shoulders"], ["Bodyweight"],
     "Hold a straight line from head to heels on the forearms, bracing the abdomen the whole time."),
    ("Hanging Knee Raise", "رفع الركبتين متدليًا", "strength", "intermediate", ["Core"], ["Back"], ["Pull-up Bar", "Bodyweight"],
     "Hang from the bar and raise the knees toward the chest without swinging, then lower with control."),
    ("Cable Crunch", "الطحن على الكابل", "strength", "intermediate", ["Core"], [], ["Cable Machine"],
     "Kneel at the cable, hold the rope at the head, and crunch the spine downward, then return with control."),
    ("Treadmill Run", "الجري على الجهاز", "cardio", "beginner", ["Core"], ["Quadriceps", "Calves"], ["Machine"],
     "Set the speed and incline, run with a steady cadence and controlled breathing."),
    ("Rowing Machine", "جهاز التجديف", "cardio", "beginner", ["Back"], ["Core", "Quadriceps"], ["Machine"],
     "Drive with the legs, pull the handle to the chest, then return in the order legs, body, arms."),
    ("Jump Rope", "القفز بالحبل", "cardio", "beginner", ["Calves"], ["Core", "Shoulders"], ["Bodyweight"],
     "Jump with a small bounce, turning the rope with the wrists rather than the arms."),
    ("Burpee", "البربي", "cardio", "advanced", ["Core"], ["Chest", "Quadriceps", "Glutes"], ["Bodyweight"],
     "Drop to the floor, push up, jump the feet in, then jump upward and repeat."),
    ("World's Greatest Stretch", "أفضل إطالة", "flexibility", "beginner", ["Core"], ["Hamstrings", "Back"], ["Bodyweight"],
     "Step into a deep lunge, rotate the torso toward the front leg, then switch sides."),
    ("Couch Stretch", "إطالة أوتار الركبة", "flexibility", "intermediate", ["Quadriceps"], ["Glutes"], ["Bodyweight"],
     "Kneel with the rear foot elevated on a bench, tuck the pelvis and hold an upright posture."),
    ("Single-leg Balance", "التوازن على قدم واحدة", "balance", "beginner", ["Core"], ["Glutes", "Calves"], ["Bodyweight"],
     "Stand on one leg and hold steadily, adding eyes-closed or unstable surfaces as it becomes easier."),
]


class Command(BaseCommand):
    help = "Populate the exercise library with muscle groups, equipment and exercises."

    def handle(self, *args, **options):
        groups = {}
        for name, region, name_ar in MUSCLE_GROUPS:
            group, _ = MuscleGroup.objects.get_or_create(
                name=name, defaults={"body_region": region, "name_ar": name_ar}
            )
            groups[name] = group

        equipment = {}
        for name, name_ar in EQUIPMENT:
            item, _ = Equipment.objects.get_or_create(name=name, defaults={"name_ar": name_ar})
            equipment[name] = item

        created = 0
        for name, name_ar, exercise_type, difficulty, primary, secondary, tools, instructions in EXERCISES:
            exercise, was_created = Exercise.objects.get_or_create(
                name=name,
                defaults={
                    "name_ar": name_ar,
                    "exercise_type": exercise_type,
                    "difficulty": difficulty,
                    "instructions": instructions,
                    "description": f"{name} ({exercise_type}, {difficulty}).",
                },
            )
            if not was_created:
                continue
            created += 1
            for muscle in primary:
                ExerciseMuscleGroup.objects.create(
                    exercise=exercise, muscle_group=groups[muscle], role=ExerciseMuscleGroup.Role.PRIMARY
                )
            for muscle in secondary:
                ExerciseMuscleGroup.objects.create(
                    exercise=exercise, muscle_group=groups[muscle], role=ExerciseMuscleGroup.Role.SECONDARY
                )
            for tool in tools:
                ExerciseEquipment.objects.create(exercise=exercise, equipment=equipment[tool])

        self.stdout.write(
            f"Seeded {len(groups)} muscle groups, {len(equipment)} equipment items and {created} exercises."
        )
