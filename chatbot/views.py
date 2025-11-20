import os
import json
import string
import joblib
import pandas as pd

from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

from nltk.corpus import stopwords
from nltk.stem import PorterStemmer

from .models import Profile, ChatHistory


# -----------------------------
#   LOAD FAQ CSV
# -----------------------------
BASE_DIR = os.path.dirname(__file__)
FAQ_PATH = os.path.join(BASE_DIR, "faq.csv")

faq_data = None
if os.path.exists(FAQ_PATH):
    faq_data = pd.read_csv(FAQ_PATH)
else:
    print("FAQ CSV not found:", FAQ_PATH)


# -----------------------------
#   CSV Search Function
# -----------------------------
def find_faq_answer(question):
    if faq_data is None:
        return None

    q = question.lower().strip()

    for _, row in faq_data.iterrows():
        if row["question"].lower().strip() in q:
            return row["answer"]

    return None


# -----------------------------
#   MODEL LOADING
# -----------------------------
MODEL_DIR = os.path.join(BASE_DIR, 'model_files')
MODEL_PATH = os.path.join(MODEL_DIR, 'model.pkl')
VECT_PATH = os.path.join(MODEL_DIR, 'vectorizer.pkl')

model = None
vectorizer = None

try:
    model = joblib.load(MODEL_PATH)
    vectorizer = joblib.load(VECT_PATH)
except Exception as e:
    print("Model load error:", e)


# -----------------------------
#   HOME — ALWAYS REDIRECT TO LOGIN
# -----------------------------
def home(request):
    if not request.user.is_authenticated:
        return redirect("login")
    return redirect("index")


# -----------------------------
#   TEXT PREPROCESSING
# -----------------------------
def preprocess_text(s):
    s = str(s).lower()
    s = s.translate(str.maketrans('', '', string.punctuation))
    tokens = s.split()

    stop = set(stopwords.words("english"))
    tokens = [t for t in tokens if t not in stop]

    ps = PorterStemmer()
    tokens = [ps.stem(t) for t in tokens]

    return " ".join(tokens)


# -----------------------------
#   SIGNUP
# -----------------------------
def signup_page(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        role = request.POST.get("user_type")

        if User.objects.filter(username=username).exists():
            return render(request, "signup.html", {"error": "Username already exists."})

        if User.objects.filter(email=email).exists():
            return render(request, "signup.html", {"error": "Email already registered."})

        user = User.objects.create_user(username=username, email=email, password=password)
        Profile.objects.create(user=user, role=role)

        return redirect("login")

    return render(request, "signup.html")


# -----------------------------
#   LOGIN
# -----------------------------
def login_page(request):
    request.session.flush()

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(username=username, password=password)
        if user:
            login(request, user)
            return redirect("index")

        return render(request, "login.html", {"error": "Invalid username or password"})

    return render(request, "login.html")


# -----------------------------
#   LOGOUT
# -----------------------------
def logout_user(request):
    logout(request)
    return redirect("login")


# -----------------------------
#   CHATBOT MAIN PAGE
# -----------------------------
@login_required(login_url='login')
def index(request):
    return render(request, "index.html")


# -----------------------------
#   CHATBOT API (CSV + ML + SAVE HISTORY)
# -----------------------------
@csrf_exempt
@login_required(login_url='login')
def ask(request):
    if request.method == "POST":

        data = json.loads(request.body.decode("utf-8"))
        question = data.get("question", "")

        if not question.strip():
            return JsonResponse({"answer": "Please ask a valid question."})

        # ----------- 1. Check CSV first -----------
        faq_answer = find_faq_answer(question)
        if faq_answer:
            ChatHistory.objects.create(
                user=request.user,
                question=question,
                answer=faq_answer
            )
            return JsonResponse({"answer": faq_answer})

        # ----------- 2. ML fallback -----------
        if model is None or vectorizer is None:
            return JsonResponse({"answer": "Model not found. Please train the model."})

        try:
            clean_q = preprocess_text(question)
            q_vec = vectorizer.transform([clean_q])
            pred = model.predict(q_vec)
            ml_answer = pred[0]

            # SAVE CHAT
            ChatHistory.objects.create(
                user=request.user,
                question=question,
                answer=ml_answer
            )

            return JsonResponse({"answer": ml_answer})

        except Exception as e:
            return JsonResponse({"answer": "Error: " + str(e)})

    return JsonResponse({"answer": "Only POST allowed"})


# -----------------------------
#   CHAT HISTORY PAGE
# -----------------------------
@login_required(login_url='login')
def history(request):
    chats = ChatHistory.objects.filter(user=request.user).order_by('-timestamp')
    return render(request, "history.html", {"chats": chats})


# -----------------------------
#   DELETE CHAT HISTORY
# -----------------------------
@login_required(login_url='login')
def delete_history(request):
    ChatHistory.objects.filter(user=request.user).delete()
    return redirect("history")
