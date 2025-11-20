import pandas as pd
import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
import pickle
import os

# -------------------------------------
# DOWNLOAD NLTK DATA (Once per device)
# -------------------------------------
nltk.download('punkt')
nltk.download('stopwords')

# -------------------------------------
# CORRECT CSV PATH
# -------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))   # chatbot/
CSV_PATH = os.path.join(BASE_DIR, "faqs.csv")

print("Loading CSV from:", CSV_PATH)

# Load CSV safely + remove header spaces
df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
df.columns = df.columns.str.strip()   # Remove trailing spaces in "answer  "

# -------------------------------------
# TEXT CLEANING FUNCTION
# -------------------------------------
def clean_text(s):
    s = str(s).lower()
    tokens = nltk.word_tokenize(s)
    ps = PorterStemmer()
    cleaned = [ps.stem(word) for word in tokens if word not in stopwords.words('english')]
    return " ".join(cleaned)

# Apply cleaning
df['cleaned_questions'] = df['question'].apply(clean_text)

# -------------------------------------
# TF-IDF VECTORIZER + MODEL TRAINING
# -------------------------------------
vectorizer = TfidfVectorizer()
X = vectorizer.fit_transform(df['cleaned_questions'])
y = df['answer']

model = LogisticRegression()
model.fit(X, y)

# -------------------------------------
# SAVE MODEL FILES
# -------------------------------------
MODEL_DIR = os.path.join(BASE_DIR, "model_files")

if not os.path.exists(MODEL_DIR):
    os.makedirs(MODEL_DIR)

with open(os.path.join(MODEL_DIR, "model.pkl"), "wb") as f:
    pickle.dump(model, f)

with open(os.path.join(MODEL_DIR, "vectorizer.pkl"), "wb") as f:
    pickle.dump(vectorizer, f)

print("\nModel training completed successfully!")
print("Files saved in:", MODEL_DIR)
