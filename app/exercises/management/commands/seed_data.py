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
    ("Ab Wheel", "عجلة البطن"),
    ("Battle Rope", "حبل المعركة"),
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
    ("Seated Back Extension", "تمديد الظهر جالسًا", "strength", "beginner", ["Back"], ["Glutes", "Hamstrings"], ["Machine"],
     "Set the machine so the pad rests against your upper back. Brace your core, extend your torso to neutral, then return slowly."),
    ("Inverted Row", "تجديف مقلوب", "strength", "beginner", ["Back"], ["Biceps", "Core"], ["Pull-up Bar", "Bodyweight"],
     "Lie beneath a secure horizontal bar and hold it with arms extended. Pull your chest toward the bar while keeping your body straight, then lower with control."),
    ("One Arm Landmine Row", "تجديف لاندماين بذراع واحدة", "strength", "intermediate", ["Back"], ["Biceps", "Core"], ["Barbell"],
     "Hinge with a neutral spine and hold the end of a secured barbell. Row it toward your hip without rotating your torso, then lower steadily."),
    ("Barbell Floor Press", "ضغط البار من الأرض", "strength", "intermediate", ["Chest"], ["Triceps", "Shoulders"], ["Barbell"],
     "Lie on the floor with the bar above your chest. Lower until your upper arms touch the floor, pause briefly, then press back up."),
    ("Incline Landmine Press", "ضغط لاندماين مائل", "strength", "intermediate", ["Shoulders"], ["Chest", "Triceps", "Core"], ["Barbell"],
     "Hold the end of a secured barbell at shoulder height. Press it upward and forward, then lower it with control."),
    ("Cable Upright Row", "تجديف عمودي بالكيبل", "strength", "beginner", ["Shoulders"], ["Biceps"], ["Cable Machine"],
     "Hold a low cable attachment in front of your thighs. Pull it upward close to your body without raising your elbows above shoulder level, then lower slowly."),
    ("Wall Sit", "جلوس الحائط", "strength", "beginner", ["Quadriceps"], ["Glutes"], ["Bodyweight"],
     "Lean your back against a wall and slide down until your knees are comfortably bent. Hold the position while keeping your feet flat."),
    ("Glute Bridge", "جسر الأرداف", "strength", "beginner", ["Glutes"], ["Hamstrings", "Core"], ["Bodyweight"],
     "Lie on your back with knees bent and feet flat. Brace your abdomen, squeeze your glutes to lift your hips, then lower under control."),
    ("Cable Pull Through", "سحب الكيبل بين الساقين", "strength", "beginner", ["Glutes"], ["Hamstrings", "Back"], ["Cable Machine"],
     "Stand facing away from a low pulley with the cable between your legs. Hinge at the hips, then drive them forward to stand tall without arching your back."),
    ("Glute Kickback Machine", "ركل الأرداف على الجهاز", "strength", "beginner", ["Glutes"], ["Hamstrings"], ["Machine"],
     "Position yourself securely on the machine and brace your core. Extend one hip against the pad without arching your back, then return slowly."),
    ("Kettlebell Swings", "تأرجح الكيتل بيل", "strength", "intermediate", ["Glutes"], ["Hamstrings", "Core"], ["Kettlebell"],
     "Hinge at the hips and guide the kettlebell between your thighs. Drive your hips forward to swing it to chest height, then let it return smoothly."),
    ("Good Morning", "انحناء الجذع بالبار", "strength", "intermediate", ["Hamstrings"], ["Glutes", "Back", "Core"], ["Barbell"],
     "Rest a barbell across your upper back and brace. Hinge at the hips with a soft knee bend, then return to standing by driving the hips forward."),
    ("Nordic Hamstring Curl", "ثني أوتار الركبة نورديك", "strength", "advanced", ["Hamstrings"], ["Glutes", "Calves"], ["Bodyweight"],
     "Kneel with your ankles securely anchored. Keep your body straight as you lower forward under control, catch yourself with your hands, and return carefully."),
    ("Donkey Calf Raise", "رفع البطات بطريقة الحمار", "strength", "beginner", ["Calves"], [], ["Machine"],
     "Position the balls of your feet on the platform and hinge forward against the support. Raise your heels, pause, then lower through a comfortable stretch."),
    ("Side Plank Hip Adduction", "تقريب الورك من وضعية البلانك الجانبي", "strength", "intermediate", ["Adductors"], ["Core"], ["Bench", "Bodyweight"],
     "Support your upper body on one forearm and place the top leg on a bench. Lift your hips and lower leg toward the bench, then return with control and switch sides."),
    ("Wrist Curl", "ثني الرسغ", "strength", "beginner", ["Forearms"], [], ["Barbell"],
     "Sit with your forearms supported and palms facing up. Curl your wrists to raise the bar, then lower it slowly through a comfortable range."),
    ("Reverse Wrist Curl", "ثني الرسغ العكسي", "strength", "beginner", ["Forearms"], [], ["Barbell"],
     "Sit with your forearms supported and palms facing down. Raise the backs of your hands by extending your wrists, then lower slowly."),
    ("Farmer's Walk", "مشي المزارع", "strength", "intermediate", ["Forearms"], ["Core", "Shoulders"], ["Dumbbell", "Kettlebell"],
     "Hold a weight in each hand, stand tall, and brace your core. Walk with short, steady steps while keeping your shoulders level."),
    ("Ab Wheel Rollout", "تمرير عجلة البطن", "strength", "intermediate", ["Core"], ["Shoulders"], ["Ab Wheel"],
     "Kneel with both hands on the wheel. Brace your abdomen and roll forward only as far as you can keep your lower back controlled, then return."),
    ("Cable Half Kneeling Pallof Press", "ضغط بالوف بالكابل من الركوع", "strength", "beginner", ["Core"], ["Shoulders", "Glutes"], ["Cable Machine"],
     "Kneel sideways to a cable set at chest height and hold the handle at your chest. Press your hands forward without letting your torso rotate, then return."),
    ("Turkish Get-Up", "النهوض التركي", "strength", "advanced", ["Core"], ["Shoulders", "Glutes"], ["Kettlebell"],
     "Lie on your back holding a light kettlebell above one shoulder. Keep your eyes on it and move through a controlled sequence to stand, then reverse the steps."),
    ("Jumping Jack", "القفز بفتح وإغلاق الذراعين", "cardio", "beginner", ["Quadriceps"], ["Calves", "Shoulders"], ["Bodyweight"],
     "Stand tall with arms at your sides. Jump your feet apart as you raise your arms overhead, then return to the start at a steady pace."),
    ("Battle Rope", "تمارين حبال المعركة", "cardio", "intermediate", ["Shoulders"], ["Back", "Core"], ["Battle Rope"],
     "Hold one rope end in each hand with a stable stance. Alternate raising and lowering your arms to create continuous waves while keeping your torso braced."),
    ("Skater", "قفز المتزلج الجانبي", "cardio", "beginner", ["Glutes"], ["Quadriceps", "Calves"], ["Bodyweight"],
     "Hop laterally from one foot to the other, landing softly with a slight knee bend. Swing your arms naturally and keep each landing controlled."),
    ("High Knees Lift Run", "الجري مع رفع الركبتين", "cardio", "beginner", ["Quadriceps"], ["Calves", "Core"], ["Bodyweight"],
     "Run in place while lifting each knee toward hip height. Stay tall, land lightly, and maintain a controlled rhythm."),
    ("Bicycle Crunch", "كرنش الدراجة", "strength", "beginner", ["Core"], [], ["Bodyweight"],
     "Lie on your back with knees bent and hands lightly behind your head. Bring one elbow toward the opposite knee while extending the other leg, then alternate sides without pulling on your neck."),
    ("Incline Treadmill Run", "الجري على السير المائل", "cardio", "intermediate", ["Quadriceps"], ["Calves", "Glutes"], ["Treadmill"],
     "Set a moderate treadmill incline and a sustainable speed. Run with short, controlled strides, stay upright, and reduce the pace if your form falters."),
    ("Kneeling Hip Flexor Stretch", "إطالة مثنيات الورك من الركوع", "flexibility", "beginner", ["Quadriceps"], ["Glutes"], ["Bodyweight"],
     "Kneel with one knee down and the other foot planted ahead. Gently tuck your pelvis and shift your hips forward until you feel a stretch at the front of the rear hip, then switch sides."),
]

RETIRED_EXERCISES = {
    "Chest-supported Row",
    "Couch Stretch",
    "Decline Bench Press",
    "Donkey Calf Raise",
    "Dumbbell Triceps Extension",
    "Hanging Leg Raise",
    "Reverse Wrist Curl",
    "Rope Triceps Pushdown",
    "Single-leg Balance",
    "Side Plank Hip Adduction",
    "Skater",
    "Straight-bar Triceps Pushdown",
    "Turkish Get-Up",
    "Treadmill Walking",
    "Wrist Curl",
    "World's Greatest Stretch",
    "Zottman Curl",
}

EXERCISE_IMAGES = {
    "Incline Dumbbell Press": "exercises/dc74f364a46a21990c1a9286fff620a30593fff1d81e43051e3b8dcdccbe8040.gif",
    "Push-up": "exercises/e91037e4d1c2d60f5ae9203ae70d1c45a9beaaa7c2b0534b5b941c84faa7c2fe.gif",
    "Dumbbell Fly": "exercises/b299ef7e1b878824ff5987f30c00e93ccb9e8bd6a2e127bde51a7422e0a1cdc6.gif",
    "Pull-up": "exercises/aa651e6c2e51931925be10c0a0785f08b152ca73ddb82c89ac920ec8c61ad6e6.gif",
    "Lat Pulldown": "exercises/38e3bb904321cc1f279813ced330d34bc31b6df660b921ef590b1145a2e279fc.gif",
    "Seated Cable Row": "exercises/961f6b7e825040126b1f7c0e148f5cf4c6b2e0ac88d84760b37f8965aca223d8.gif",
    "Barbell Curl": "exercises/5bd283ab61519321ecbef3d2093abfc4c592484fcb2b455a6c1c205d15b0acbb.gif",
    "Hammer Curl": "exercises/551aa9a10b21863dab78ec8e39d5aba5d8ff938fdb771eb4a06ae291ac9aad23.gif",
    "Romanian Deadlift": "exercises/662a9ce6ab4e307e7cd405fca0cbc4f45f8fa88053d75caccb027db0d4d00e41.gif",
    "Plank": "exercises/4ef5ad2d6159d5fabebca0d422f2e58eefe83ae271ffcb54aacb46807408e56e.gif",
    "Rowing Machine": "exercises/171ba023e723695c934801ec33aafb822676d8bd62095b44519ce6a08a378498.gif",
    "Jump Rope": "exercises/11ea7315c5300e909b82524ea13a53a7ad237ed0cd4f3963b153176a1a951b04.gif",
    "Incline Barbell Bench Press": "exercises/dc138127178710a9404a26664b00076ef3e0e356ffb8589c8833d81a5cde8c08.gif",
    "Pec Deck Fly": "exercises/96752bb9f4111d0a13c8cb391f36722ae327b6665aa7bbddfc6c36cc292c8864.gif",
    "Close-grip Lat Pulldown": "exercises/95614eec578f516445941905989336317292545007f9af32408cff8b9142aa35.gif",
    "T-bar Row": "exercises/da456b4dece811a192183c88feb68152e1b4817784d17ed3c0ae6282cd284cd8.gif",
    "Assisted Pull-up": "exercises/2cb88d60d57101bb7b6d0bb27515f635e94386fa986d50f62de21e313efe9430.gif",
    "Dumbbell Shoulder Press": "exercises/e7c68ce6d703d890e15051d0503abdb75fe357b3f049209f7eca865ed02aba93.gif",
    "Cable Lateral Raise": "exercises/ed571c9c8bd46921dde0f7545eccc540c2b90965bfd29cfc701f1c83b40c0379.gif",
    "Dumbbell Front Raise": "exercises/fe5ce983cef8a395a64ed5afa617d490c203f667a87a908c6c1f8015dc92d578.gif",
    "Concentration Curl": "exercises/c8da9fdbb11bc09ca8f60a0f21d661eddb24786300751dbf1df5b924480edc10.gif",
    "Dumbbell Triceps Extension": "exercises/f237036e1f30718d839b7ac7f23770108cc9babdd62125325feb2ff0fd41ade7.gif",
    "Leg Press": "exercises/95398be068086f450d03ed4554aecc1b4200254d68bde59af0433ec547838663.gif",
    "Leg Extension": "exercises/c0df9b3a26ad5df3acd2f35fd8329022235f52c9d4ac6de626cba256af4b34da.gif",
    "Seated Leg Curl": "exercises/0ee925a7430d1a6adb02e930460bad3f6f0413021e26df7127b6f5dedf1d9cb7.gif",
    "Smith Machine Squat": "exercises/12cfe08c2baed7a6cc10f68f7847b33a5a5cdc14dc1974c19396ea5dace263ac.gif",
    "Dumbbell Romanian Deadlift": "exercises/3830cb7686a20e4a0255c30434a4d8a2e65b32e973a006b435fa7a30806b2c55.gif",
    "Hip Abduction Machine": "exercises/329bbb77643d3713c2270cbd50e7801f3708a3ddf11e67deb429b96a05746306.gif",
    "Hip Adduction Machine": "exercises/bf915b406aca4206256b44cb150a232fb441036910f7e606c53fb14394f9a031.gif",
    "Leg Press Calf Raise": "exercises/96914b39c399a123ecbbad7a1c6057a48b159498b72059f36a831ebb72e22b23.gif",
    "Reverse Crunch": "exercises/294214e3955f19279e38a6fa9a367871de905ea46df5a2cc057803db37d665a5.gif",
    "Side Plank": "exercises/9758189baa4011f690852992aca866077eccadd3f83df5d6541b66867d64c9d1.png",
    "Russian Twist": "exercises/b12c305c19ec45d64d7d3ff21fd6b87fff1018c5cc86a754984ebe6603e4e956.gif",
    "Stationary Bike": "exercises/ea8d837404ec5a01c28dfd00ae4276e7fcd493139368a0f799bc47a3c5029c87.gif",
    "Elliptical Machine": "exercises/33b66393d433586c876926fa81a8f6765d7065a7d8e592dce7982f4127a8b121.gif",
    "Dumbbell Pullover": "exercises/e702511da78b88a21e2f75e91e8712c9212980067aec967d90f40780dd0aa86a.gif",
    "Arnold Press": "exercises/65e32a83f01e2075b6928152631f3e907b351bd065609a4ec4429e8e1dc637bc.gif",
    "Zottman Curl": "exercises/a049149f5d535b2ee468c9a85d9291a0fe6c7cddca2d6bb5433ab484c60353d6.gif",
    "Close-grip Bench Press": "exercises/d08389b37941320263d18715c92c2920f5957e39f7ef24de748a462c60d62d6d.gif",
    "Sumo Deadlift": "exercises/fac8d02cb05685dbe694acc6dbc3a2a670fc7dbc52016040a41b36c68676555c.gif",
    "Mountain Climber": "exercises/612bd5659ab0a701964d99df7f4449a220895439432d92fc6263eeb32fbce847.gif",
    "Seated Back Extension": "exercises/c465f1522d6a22fb6c3fd7ba98fdd0a22c5b4755615f15e6403e11cc792876d9.gif",
    "Inverted Row": "exercises/e627bd8e1d51a060471d23fa5dad31a4b9ad115b3bd063a0b6c2ebba9409b3c8.gif",
    "One Arm Landmine Row": "exercises/4212e344224999589a494b6b20f627b558cac5f4d1c0a7825bad1a95fcd7a003.gif",
    "Barbell Floor Press": "exercises/1f24a33d007b6adcc73dc624a14e74d19baad08c40650bb8507e771c60c54371.gif",
    "Incline Landmine Press": "exercises/ccde1ed451d0398b4ce4d61a14cc2b1784a2ddd049a7e30042efd448d8ee9e99.gif",
    "Cable Upright Row": "exercises/43c6719cd217209055e16d8e02b997a59f3991ba6f8449420f772b5d7c2e06e8.gif",
    "Wall Sit": "exercises/5040bf96f9a972407998c875fc63bab5d1980648a989e321ad3b5011ca15537d.png",
    "Glute Bridge": "exercises/947e3cb0b6849ab159dc3b81e8e29e9b1c1f90092bdb10624d4045c73832723f.gif",
    "Cable Pull Through": "exercises/cdb8056693eef4cde09e68f238eb57eb534ab5138b0a112a25708b347ef55425.gif",
    "Glute Kickback Machine": "exercises/d5ba21d65a6d2480506e35b47dacc8db49ed73895fbd400eeb7d5be7e5095b2e.gif",
    "Kettlebell Swings": "exercises/8116ae66e65d65ee769abf605868cf66dd8e45cabc3a7754465b8b56c2b8fd41.gif",
    "Good Morning": "exercises/4f8a3b0ca59d2fb1fc196c476cb48cdb76fa0119e04a8aacf5ee6c2a0847d8a5.gif",
    "Nordic Hamstring Curl": "exercises/e41c3851c0b7c2445a3c872aede45e0857d50271de5d9da2613a8a365ac98f6f.gif",
    "Donkey Calf Raise": "exercises/fb742084c5d60eccf61ee838afbeba75a1d293a8700906f1b2c6441b89779209.gif",
    "Side Plank Hip Adduction": "exercises/cab297864cecd724d65fbae4c3d6b9e8ad14976f220eeb8ebfceaa6a44cc75ad.gif",
    "Wrist Curl": "exercises/840131cdafc65fcbcf8ffe422ea4e6adecf0b9bc5d12f796ee1e79f98e7c0519.gif",
    "Reverse Wrist Curl": "exercises/98645e00240c5d0898eff811a9e27607d0e6efc0437db37829e0abf51d9586c4.gif",
    "Farmer's Walk": "exercises/8d41a46a82747fd955fe5eed22999327ea31609f1d5f9a86d59ef8f6c2b8c29f.gif",
    "Ab Wheel Rollout": "exercises/0a86e9089ccc20f87fddf26d6b76d8617e0215fe53ffbb50bb6b1a0f90da2cdf.gif",
    "Cable Half Kneeling Pallof Press": "exercises/da33771e906d3c212f39390a5cd5ea3f338b436b10507717f1c966380e7ef37e.gif",
    "Turkish Get-Up": "exercises/568f1927b129c06c240b5beaf28eb17cbead24021a17a1e44f1378560628b738.gif",
    "Jumping Jack": "exercises/3d367f0fd4696a26653af5fbc86db1bc36bcba51e00ace4036902f450d2e8a06.gif",
    "Battle Rope": "exercises/8117649d8c3135d97b99da73534323b2c90dc50f11955a881ea14eec623d00a2.gif",
    "Skater": "exercises/0a0889480c287ed023abadaf98f4e8ad451aadb7ac76c80dbf2986f2134aea8e.gif",
    "High Knees Lift Run": "exercises/5587ebf24a42305195bb6f45a4a7ba11ec3bccab51b882148e6681ac4a095de5.gif",
    "Barbell Bench Press": "exercises/5d8f4c247630ccba9b8df09432d6174a96f8df3d3450164a6cabbde766de93a8.gif",
    "Barbell Row": "exercises/4c75809204cb859ed8b9695e25cc6641e32fbe67e2ad4df41158b1163992276b.gif",
    "Lateral Raise": "exercises/0bf65931e27cd3ca057106280e69093aa5872f0fb1e254d67e839e38def7e8bc.gif",
    "Triceps Pushdown": "exercises/b28a283588ffb26882081c53ceab0b0d20b50d8faf8c147c57961dc499486e90.gif",
    "Back Squat": "exercises/d371660666055877811a7f3225afd3cf543280a9ca48ca9d96a17b2d4d01c651.gif",
    "Front Squat": "exercises/a8658eb9b6dada8ea04b183021d276aa2efe1b30277ddaea80eb066205303e07.gif",
    "Conventional Deadlift": "exercises/888c706085921cf9d26af8cf28acfec0b8cc3c829d3ff37a49f4c8cb6191de2a.gif",
    "Walking Lunge": "exercises/24abd3c5f2e0ef749db7495bd42049ffee857a9e8808081e44fa1283726fa140.gif",
    "Hip Thrust": "exercises/278f9eabb0849f09ec456f713ef6cae02559f90b4149b5cf3d9e96ee71ef213a.gif",
    "Standing Calf Raise": "exercises/f2eec2e79b1c380477f9ab7f3d785829e65572b0bf2f9685b35f26aeeef76332.gif",
    "Hanging Knee Raise": "exercises/fcd8aeea97c55cf7ccb887c6cc5fab69f453ca3e6d5f65398df8ea77e8bae055.gif",
    "Cable Crunch": "exercises/4fd055f09365294dd94509fe75849f8b617b840ae813cb465b24c901d43de260.gif",
    "Treadmill Run": "exercises/643204256c8a36a93e32fba282fdf4b3876f302223040f4899e4933b840dbe3f.gif",
    "Burpee": "exercises/462f45bbb25635d3e6dd74403f8929539821cf6106e21f5180289cff3d24e86a.gif",
    "Flat Dumbbell Bench Press": "exercises/c0cb28c6d53497c393dbd983235dca0e701e68296310e33fe220ac445c1c7a47.gif",
    "Machine Chest Press": "exercises/b0a1c7a54d2d765231e7ad87b543266fbd6ed80d2b7505ae4650332bc6b075ee.gif",
    "Cable Chest Fly": "exercises/39e2a11c814f340ef501cfcac761739a2f382afaebab3cf3b53aef1993600f46.gif",
    "One-arm Dumbbell Row": "exercises/06906bcfab26e3d41023f3b7b28c4222fee43b1c721f09d33cfa3becf21fc082.gif",
    "Machine Seated Row": "exercises/5dbdcf2af41a94e0755ea7cca958a005c11cdae49cb31f0da14b3e9b39c42fd3.gif",
    "Straight-arm Cable Pulldown": "exercises/6b1143ef5f1aa8e0dc1ba63617d70dbd239ee02ecba674a2a195702a6d3db61e.gif",
    "Machine Shoulder Press": "exercises/81e999ce017d551b8b61b837dfbd9d46a304029106532e4b408992c9caac1457.gif",
    "Dumbbell Biceps Curl": "exercises/c263baf392cb86809b0613739e8a6734f4c36c1949e837632eba645c2ca6d563.gif",
    "Incline Dumbbell Curl": "exercises/578f78fa999c9e1c50d03e5fd9c36ad0ae56a84db8c763c6ee2f5adb959a6228.gif",
    "Preacher Curl": "exercises/55bb46d550be00a5d1a70099c39c4147e088b31a1c23996fd7d5ebc98e2f5ca8.gif",
    "EZ-bar Curl": "exercises/cb0648bfce6b44a261095ac04ff6db89c4cbb4ef09d2752d3f80476fd42e103c.gif",
    "Rope Triceps Pushdown": "exercises/b28a283588ffb26882081c53ceab0b0d20b50d8faf8c147c57961dc499486e90.gif",
    "Assisted Dip": "exercises/4a17099433d00ff4fbb082aef2cd0dc50d634c990b533824815632597846a1e5.gif",
    "Hack Squat": "exercises/7b320c95ae4c23b327ea0f8012e78f9a117f12bd9ad399272585377d7b87e84b.gif",
    "Goblet Squat": "exercises/4e0af5117c7e2e865323724ca9e9d590d573b826118c90742a80551b2c341b5f.gif",
    "Lying Leg Curl": "exercises/b61de95269e5df52a12e0140243c239aad51b323f72dd9cca9b53cea51787295.gif",
    "Seated Calf Raise": "exercises/06677479afca626e0e13fd06cc77c654b3fdf01cc4ac3d6892272c99e179b22c.gif",
    "Abdominal Crunch": "exercises/77af4db4ca1c60c5628e8b9279a273e259f80d8267c740f5f4a7f6737acf5a7b.gif",
    "Stair Climber": "exercises/73727fcf7e97c76bc0215da0a8ca1a9476775e3ab962272fe8ec7b3938e99c1b.gif",
    "Outdoor Running": "exercises/5dd60a2797f4c623f1b5c3ea9f8e58b30a79a402e269dbab05954bfd81cdefb4.gif",
    "Brisk Walking": "exercises/0ed9fbdd54e40b34a45acc284e814691454b9f7f9ede6299006d2d766d33e18e.gif",
    "Single-arm Cable Row": "exercises/d88588017c234d028f38046fb670356cca3e6728e3941f04d7121da95b9abe04.gif",
    "Reverse Curl": "exercises/e85fdd92a319d7381d3bfe84a7289779bdb493c8ac730cf9ddc60c60e73fdb98.gif",
    "Bench Dip": "exercises/b23f712f5b46bb63cbb2c71a9ab8244fdde913dbf7e2e7cf68d77ffef4e314de.gif",
    "Bicycle Crunch": "exercises/b92a90d1c4a849a367739f3b039de244e3d46c65ad507c58e91d6017334ce049.gif",
    "Incline Treadmill Run": "exercises/b6b68c0ee39bf8ba30a3aeb518c7cd8760ad605da73a684c8d2fe113ca8b195c.gif",
    "Bulgarian Split Squat": "exercises/b9690977db5902f036986669e9c92e6e2e0aac26b608139bf75be337a118565e.gif",
    "Cable Biceps Curl": "exercises/cddc7f21353cf636a5cc81b3c8806478f20faa8267f6a7db48b86a0ac7ab6321.gif",
    "Face Pull": "exercises/a69b7384080a9d3ee1c84a4b687605d1ebfb28d9fafd87ae724593b0f1b9f4de.gif",
    "Overhead Cable Triceps Extension": "exercises/9bbb485b55c04cffd93f46f1d832d602ec236582705d70ca740fcee616adc3fc.gif",
    "Dead Bug": "exercises/8f24c698614be8537cdbfcdfe9ebe266d8f5f55430422761452fa4fa9d999ecd.gif",
    "Lying Leg Raise": "exercises/d444ef245650dfffcf1888f88414bc90d1ef869950c323e5b5b4022432965644.gif",
    "Machine Standing Calf Raise": "exercises/f804f6c426447ac4d028df04a65d3c3fd39077d045349e9b1546d9a7e057b4c5.gif",
    "Overhead Press": "exercises/63fe9528df4c89ba1dcc80476f64a8736733dbc2644ea9fdeed7a16d6988cf3b.gif",
    "Overhead Triceps Extension": "exercises/f237036e1f30718d839b7ac7f23770108cc9babdd62125325feb2ff0fd41ade7.gif",
    "Rear Delt Fly": "exercises/048b78e9f1c6dc9a34e229efdda970852767a21db20ea962e83c09f4fdb7f090.gif",
    "Reverse Pec Deck": "exercises/1f74998e4c5cba158df6666b9463f7837dfe9b0e16dae2e04ae916b381ca2484.gif",
    "Skull Crusher": "exercises/be2d69d1dabd1b3a3d63a717fd761afba30a44a399b197780c2c3b3e781c8788.gif",
    "Step-up": "exercises/9fb36dd06cb25aa6922da5cab2df0a2cdbe55046578ae89045446fb06f29d26f.gif",
    "Kneeling Hip Flexor Stretch": "exercises/56cf258ed23fd73fedcc7f0a0745897b1cf984d204c9ee4b546f5c293c042a4d.gif",
}


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
            image = EXERCISE_IMAGES.get(name, "")
            exercise, was_created = Exercise.objects.get_or_create(
                name=name,
                defaults={
                    "name_ar": name_ar,
                    "exercise_type": exercise_type,
                    "difficulty": difficulty,
                    "instructions": instructions,
                    "description": description,
                    "image": image,
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
                update_fields = ["name_ar", "exercise_type", "difficulty", "instructions"]
                if image:
                    exercise.image = image
                    update_fields.append("image")
                exercise.save(update_fields=update_fields)

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

        for exercise in Exercise.objects.filter(name__in=RETIRED_EXERCISES, created_by__isnull=True):
            description = f"{exercise.name} ({exercise.exercise_type}, {exercise.difficulty})."
            if self._is_seed_managed(exercise, description) and exercise.is_active:
                exercise.is_active = False
                exercise.save(update_fields=["is_active"])

        self.stdout.write(
            f"Seeded {len(groups)} muscle groups, {len(equipment)} equipment items, "
            f"created {created} exercises, updated {updated}, skipped {skipped} user-managed records."
        )

    @staticmethod
    def _is_seed_managed(exercise, expected_description):
        return exercise.created_by_id is None and exercise.description == expected_description
