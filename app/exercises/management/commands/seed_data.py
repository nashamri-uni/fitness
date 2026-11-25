"""Seed the exercise library with muscle groups, equipment and exercises (UC-32).

Names are stored in English (the canonical `Name` column) with an optional Arabic
name in `Name_Ar`, so the library can render either language.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from exercises.models import Equipment, Exercise, ExerciseEquipment, ExerciseMuscleGroup, MuscleGroup

# name, body region, Arabic name
MUSCLE_GROUPS = [
    ("Chest", "upper", "الصدر"),
    ("Back", "upper", "الظهر"),
    ("Shoulders", "upper", "الأكتاف"),
    ("Biceps", "upper", "الباي"),
    ("Triceps", "upper", "التراي"),
    ("Forearms", "upper", "السواعد"),
    ("Quadriceps", "lower", "الفخذ الأمامي"),
    ("Hamstrings", "lower", "الفخذ الخلفي"),
    ("Glutes", "lower", "الأرداف"),
    ("Calves", "lower", "البطات"),
    ("Core", "core", "البطن والوسط"),
    ("Adductors", "lower", "مقربات الفخذ"),
]

# Names from the previous seed catalogue, used to update only known seed translations.
LEGACY_MUSCLE_NAMES = {
    "Chest": "الصدر",
    "Back": "الظهر",
    "Shoulders": "الكتف",
    "Biceps": "العضلة ذات الرأسين",
    "Triceps": "العضلة ثلاثية الرؤوس",
    "Forearms": "السواعد",
    "Quadriceps": "العضلة الرباعية",
    "Hamstrings": "أوتار الركبة",
    "Glutes": "العضلات المؤخرة",
    "Calves": "البطات",
    "Core": "الجذع",
}

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
    ("Smith Machine", "جهاز سميث"),
    ("Leg Press Machine", "جهاز ضغط الأرجل"),
    ("Chest Press Machine", "جهاز ضغط الصدر"),
    ("Pec Deck Machine", "جهاز الفراشة"),
    ("EZ Bar", "بار EZ"),
    ("Preacher Curl Bench", "مقعد الباي"),
    ("Stationary Bike", "دراجة ثابتة"),
    ("Elliptical Machine", "جهاز إليبتيكال"),
    ("Stair Climber", "جهاز صعود الدرج"),
    ("Treadmill", "جهاز السير"),
    ("Assisted Pull-up Machine", "جهاز مساعدة العقلة"),
    ("Assisted Dip Machine", "جهاز مساعدة الدبس"),
]

# name, Arabic name, type, difficulty, primary muscles, secondary muscles, equipment, instructions
EXERCISES = [
    ("Barbell Bench Press", "بنش برس بالبار", "strength", "intermediate", ["Chest"], ["Triceps", "Shoulders"], ["Barbell", "Bench"],
     "Lie on a flat bench with a grip slightly wider than shoulder width. Unrack the bar, lower it to the chest with control, then press it back up until the arms are extended."),
    ("Incline Dumbbell Press", "بنش مائل بالدمبل", "strength", "intermediate", ["Chest"], ["Shoulders"], ["Dumbbell", "Bench"],
     "Set a bench to 30-45 degrees. Hold a dumbbell in each hand, press the arms up above the chest and lower them with control."),
    ("Push-up", "بوش أب", "strength", "beginner", ["Chest"], ["Core", "Triceps"], ["Bodyweight"],
     "Start in a plank position with hands under the shoulders. Lower the chest until it is close to the floor, then push back up keeping the body rigid."),
    ("Dumbbell Fly", "تفتيح صدر بالدمبل", "strength", "beginner", ["Chest"], ["Shoulders"], ["Dumbbell", "Bench"],
     "Lie on a bench with a dumbbell in each hand above the chest. Open the arms outward in a wide arc and return to the starting position."),
    ("Pull-up", "عقلة", "strength", "intermediate", ["Back"], ["Biceps", "Core"], ["Pull-up Bar", "Bodyweight"],
     "Hang from the bar with hands slightly wider than the shoulders. Pull the chest toward the bar by driving the elbows down, then lower with control."),
    ("Barbell Row", "تجديف بالبار", "strength", "intermediate", ["Back"], ["Core", "Biceps"], ["Barbell"],
     "Hinge forward with a neutral spine, let the bar hang, then pull it toward the lower chest while squeezing the shoulder blades."),
    ("Lat Pulldown", "سحب ظهر علوي", "strength", "beginner", ["Back"], ["Biceps"], ["Cable Machine"],
     "Sit at the pulldown machine, grab the bar, and pull it toward the upper chest while keeping the torso upright."),
    ("Seated Cable Row", "سحب ظهر كيبل جالس", "strength", "beginner", ["Back"], ["Core"], ["Cable Machine"],
     "Sit tall, pull the handle toward the abdomen by retracting the shoulder blades, then return with control."),
    ("Overhead Press", "ضغط أكتاف بالبار", "strength", "intermediate", ["Shoulders"], ["Triceps", "Core"], ["Barbell"],
     "Stand with the bar at shoulder height. Press it overhead until the arms are extended, then lower it back to the shoulders."),
    ("Lateral Raise", "رفرفة جانبية بالدمبل", "strength", "beginner", ["Shoulders"], [], ["Dumbbell"],
     "Hold a dumbbell in each hand at the sides. Raise the arms out to shoulder height with a slight bend in the elbow and lower slowly."),
    ("Face Pull", "سحب الوجه بالكيبل", "strength", "beginner", ["Shoulders"], ["Back"], ["Cable Machine", "Resistance Band"],
     "Pull the cable handle toward the face, externally rotating the shoulders, then return with control."),
    ("Barbell Curl", "باي بالبار", "strength", "beginner", ["Biceps"], ["Forearms"], ["Barbell"],
     "Stand tall with the bar in front of the thighs. Curl the bar toward the chest without swinging the body, then lower it."),
    ("Hammer Curl", "هامر باي بالدمبل", "strength", "beginner", ["Biceps"], ["Forearms"], ["Dumbbell"],
     "Hold dumbbells with a neutral grip. Curl both hands toward the shoulders keeping the elbows fixed."),
    ("Triceps Pushdown", "تراي كيبل", "strength", "beginner", ["Triceps"], [], ["Cable Machine"],
     "Stand at the cable machine with elbows at the sides. Extend the arms fully downward, then return to 90 degrees."),
    ("Overhead Triceps Extension", "تمديد تراي فوق الرأس", "strength", "intermediate", ["Triceps"], ["Core"], ["Dumbbell"],
     "Hold a dumbbell overhead. Lower it behind the head by bending the elbows, then extend the arms again."),
    ("Back Squat", "سكوات بالبار", "strength", "intermediate", ["Quadriceps"], ["Glutes", "Hamstrings", "Core"], ["Barbell", "Squat Rack"],
     "Place the bar on the upper back and brace the core. Lower the hips until the thighs are parallel, then drive back up through the floor."),
    ("Front Squat", "سكوات أمامي بالبار", "strength", "advanced", ["Quadriceps"], ["Core", "Glutes"], ["Barbell", "Squat Rack"],
     "Rack the bar in front of the shoulders, keep the torso upright, squat to parallel and stand back up."),
    ("Romanian Deadlift", "ديدليفت روماني", "strength", "intermediate", ["Hamstrings"], ["Glutes", "Back"], ["Barbell"],
     "Hold the bar at the hips. Hinge at the hips with soft knees until a stretch is felt in the hamstrings, then return to standing."),
    ("Conventional Deadlift", "ديدليفت تقليدي", "strength", "advanced", ["Hamstrings"], ["Back", "Glutes", "Core"], ["Barbell"],
     "Set the feet over the bar, brace, and lift the bar by extending the hips and knees, keeping the spine neutral."),
    ("Walking Lunge", "لانجز أثناء المشي", "strength", "beginner", ["Quadriceps"], ["Glutes", "Hamstrings"], ["Dumbbell", "Bodyweight"],
     "Step forward and lower the back knee toward the floor, then push off and continue stepping."),
    ("Bulgarian Split Squat", "سكوات بلغاري", "strength", "intermediate", ["Quadriceps"], ["Glutes"], ["Dumbbell", "Bench"],
     "Place the rear foot on a bench, lower the hips until the front thigh is parallel, then drive back up."),
    ("Hip Thrust", "هيب ثرست", "strength", "beginner", ["Glutes"], ["Hamstrings"], ["Barbell", "Bench"],
     "Rest the upper back on a bench with the bar over the hips. Drive the hips up by squeezing the glutes, then lower with control."),
    ("Standing Calf Raise", "رفع البطات واقفًا", "strength", "beginner", ["Calves"], [], ["Bodyweight", "Machine"],
     "Rise onto the balls of the feet as high as possible, pause, then lower slowly for a full stretch."),
    ("Plank", "بلانك", "strength", "beginner", ["Core"], ["Shoulders"], ["Bodyweight"],
     "Hold a straight line from head to heels on the forearms, bracing the abdomen the whole time."),
    ("Hanging Knee Raise", "رفع الركبتين بالتعلق", "strength", "intermediate", ["Core"], ["Back"], ["Pull-up Bar", "Bodyweight"],
     "Hang from the bar and raise the knees toward the chest without swinging, then lower with control."),
    ("Cable Crunch", "كرنش البطن بالكيبل", "strength", "intermediate", ["Core"], [], ["Cable Machine"],
     "Kneel at the cable, hold the rope at the head, and crunch the spine downward, then return with control."),
    ("Treadmill Run", "الجري على السير", "cardio", "beginner", ["Quadriceps"], ["Calves", "Core"], ["Treadmill"],
     "Set the speed and incline, run with a steady cadence and controlled breathing."),
    ("Rowing Machine", "جهاز التجديف", "cardio", "beginner", ["Back"], ["Core", "Quadriceps"], ["Machine"],
     "Drive with the legs, pull the handle to the chest, then return in the order legs, body, arms."),
    ("Jump Rope", "نط الحبل", "cardio", "beginner", ["Calves"], ["Core", "Shoulders"], ["Bodyweight"],
     "Jump with a small bounce, turning the rope with the wrists rather than the arms."),
    ("Burpee", "بيربي", "cardio", "advanced", ["Core"], ["Chest", "Quadriceps", "Glutes"], ["Bodyweight"],
     "Drop to the floor, push up, jump the feet in, then jump upward and repeat."),
    ("World's Greatest Stretch", "أفضل إطالة في العالم", "flexibility", "beginner", ["Core"], ["Hamstrings", "Back"], ["Bodyweight"],
     "Step into a deep lunge, rotate the torso toward the front leg, then switch sides."),
    ("Couch Stretch", "إطالة الورك مع إسناد القدم", "flexibility", "intermediate", ["Quadriceps"], ["Glutes"], ["Bodyweight"],
     "Kneel with the rear foot elevated on a bench, tuck the pelvis and hold an upright posture."),
    ("Single-leg Balance", "توازن على ساق واحدة", "balance", "beginner", ["Core"], ["Glutes", "Calves"], ["Bodyweight"],
     "Stand on one leg and hold steadily, adding eyes-closed or unstable surfaces as it becomes easier."),
    ("Flat Dumbbell Bench Press", "بنش مستوٍ بالدمبل", "strength", "intermediate", ["Chest"], ["Triceps", "Shoulders"], ["Dumbbell", "Bench"],
     "Lie on a flat bench with the dumbbells beside your chest. Press them up without letting them touch, then lower under control."),
    ("Incline Barbell Bench Press", "بنش مائل بالبار", "strength", "intermediate", ["Chest"], ["Shoulders", "Triceps"], ["Barbell", "Bench"],
     "Set the bench to a moderate incline. Lower the bar toward the upper chest, then press it back to the start."),
    ("Decline Bench Press", "بنش مائل للأسفل بالبار", "strength", "intermediate", ["Chest"], ["Triceps", "Shoulders"], ["Barbell", "Bench"],
     "Secure your legs on a decline bench. Lower the bar to the lower chest and press it up with control."),
    ("Machine Chest Press", "ضغط صدر على الجهاز", "strength", "beginner", ["Chest"], ["Triceps", "Shoulders"], ["Chest Press Machine"],
     "Adjust the seat so the handles align with your chest. Press the handles forward, then return slowly."),
    ("Cable Chest Fly", "تفتيح صدر بالكيبل", "strength", "beginner", ["Chest"], ["Shoulders"], ["Cable Machine"],
     "Stand between the pulleys with a slight bend in your elbows. Bring your hands together in front of your chest, then open them slowly."),
    ("Pec Deck Fly", "تفتيح صدر بجهاز الفراشة", "strength", "beginner", ["Chest"], ["Shoulders"], ["Pec Deck Machine"],
     "Sit with your back against the pad and elbows on the supports. Bring the arms together, then return until you feel a gentle chest stretch."),
    ("One-arm Dumbbell Row", "تجديف دمبل بذراع واحدة", "strength", "beginner", ["Back"], ["Biceps", "Core"], ["Dumbbell", "Bench"],
     "Support one hand and knee on a bench. Row the dumbbell toward your hip without twisting, then lower it steadily."),
    ("Chest-supported Row", "تجديف مع إسناد الصدر", "strength", "beginner", ["Back"], ["Biceps", "Shoulders"], ["Machine", "Bench"],
     "Set your chest against the pad and grasp the handles. Pull your elbows back, pause briefly, then extend your arms."),
    ("Machine Seated Row", "تجديف جالس على الجهاز", "strength", "beginner", ["Back"], ["Biceps"], ["Machine"],
     "Sit upright and hold the handles with arms extended. Pull toward your torso while keeping your shoulders down, then return slowly."),
    ("Close-grip Lat Pulldown", "سحب علوي بقبضة ضيقة", "strength", "beginner", ["Back"], ["Biceps"], ["Cable Machine"],
     "Sit at the pulldown station and hold the close-grip attachment. Pull it toward your upper chest, then allow your arms to extend."),
    ("Straight-arm Cable Pulldown", "سحب كيبل بذراعين مستقيمتين", "strength", "intermediate", ["Back"], ["Shoulders", "Core"], ["Cable Machine"],
     "Face the high pulley with arms nearly straight. Pull the bar down to your thighs without leaning back, then return with control."),
    ("T-bar Row", "تجديف تي بار", "strength", "intermediate", ["Back"], ["Biceps", "Core"], ["Barbell"],
     "Hinge forward with a steady torso and grasp the T-bar handle. Row the bar toward your abdomen, then lower it smoothly."),
    ("Assisted Pull-up", "عقلة بمساعدة الجهاز", "strength", "beginner", ["Back"], ["Biceps"], ["Assisted Pull-up Machine"],
     "Set the assistance and kneel or stand on the platform. Pull your chest toward the bar, then lower until your arms extend."),
    ("Dumbbell Shoulder Press", "ضغط أكتاف بالدمبل", "strength", "beginner", ["Shoulders"], ["Triceps"], ["Dumbbell"],
     "Sit or stand with dumbbells at shoulder height. Press them overhead without arching your back, then lower steadily."),
    ("Machine Shoulder Press", "ضغط أكتاف على الجهاز", "strength", "beginner", ["Shoulders"], ["Triceps"], ["Machine"],
     "Adjust the seat so the handles begin near shoulder height. Press overhead and lower the handles slowly."),
    ("Cable Lateral Raise", "رفرفة جانبية بالكيبل", "strength", "beginner", ["Shoulders"], [], ["Cable Machine"],
     "Stand beside a low cable with the handle in your far hand. Raise your arm out to shoulder height, then lower it under control."),
    ("Rear Delt Fly", "تفتيح خلفي للأكتاف", "strength", "beginner", ["Shoulders"], ["Back"], ["Dumbbell", "Bench"],
     "Hinge at the hips and let the dumbbells hang below your shoulders. Raise your arms out to the sides, then lower slowly."),
    ("Reverse Pec Deck", "تفتيح خلفي على جهاز الفراشة", "strength", "beginner", ["Shoulders"], ["Back"], ["Pec Deck Machine"],
     "Face the machine pad and grasp the handles. Sweep your arms outward, keeping a soft elbow bend, then return slowly."),
    ("Dumbbell Front Raise", "رفرفة أمامية بالدمبل", "strength", "beginner", ["Shoulders"], ["Chest"], ["Dumbbell"],
     "Hold dumbbells in front of your thighs. Raise them to shoulder height without swinging, then lower with control."),
    ("Dumbbell Biceps Curl", "باي بالدمبل", "strength", "beginner", ["Biceps"], ["Forearms"], ["Dumbbell"],
     "Stand tall with dumbbells at your sides. Curl them toward your shoulders while keeping your elbows close to your body."),
    ("Incline Dumbbell Curl", "باي بالدمبل على مقعد مائل", "strength", "intermediate", ["Biceps"], ["Forearms"], ["Dumbbell", "Bench"],
     "Sit back on an inclined bench with arms hanging down. Curl the dumbbells without moving your upper arms, then lower fully."),
    ("Preacher Curl", "باي على مقعد بريتشر", "strength", "beginner", ["Biceps"], ["Forearms"], ["Preacher Curl Bench", "EZ Bar"],
     "Rest your upper arms on the preacher pad. Curl the bar toward your shoulders, then lower it until your arms are nearly straight."),
    ("Cable Biceps Curl", "باي بالكيبل", "strength", "beginner", ["Biceps"], ["Forearms"], ["Cable Machine"],
     "Stand at a low pulley with elbows near your sides. Curl the handle upward, then return slowly without rocking."),
    ("Concentration Curl", "باي تركيز بالدمبل", "strength", "beginner", ["Biceps"], ["Forearms"], ["Dumbbell", "Bench"],
     "Sit and brace your upper arm against your inner thigh. Curl the dumbbell toward your shoulder, then lower with control."),
    ("EZ-bar Curl", "باي ببار EZ", "strength", "beginner", ["Biceps"], ["Forearms"], ["EZ Bar"],
     "Hold the EZ bar with a comfortable angled grip. Curl it toward your chest while keeping your elbows still, then lower steadily."),
    ("Rope Triceps Pushdown", "تراي بالحبل", "strength", "beginner", ["Triceps"], [], ["Cable Machine"],
     "Keep your elbows by your sides and hold the rope ends. Extend your arms downward, then return until your elbows are bent."),
    ("Straight-bar Triceps Pushdown", "تراي بالبار المستقيم", "strength", "beginner", ["Triceps"], [], ["Cable Machine"],
     "Stand at a high pulley with elbows tucked in. Push the straight bar down until your arms extend, then return slowly."),
    ("Overhead Cable Triceps Extension", "تمديد تراي بالكيبل فوق الرأس", "strength", "intermediate", ["Triceps"], ["Shoulders"], ["Cable Machine"],
     "Face away from a low pulley and hold the rope behind your head. Extend your elbows overhead, then bend them slowly."),
    ("Skull Crusher", "تمديد تراي مستلقياً ببار EZ", "strength", "intermediate", ["Triceps"], ["Shoulders"], ["EZ Bar", "Bench"],
     "Lie on a bench and hold the EZ bar above your chest. Bend your elbows to lower it near your forehead, then extend your arms."),
    ("Dumbbell Triceps Extension", "تمديد تراي بالدمبل", "strength", "beginner", ["Triceps"], ["Shoulders"], ["Dumbbell"],
     "Hold one dumbbell overhead with both hands. Bend your elbows to lower it behind your head, then extend your arms."),
    ("Assisted Dip", "ديبس بمساعدة الجهاز", "strength", "beginner", ["Triceps"], ["Chest", "Shoulders"], ["Assisted Dip Machine"],
     "Set the assistance and grip the parallel bars. Lower by bending your elbows, then press back up without locking them forcefully."),
    ("Leg Press", "ضغط الأرجل على الجهاز", "strength", "beginner", ["Quadriceps"], ["Glutes", "Hamstrings"], ["Leg Press Machine"],
     "Sit with feet shoulder-width on the platform. Lower until your knees are comfortably bent, then press through your feet."),
    ("Hack Squat", "هاك سكوات", "strength", "intermediate", ["Quadriceps"], ["Glutes"], ["Machine"],
     "Position your shoulders under the pads and feet on the platform. Lower into a controlled squat, then drive back up."),
    ("Goblet Squat", "سكوات الكأس بالدمبل", "strength", "beginner", ["Quadriceps"], ["Glutes", "Core"], ["Dumbbell"],
     "Hold one dumbbell upright against your chest. Squat between your hips while keeping your torso tall, then stand."),
    ("Leg Extension", "تمديد الأرجل على الجهاز", "strength", "beginner", ["Quadriceps"], [], ["Machine"],
     "Adjust the pad above your ankles. Straighten your knees to lift the pad, pause, then lower it slowly."),
    ("Seated Leg Curl", "ثني الأرجل جالساً على الجهاز", "strength", "beginner", ["Hamstrings"], [], ["Machine"],
     "Set the pads against your lower legs and thighs. Bend your knees to pull the lower pad down, then return slowly."),
    ("Lying Leg Curl", "ثني الأرجل مستلقياً على الجهاز", "strength", "beginner", ["Hamstrings"], [], ["Machine"],
     "Lie face down with the pad above your heels. Curl your heels toward your hips, then lower the weight with control."),
    ("Smith Machine Squat", "سكوات بجهاز سميث", "strength", "intermediate", ["Quadriceps"], ["Glutes", "Hamstrings", "Core"], ["Smith Machine"],
     "Set the bar across your upper back and stand with feet stable. Squat to a comfortable depth, then stand while keeping your knees aligned."),
    ("Dumbbell Romanian Deadlift", "ديدليفت روماني بالدمبل", "strength", "intermediate", ["Hamstrings"], ["Glutes", "Back"], ["Dumbbell"],
     "Hold dumbbells in front of your thighs. Push your hips back with soft knees, lower along your legs, then stand by driving your hips forward."),
    ("Hip Abduction Machine", "فتح الورك على الجهاز", "strength", "beginner", ["Glutes"], [], ["Machine"],
     "Sit with your knees against the pads. Press your thighs outward, pause briefly, then return slowly."),
    ("Hip Adduction Machine", "ضم الورك على الجهاز", "strength", "beginner", ["Adductors"], ["Glutes"], ["Machine"],
     "Sit with your thighs against the pads. Bring your legs together against the resistance, then open them in a controlled return."),
    ("Seated Calf Raise", "رفع البطات جالساً", "strength", "beginner", ["Calves"], [], ["Machine"],
     "Sit with the pad resting above your knees and the balls of your feet on the platform. Raise your heels, then lower them for a stretch."),
    ("Machine Standing Calf Raise", "رفع البطات واقفاً على الجهاز", "strength", "beginner", ["Calves"], [], ["Machine"],
     "Stand with the balls of your feet on the platform and shoulders under the pads. Raise your heels, pause, then lower slowly."),
    ("Leg Press Calf Raise", "رفع البطات على جهاز ضغط الأرجل", "strength", "beginner", ["Calves"], [], ["Leg Press Machine"],
     "Place the balls of your feet near the bottom edge of the platform. Extend your ankles to press it away, then lower your heels."),
    ("Abdominal Crunch", "كرنش البطن", "strength", "beginner", ["Core"], [], ["Bodyweight"],
     "Lie on your back with knees bent and hands lightly by your head. Curl your shoulders toward your hips, then lower without pulling your neck."),
    ("Reverse Crunch", "كرنش عكسي للبطن", "strength", "beginner", ["Core"], [], ["Bodyweight"],
     "Lie on your back with knees bent above your hips. Curl your pelvis to lift your hips slightly, then lower with control."),
    ("Hanging Leg Raise", "رفع الساقين بالتعلق", "strength", "intermediate", ["Core"], ["Back"], ["Pull-up Bar"],
     "Hang from a bar with your body steady. Raise your straight legs as far as you can without swinging, then lower slowly."),
    ("Lying Leg Raise", "رفع الساقين من الاستلقاء", "strength", "beginner", ["Core"], [], ["Bodyweight"],
     "Lie on your back with legs extended. Lift your legs while keeping your lower back controlled, then lower without relaxing your brace."),
    ("Side Plank", "بلانك جانبي", "strength", "beginner", ["Core"], ["Shoulders"], ["Bodyweight"],
     "Lie on one side and support yourself on your forearm. Lift your hips into a straight line and hold, then switch sides."),
    ("Russian Twist", "لف روسي للبطن", "strength", "beginner", ["Core"], [], ["Bodyweight"],
     "Sit with knees bent and torso slightly reclined. Rotate your shoulders from side to side while keeping your trunk controlled."),
    ("Treadmill Walking", "مشي على السير", "cardio", "beginner", ["Quadriceps"], ["Calves", "Glutes"], ["Treadmill"],
     "Choose a comfortable pace and walk with an upright posture. Keep your steps steady and hold the rails only when needed for safety."),
    ("Stationary Bike", "دراجة ثابتة", "cardio", "beginner", ["Quadriceps"], ["Glutes", "Calves"], ["Stationary Bike"],
     "Adjust the seat so your knee remains slightly bent at the bottom of each pedal stroke. Pedal at a steady, comfortable effort."),
    ("Elliptical Machine", "جهاز إليبتيكال", "cardio", "beginner", ["Quadriceps"], ["Glutes", "Calves"], ["Elliptical Machine"],
     "Step onto the pedals and hold the handles. Move in a smooth stride at a steady pace, keeping your posture upright."),
    ("Stair Climber", "صعود الدرج على الجهاز", "cardio", "beginner", ["Quadriceps"], ["Glutes", "Calves"], ["Stair Climber"],
     "Step onto the pedals and climb at a controlled pace. Keep your torso upright and use the handrails for balance when needed."),
    ("Outdoor Running", "جري خارجي", "cardio", "intermediate", ["Quadriceps"], ["Calves", "Glutes"], [],
     "Run on a clear, suitable route at a pace you can sustain. Keep your stride relaxed and increase speed gradually."),
    ("Brisk Walking", "مشي سريع", "cardio", "beginner", ["Quadriceps"], ["Calves", "Glutes"], [],
     "Walk at a purposeful pace that raises your breathing while allowing conversation. Maintain a relaxed, upright posture."),
    ("Dumbbell Pullover", "بول أوفر بالدمبل", "strength", "intermediate", ["Chest"], ["Back"], ["Dumbbell", "Bench"],
     "Lie across or along a bench and hold one dumbbell above your chest. Lower it in an arc behind your head, then bring it back over your chest."),
    ("Single-arm Cable Row", "تجديف بالكيبل بذراع واحدة", "strength", "beginner", ["Back"], ["Biceps", "Core"], ["Cable Machine"],
     "Sit or stand facing a low pulley with one arm extended. Pull the handle toward your waist without rotating your torso, then return slowly."),
    ("Arnold Press", "ضغط أرنولد بالدمبل", "strength", "intermediate", ["Shoulders"], ["Triceps"], ["Dumbbell"],
     "Start with dumbbells in front of your shoulders and palms facing you. Press overhead while rotating your palms forward, then reverse the motion."),
    ("Reverse Curl", "باي عكسي بالبار", "strength", "beginner", ["Biceps"], ["Forearms"], ["Barbell"],
     "Hold a bar with palms facing down and elbows close to your sides. Curl it toward your shoulders, then lower without swinging."),
    ("Zottman Curl", "زوتمان كيرل بالدمبل", "strength", "intermediate", ["Biceps"], ["Forearms"], ["Dumbbell"],
     "Curl dumbbells with palms up. Rotate your wrists at the top so palms face down, then lower slowly and turn back at the bottom."),
    ("Close-grip Bench Press", "بنش برس بقبضة ضيقة", "strength", "intermediate", ["Triceps"], ["Chest", "Shoulders"], ["Barbell", "Bench"],
     "Lie on a bench and grip the bar slightly narrower than shoulder width. Lower it to your chest with elbows near your sides, then press up."),
    ("Bench Dip", "ديبس على المقعد", "strength", "beginner", ["Triceps"], ["Chest", "Shoulders"], ["Bench", "Bodyweight"],
     "Place your hands on the edge of a stable bench and extend your legs. Bend your elbows to lower your hips, then press back up."),
    ("Step-up", "صعود على صندوق بالتبادل", "strength", "beginner", ["Quadriceps"], ["Glutes", "Hamstrings"], ["Bench", "Dumbbell"],
     "Place one foot fully on a stable step. Drive through that leg to stand on the step, then step down carefully and alternate sides."),
    ("Sumo Deadlift", "ديدليفت سومو", "strength", "intermediate", ["Glutes"], ["Quadriceps", "Hamstrings", "Back"], ["Barbell"],
     "Stand with a wide stance and toes turned slightly outward. Brace, grip the bar between your legs, and stand by extending your hips and knees."),
    ("Dead Bug", "ديد بغ للبطن", "strength", "beginner", ["Core"], [], ["Bodyweight"],
     "Lie on your back with arms raised and knees bent. Extend the opposite arm and leg while keeping your lower back steady, then alternate."),
    ("Mountain Climber", "متسلق الجبل", "cardio", "beginner", ["Core"], ["Shoulders", "Quadriceps"], ["Bodyweight"],
     "Start in a high plank with hands under your shoulders. Drive one knee toward your chest, switch legs rhythmically, and keep your hips steady."),
]


class Command(BaseCommand):
    help = "Populate the exercise library with muscle groups, equipment and exercises."

    @transaction.atomic
    def handle(self, *args, **options):
        groups = {}
        for name, region, name_ar in MUSCLE_GROUPS:
            group, _ = MuscleGroup.objects.get_or_create(
                name=name, defaults={"body_region": region, "name_ar": name_ar}
            )
            previous_name = LEGACY_MUSCLE_NAMES.get(name)
            if group.name_ar in {"", name_ar, previous_name}:
                group.name_ar = name_ar
                group.save(update_fields=["name_ar"])
            groups[name] = group

        equipment = {}
        for name, name_ar in EQUIPMENT:
            item, _ = Equipment.objects.get_or_create(name=name, defaults={"name_ar": name_ar})
            equipment[name] = item

        created = 0
        updated = 0
        skipped = 0
        for name, name_ar, exercise_type, difficulty, primary, secondary, tools, instructions in EXERCISES:
            description = f"{name} ({exercise_type}, {difficulty})."
            exercise, was_created = Exercise.objects.get_or_create(
                name=name,
                defaults={
                    "name_ar": name_ar,
                    "exercise_type": exercise_type,
                    "difficulty": difficulty,
                    "instructions": instructions,
                    "description": description,
                },
            )
            if not was_created and not self._is_seed_managed(exercise, description):
                skipped += 1
                continue
            if was_created:
                created += 1
            else:
                updated += 1
                exercise.name_ar = name_ar
                exercise.exercise_type = exercise_type
                exercise.difficulty = difficulty
                exercise.instructions = instructions
                exercise.save(update_fields=["name_ar", "exercise_type", "difficulty", "instructions"])

            desired_muscles = {
                (groups[muscle].pk, ExerciseMuscleGroup.Role.PRIMARY)
                for muscle in primary
            }
            desired_muscles.update(
                (groups[muscle].pk, ExerciseMuscleGroup.Role.SECONDARY)
                for muscle in secondary
            )
            for muscle_group_id, role in desired_muscles:
                ExerciseMuscleGroup.objects.update_or_create(
                    exercise=exercise,
                    muscle_group_id=muscle_group_id,
                    defaults={"role": role},
                )
            exercise.muscle_links.exclude(
                muscle_group_id__in=[muscle_group_id for muscle_group_id, _ in desired_muscles]
            ).delete()

            desired_equipment_ids = [equipment[tool].pk for tool in tools]
            for equipment_id in desired_equipment_ids:
                ExerciseEquipment.objects.get_or_create(exercise=exercise, equipment_id=equipment_id)
            exercise.equipment_links.exclude(equipment_id__in=desired_equipment_ids).delete()

        self.stdout.write(
            f"Seeded {len(groups)} muscle groups, {len(equipment)} equipment items, "
            f"created {created} exercises, updated {updated}, skipped {skipped} user-managed records."
        )

    @staticmethod
    def _is_seed_managed(exercise, expected_description):
        return exercise.created_by_id is None and exercise.description == expected_description
