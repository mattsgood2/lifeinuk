# quiz/views.py

import os
import random
import re
import string

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Q
from .models import Question
from .forms import UploadFileForm
from django.http import FileResponse, HttpResponseBadRequest
from tempfile import NamedTemporaryFile
from gtts import gTTS

# ----------------- GLOBAL EXAM SETTINGS -----------------

EXAM_QUESTION_COUNT = 24          # questions per exam
EXAM_DURATION_SECONDS = 45 * 60  # 45 minutes


# ----------------- HELPER: NORMALISE ANSWERS -----------------

def normalise_answer(value: str) -> str:
    """
    Normalise answers for comparison:
      - handle None safely
      - strip spaces
      - lowercase
      - strip punctuation at both ends
    So:
      'True.'  ' TRUE! '  'true??'  all become 'true'
    """
    if not value:
        return ""
    return value.strip().lower().strip(string.punctuation)


# ----------------- HELPER: QUESTION POOL BY MODE -----------------

def _get_question_queryset_for_mode(mode: str):
    """
    Interpret `mode` flexibly:

      - "all"      -> all questions
      - "practice"  -> mixed realistic practice (general + common + hardest)
      - category key -> filter by category (general / hardest / cheatsheet / common)
      - topic key    -> filter by topic (history / government / culture / geography / other)
    """
    mode = (mode or "").strip().lower()

    # 1. ALL QUESTIONS
    if mode == "all":
        return Question.objects.all()

    # 2. PRACTICE MIX
    if mode == "practice":
        return Question.objects.filter(
            category__in=["general", "common", "hardest"]
            # add "cheatsheet" if you want them included as well:
            # category__in=["general", "common", "hardest", "cheatsheet"]
        )

    # 3. CATEGORY (matches CATEGORY_CHOICES keys)
    category_keys = {key for key, _ in Question.CATEGORY_CHOICES}
    if mode in category_keys:
        return Question.objects.filter(category=mode)

    # 4. TOPIC (matches TOPIC_CHOICES keys)
    topic_keys = {key for key, _ in Question.TOPIC_CHOICES}
    if mode in topic_keys:
        return Question.objects.filter(topic=mode)

    # 5. Unknown -> empty queryset
    return Question.objects.none()


# ----------------- SIMPLE MENU -----------------

def practice_menu(request):
    return render(request, "quiz/practice_menu.html", {})


# ----------------- UPLOAD QUESTIONS -----------------

@user_passes_test(lambda u: u.is_authenticated and u.is_staff)
def upload_questions(request):
    """
    Upload a plain text file containing Q&A blocks.

    Accepted formats (all OK):

    Q: When was the Magna Carta signed?
    A: 1215.

    question: When was the Magna Carta signed?
    answer: 1215.
    """
    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            topic = form.cleaned_data["topic"]
            category = form.cleaned_data["category"]
            file_obj = request.FILES["file"]
            content = file_obj.read().decode("utf-8", errors="ignore")

            # Derive subcategory from filename
            filename = file_obj.name
            base, _ = os.path.splitext(filename)
            subcategory = base.replace("_", " ").title().strip()

            parsed = 0
            created = 0
            updated = 0
            current_q = None
            current_a = None

            def save_pair(q_text, a_text):
                nonlocal parsed, created, updated
                if not q_text or not a_text:
                    return
                parsed += 1
                q_clean = q_text.strip()
                a_clean = a_text.strip()

                obj, was_created = Question.objects.update_or_create(
                    # question text as the unique-ish key (case-insensitive)
                    question_text__iexact=q_clean,
                    defaults={
                        "question_text": q_clean,
                        "answer_text": a_clean,
                        "topic": topic,
                        "category": category,
                        "subcategory": subcategory,
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

            # Accept: "Q:", "question:", "A:", "answer:" (any case, optional spaces)
            q_pattern = re.compile(r"^\s*(question|q)\s*:", re.IGNORECASE)
            a_pattern = re.compile(r"^\s*(answer|a)\s*:", re.IGNORECASE)

            for raw_line in content.splitlines():
                line = raw_line.strip()
                if not line:
                    continue

                if q_pattern.match(line):
                    # save previous pair
                    if current_q and current_a:
                        save_pair(current_q, current_a)
                    current_q = line.split(":", 1)[1].strip()
                    current_a = None

                elif a_pattern.match(line):
                    current_a = line.split(":", 1)[1].strip()

                else:
                    # continuation lines
                    if current_a is not None:
                        current_a += "\n" + line
                    elif current_q is not None:
                        current_q += "\n" + line

            # flush last pair
            if current_q and current_a:
                save_pair(current_q, current_a)

            messages.success(
                request,
                f"Parsed {parsed} Q/A pairs. Created {created}, updated {updated}."
            )
            return redirect("practice_menu")
    else:
        form = UploadFileForm()

    return render(request, "quiz/upload.html", {"form": form})

# ----------------- MULTIPLE-CHOICE PRACTICE -----------------


def mc_quiz(request, mode):
    """
    Multiple-choice practice view.

    Supports:
      - mode = 'all', 'practice', 'general', 'hardest', 'common', 'history', etc.
      - ?sub=SubcategoryName
      - ?topic=history / government / culture / geography / other
      - ?q=free text search (e.g. 'king', 'Cnut', '1945')
    """

    # --- read filters from querystring ---
    current_sub = (request.GET.get("sub") or "").strip() or None
    current_topic = (request.GET.get("topic") or "").strip() or None
    search_query = (request.GET.get("q") or "").strip() or None

    # --- base queryset for this mode ---
    base_qs = _get_question_queryset_for_mode(mode)

    # subcategory list for dropdown (based only on mode, not search)
    subcategories = (
        base_qs.exclude(subcategory__isnull=True)
              .exclude(subcategory__exact="")
              .values_list("subcategory", flat=True)
              .distinct()
              .order_by("subcategory")
    )

    # apply filters
    qs = base_qs
    if current_sub:
        qs = qs.filter(subcategory=current_sub)
    if current_topic:
        qs = qs.filter(topic=current_topic)
    if search_query:
        qs = qs.filter(
            Q(question_text__icontains=search_query) |
            Q(answer_text__icontains=search_query) |
            Q(subcategory__icontains=search_query)
        )

    total = qs.count()
    question = None
    choices = []
    selected = None
    is_correct = None
    seed = None

    # --- session keys for stats ---
    counter_key_correct = f"mc_correct_{mode}"
    counter_key_incorrect = f"mc_incorrect_{mode}"

    if counter_key_correct not in request.session:
        request.session[counter_key_correct] = 0
    if counter_key_incorrect not in request.session:
        request.session[counter_key_incorrect] = 0

    # --- admin reset ---
    if request.method == "POST" and "reset_stats" in request.POST:
        if request.user.is_authenticated and request.user.is_staff:
            request.session[counter_key_correct] = 0
            request.session[counter_key_incorrect] = 0
            request.session.modified = True
        return redirect("quiz_mc", mode=mode)

    # ------------ SMART CHOICE BUILDER ------------

    def build_choices_with_seed(q, seed_value: int):
        """
        Smarter multiple-choice options:

        - True/False questions -> only 'True' and 'False'
        - Year / date-style answers -> other year/date-style distractors
        - Other answers -> text distractors of similar length
        """
        rng = random.Random(seed_value)
        correct_raw = (q.answer_text or "").strip()
        question_text = (q.question_text or "").strip()
        norm_answer = correct_raw.lower().strip(" .!?")

        # -------- helpers --------
        def is_true_false_question() -> bool:
            qt = question_text.lower()
            return qt.startswith("true or false") or norm_answer in ("true", "false")

        # match things like 1066, 1415, 1450s, 2010s
        year_match = re.search(r"(1[0-9]{3}|20[0-9]{2})s?", correct_raw)
        year_num = int(year_match.group(1)) if year_match else None

        # -------- TRUE / FALSE --------
        if is_true_false_question():
            options = ["True", "False"]
            # safer: only treat exact 'true' as True
            correct_clean = "True" if norm_answer == "true" else "False"
            if correct_clean not in options:
                options.append(correct_clean)
            rng.shuffle(options)
            return options

        # -------- YEAR / DATE-STYLE ANSWERS --------
        if year_num is not None:
            # keep the wording pattern, e.g. "In the 1450s."
            prefix = correct_raw[:year_match.start()]
            suffix = correct_raw[year_match.end():]
            has_s = "s" in year_match.group(0)

            # collect other year values from DB
            other_years = set()
            for obj in Question.objects.exclude(id=q.id):
                a = (obj.answer_text or "")
                m2 = re.search(r"(1[0-9]{3}|20[0-9]{2})s?", a)
                if m2:
                    other_years.add(int(m2.group(1)))

            other_years.discard(year_num)
            other_years = list(other_years)
            rng.shuffle(other_years)

            distract_years = [y for y in other_years[:3]]

            # if we don't have enough, synthesise nearby years
            while len(distract_years) < 3:
                delta = rng.choice([-10, -5, -1, 1, 5, 10])
                y = year_num + delta
                if 1000 <= y <= 2099 and y not in distract_years and y != year_num:
                    distract_years.append(y)

            def make_phrase(y: int) -> str:
                y_str = f"{y}{'s' if has_s else ''}"
                return f"{prefix}{y_str}{suffix}"

            options = [make_phrase(year_num)] + [make_phrase(y) for y in distract_years[:3]]
            rng.shuffle(options)
            return options

        # -------- GENERAL TEXT ANSWERS --------
        correct = correct_raw
        pool = list(Question.objects.exclude(id=q.id))
        candidates = []

        for obj in pool:
            text = (obj.answer_text or "").strip()
            if text and text != correct:
                candidates.append(text)

        # sort by similar length
        candidates = sorted(
            candidates,
            key=lambda t: abs(len(t) - len(correct))
        )

        near = candidates[:20]
        rng.shuffle(near)
        distractors = []

        for d in near:
            d = d.strip()
            if d and d not in distractors and d != correct:
                distractors.append(d)
            if len(distractors) == 3:
                break

        # pad if still short
        extra_pool = [
            (obj.answer_text or "").strip()
            for obj in pool
            if (obj.answer_text or "").strip() not in distractors
            and (obj.answer_text or "").strip() != correct
        ]
        rng.shuffle(extra_pool)
        for d in extra_pool:
            distractors.append(d)
            if len(distractors) == 3:
                break

        # final options
        options = [correct] + distractors[:3]
        # de-duplicate while preserving order
        seen = set()
        dedup = []
        for o in options:
            if o not in seen:
                dedup.append(o)
                seen.add(o)
        options = dedup

        rng.shuffle(options)
        return options

    # ------------ MAIN PRACTICE FLOW ------------

    if total > 0:
        # --- NEXT QUESTION BUTTON ---
        if request.method == "POST" and "next" in request.POST:
            # Just pick a new random question; don't change stats
            question = random.choice(list(qs))
            seed = random.randint(1, 10_000_000)
            choices = build_choices_with_seed(question, seed)
            # selected / is_correct stay as None so template shows fresh state

        # --- CHECK ANSWER SUBMISSION ---
        elif request.method == "POST" and "choice" in request.POST and "question_id" in request.POST:
            q_id = int(request.POST.get("question_id"))
            selected = request.POST.get("choice")

            try:
                question = Question.objects.get(id=q_id)
            except Question.DoesNotExist:
                question = None

            try:
                seed = int(request.POST.get("seed", "0"))
            except ValueError:
                seed = 0

            if question:
                choices = build_choices_with_seed(question, seed)

                # NORMALISED, CASE/PUNCTUATION-INSENSITIVE COMPARISON
                correct_answer_raw = (question.answer_text or "")
                correct_answer = correct_answer_raw.strip()

                selected_norm = normalise_answer(selected or "")
                correct_norm = normalise_answer(correct_answer)

                is_correct = (selected_norm == correct_norm)

                if is_correct:
                    request.session[counter_key_correct] += 1
                else:
                    request.session[counter_key_incorrect] += 1

                request.session.modified = True

        # --- FIRST LOAD / NON-POST ---
        else:
            question = random.choice(list(qs))
            seed = random.randint(1, 10_000_000)
            choices = build_choices_with_seed(question, seed)

    # Stats
    correct_count = request.session.get(counter_key_correct, 0)
    incorrect_count = request.session.get(counter_key_incorrect, 0)
    answered = correct_count + incorrect_count

    accuracy = round(correct_count * 100 / answered) if answered > 0 else None
    progress_percent = (
        min(round(answered * 100 / total), 100) if (total > 0 and answered > 0) else 0
    )

    topic_choices = Question.TOPIC_CHOICES  # for dropdown

    return render(request, "quiz/mc_quiz.html", {
        "mode": mode,
        "question": question,
        "choices": choices,
        "selected": selected,
        "is_correct": is_correct,
        "seed": seed,
        "total": total,
        "correct_count": correct_count,
        "incorrect_count": incorrect_count,
        "answered": answered,
        "accuracy": accuracy,
        "progress_percent": progress_percent,
        "subcategories": subcategories,
        "current_sub": current_sub,
        "current_topic": current_topic,
        "topic_choices": topic_choices,
        "search_query": search_query,
    })


# ----------------- EXAM MODE -----------------

def exam_quiz(request):
    """
    PSI-style exam:
      - Fixed number of questions (EXAM_QUESTION_COUNT)
      - Linear exam, one by one
      - Timer stored in session
      - Review at the end
    """
    session = request.session

    # 🔹 Always start a fresh exam on a plain GET request.
    if request.method == "GET":
        for key in [
            "exam_active",
            "exam_question_ids",
            "exam_index",
            "exam_correct",
            "exam_incorrect",
            "exam_time_left",
            "exam_review",
        ]:
            session.pop(key, None)
        session.modified = True

    # -------- START NEW EXAM IF NEEDED --------
    if not session.get("exam_active"):
        all_ids = list(Question.objects.values_list("id", flat=True))
        if len(all_ids) <= EXAM_QUESTION_COUNT:
            selected_ids = all_ids
        else:
            selected_ids = random.sample(all_ids, EXAM_QUESTION_COUNT)

        session["exam_active"] = True
        session["exam_question_ids"] = selected_ids
        session["exam_index"] = 0
        session["exam_correct"] = 0
        session["exam_incorrect"] = 0
        session["exam_time_left"] = EXAM_DURATION_SECONDS
        session["exam_review"] = []
        session.modified = True

    ids = session.get("exam_question_ids", [])
    index = session.get("exam_index", 0)
    correct_count = session.get("exam_correct", 0)
    incorrect_count = session.get("exam_incorrect", 0)
    time_left = session.get("exam_time_left", EXAM_DURATION_SECONDS)
    review = session.get("exam_review", [])

    total = len(ids)
    finished = False
    selected = None
    is_correct = None
    question = None
    choices = []
    seed = None

    # -------- UPDATE TIMER FROM POST --------
    if request.method == "POST":
        tl_str = request.POST.get("time_left")
        try:
            tl = int(float(tl_str))
            time_left = max(tl, 0)
        except (TypeError, ValueError):
            pass
        session["exam_time_left"] = time_left
        session.modified = True

        if time_left <= 0:
            finished = True

    # -------- FINISH CONDITIONS --------
    if index >= total:
        finished = True

    if finished:
        context_review = []
        for item in review:
            context_review.append({
                "question": item["question"],
                "your_answer": item.get("your_answer"),
                "correct_answer": item.get("correct_answer"),
                "is_correct": item.get("is_correct", False),
            })

        passed = correct_count >= 18  # Life in the UK style pass mark

        for key in [
            "exam_active", "exam_question_ids", "exam_index",
            "exam_correct", "exam_incorrect",
            "exam_time_left", "exam_review",
        ]:
            session.pop(key, None)
        session.modified = True

        minutes = time_left // 60
        seconds = time_left % 60

        return render(request, "quiz/exam.html", {
            "finished": True,
            "question": None,
            "choices": [],
            "current_index": total,
            "total": total,
            "correct": correct_count,
            "incorrect": incorrect_count,
            "passed": passed,
            "minutes": minutes,
            "seconds": seconds,
            "progress_percent": 100,
            "review": context_review,
        })

    # -------- EXAM IN PROGRESS --------
    q_id = ids[index]
    question = Question.objects.get(id=q_id)

    def build_choices(q, seed_value=0):
        correct = (q.answer_text or "").strip()
        same_topic = Question.objects.filter(topic=q.topic).exclude(id=q.id)
        pool = list(same_topic)
        if len(pool) < 3:
            pool = list(Question.objects.exclude(id=q.id))

        rng = random.Random(seed_value or q.id)
        rng.shuffle(pool)

        seen = {correct}
        distractors = []
        for cand in pool:
            ans = (cand.answer_text or "").strip()
            if ans and ans not in seen:
                seen.add(ans)
                distractors.append(ans)
            if len(distractors) == 3:
                break

        opts = [correct] + distractors
        rng2 = random.Random((seed_value or q.id) + 999_999)
        rng2.shuffle(opts)
        return opts

    if request.method == "POST" and request.POST.get("check") == "1":
        selected = request.POST.get("choice")
        seed_str = request.POST.get("seed")
        try:
            seed = int(seed_str) if seed_str is not None else 0
        except ValueError:
            seed = 0

        choices = build_choices(question, seed)

        # NORMALISED, CASE/PUNCTUATION-INSENSITIVE COMPARISON
        correct_answer_raw = (question.answer_text or "")
        correct_answer = correct_answer_raw.strip()

        selected_norm = normalise_answer(selected or "")
        correct_norm = normalise_answer(correct_answer)

        is_correct = (selected_norm == correct_norm)

        if is_correct:
            correct_count += 1
            session["exam_correct"] = correct_count
        else:
            incorrect_count += 1
            session["exam_incorrect"] = incorrect_count

        review.append({
            "question": question.question_text,
            "your_answer": selected,
            "correct_answer": correct_answer,
            "is_correct": is_correct,
        })
        session["exam_review"] = review
        session.modified = True

    elif request.method == "POST" and request.POST.get("next") == "1":
        index += 1
        session["exam_index"] = index
        session.modified = True

        if index >= total:
            return redirect("exam_quiz")

        q_id = ids[index]
        question = Question.objects.get(id=q_id)
        seed = random.randint(1, 10_000_000)
        choices = build_choices(question, seed)
        selected = None
        is_correct = None

    else:
        seed = random.randint(1, 10_000_000)
        choices = build_choices(question, seed)

    minutes = time_left // 60
    seconds = time_left % 60
    current_index = index + 1
    progress_percent = round(index * 100 / total) if total > 0 else 0

    return render(request, "quiz/exam.html", {
        "finished": False,
        "question": question,
        "choices": choices,
        "selected": selected,
        "is_correct": is_correct,
        "seed": seed,
        "current_index": current_index,
        "total": total,
        "correct": correct_count,
        "incorrect": incorrect_count,
        "minutes": minutes,
        "seconds": seconds,
        "time_left": time_left,
        "progress_percent": progress_percent,
        "review": [],
    })


def tts_view(request):
    """
    Simple TTS endpoint.
    Usage: /tts/?text=Some+text+to+read
    Returns an MP3 audio response.
    """
    text = (request.GET.get("text") or "").strip()
    if not text:
        return HttpResponseBadRequest("Missing 'text' parameter")

    # Create TTS in British English
    tts = gTTS(text=text, lang="en", tld="co.uk")

    # Write to a temporary MP3 file
    tmp = NamedTemporaryFile(delete=False, suffix=".mp3")
    tts.write_to_fp(tmp)
    tmp.flush()
    tmp.seek(0)

    # Serve the file as an audio response
    audio_file = open(tmp.name, "rb")
    response = FileResponse(audio_file, content_type="audio/mpeg")
    response["Content-Disposition"] = 'inline; filename="tts.mp3"'
    return response
