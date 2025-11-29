import os
import json
import string
import pandas as pd

from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

from .models import Profile, ChatHistory

# -----------------------------
#   BASE PATHS
# -----------------------------
BASE_DIR = os.path.dirname(__file__)
FAQ_PATH = os.path.join(BASE_DIR, "faqs.csv")
MODEL_DIR = os.path.join(BASE_DIR, 'model_files')
MODEL_PATH = os.path.join(MODEL_DIR, 'model.pkl')
VECT_PATH = os.path.join(MODEL_DIR, 'vectorizer.pkl')


# -----------------------------
#   LAZY LOAD FAQ CSV
# -----------------------------
faq_data = None
def load_faq():
    global faq_data
    if faq_data is None:
        if os.path.exists(FAQ_PATH):
            faq_data = pd.read_csv(FAQ_PATH)
        else:
            print("FAQ CSV not found:", FAQ_PATH)
    return faq_data


def find_faq_answer(question):
    faq_data_local = load_faq()
    if faq_data_local is None:
        return None
    q = question.lower().strip()
    for _, row in faq_data_local.iterrows():
        if row["question"].lower().strip() in q:
            return row["answer"]
    return None


# -----------------------------
#   LAZY LOAD ML MODEL
# -----------------------------
model = None
vectorizer = None
def load_model():
    global model, vectorizer
    if model is None or vectorizer is None:
        try:
            import joblib
            model = joblib.load(MODEL_PATH)
            vectorizer = joblib.load(VECT_PATH)
        except Exception as e:
            print("Model load error:", e)
            model = None
            vectorizer = None
    return model, vectorizer


# -----------------------------
#   NLTK STOPWORDS (LAZY LOAD)
# -----------------------------
def get_stopwords():
    import nltk
    nltk.download('stopwords', quiet=True)
    from nltk.corpus import stopwords
    return set(stopwords.words("english"))


# -----------------------------
#   TEXT PREPROCESSING
# -----------------------------
from nltk.stem import PorterStemmer
def preprocess_text(s):
    s = str(s).lower()
    s = s.translate(str.maketrans('', '', string.punctuation))
    tokens = s.split()

    stop = get_stopwords()
    tokens = [t for t in tokens if t not in stop]

    ps = PorterStemmer()
    tokens = [ps.stem(t) for t in tokens]

    return " ".join(tokens)


# -----------------------------
#   HOME
# -----------------------------
def home(request):
    if not request.user.is_authenticated:
        return redirect("login")
    return redirect("index")


# -----------------------------
#   SIGNUP
# -----------------------------
def signup_page(request):
    if request.method == "POST":
        try:
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
        except Exception as e:
            print("Signup error:", e)
            return render(request, "signup.html", {"error": "Server error during signup."})

    return render(request, "signup.html")


# -----------------------------
#   LOGIN / LOGOUT
# -----------------------------
def login_page(request):
    request.session.flush()
    if request.method == "POST":
        try:
            username = request.POST.get("username")
            password = request.POST.get("password")
            user = authenticate(username=username, password=password)
            if user:
                login(request, user)
                return redirect("index")
            return render(request, "login.html", {"error": "Invalid username or password"})
        except Exception as e:
            print("Login error:", e)
            return render(request, "login.html", {"error": "Server error during login."})

    return render(request, "login.html")


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
#   CHATBOT API
# -----------------------------
@csrf_exempt
@login_required(login_url='login')
def ask(request):
    if request.method != "POST":
        return JsonResponse({"answer": "Only POST allowed"})

    try:
        data = json.loads(request.body.decode("utf-8"))
        question = data.get("question", "")
        if not question.strip():
            return JsonResponse({"answer": "Please ask a valid question."})

        # 1️⃣ Check CSV first
        faq_answer = find_faq_answer(question)
        if faq_answer:
            ChatHistory.objects.create(user=request.user, question=question, answer=faq_answer)
            return JsonResponse({"answer": faq_answer})

        # 2️⃣ ML fallback
        mdl, vect = load_model()
        if mdl is None or vect is None:
            return JsonResponse({"answer": "Model not found. Please train the model."})

        clean_q = preprocess_text(question)
        q_vec = vect.transform([clean_q])
        pred = mdl.predict(q_vec)
        ml_answer = pred[0]

        # SAVE CHAT
        ChatHistory.objects.create(user=request.user, question=question, answer=ml_answer)
        return JsonResponse({"answer": ml_answer})

    except Exception as e:
        print("Chatbot ask error:", e)
        return JsonResponse({"answer": "Server error while processing the question."})


# -----------------------------
#   CHAT HISTORY PAGE
# -----------------------------
@login_required(login_url='login')
def history(request):
    chats = ChatHistory.objects.filter(user=request.user).order_by('-timestamp')
    return render(request, "history.html", {"chats": chats})


@login_required(login_url='login')
def delete_history(request):
    ChatHistory.objects.filter(user=request.user).delete()
    return redirect("history")
