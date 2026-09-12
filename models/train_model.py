import os
import joblib
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from src.database import get_connection

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "..", "models")
MODEL_PATH = os.path.join(MODEL_DIR, "churn_model.pkl")

categorical_cols = [
    "gender", "partner", "dependents", "contract",
    "paperless_billing", "payment_method", "internet_service",
    "online_security", "tech_support"
]
numeric_cols = ["senior_citizen", "tenure", "monthly_charges"]


def load_data():
    query = """
        SELECT
            c.gender,
            c.senior_citizen,
            c.partner,
            c.dependents,
            c.tenure,
            b.contract,
            b.paperless_billing,
            b.payment_method,
            b.monthly_charges,
            s.internet_service,
            s.online_security,
            s.tech_support,
            ch.churn
        FROM customers c
        JOIN billing b ON c.customer_id = b.customer_id
        JOIN services s ON c.customer_id = s.customer_id
        JOIN churn ch ON c.customer_id = ch.customer_id
    """

    conn = get_connection()
    try:
        return pd.read_sql(query, conn)
    finally:
        conn.close()


def prepare_features(df):
    df = df.copy()

    if df.empty:
        raise ValueError("No data returned from the database.")

    if "churn" not in df.columns:
        raise ValueError("Column 'churn' not found in the training data.")

    df["target"] = (
        df["churn"]
        .astype(str)
        .str.strip()
        .str.lower()
        .map({"yes": 1, "no": 0})
    )

    df = df.dropna(subset=["target"]).copy()
    if df.empty:
        raise ValueError("No valid churn records were returned from the database.")

    X = df[categorical_cols + numeric_cols]
    y = df["target"].astype(int)

    if y.nunique() < 2:
        raise ValueError("Target column must contain both classes (0 and 1).")

    return X, y


print("Fetching data from MySQL...")
df = load_data()

print("Preparing training data...")
X, y = prepare_features(df)

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

preprocessor = ColumnTransformer(
    transformers=[
        ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_cols),
        ("num", "passthrough", numeric_cols)
    ]
)

model_pipeline = Pipeline(steps=[
    ("preprocessor", preprocessor),
    ("classifier", RandomForestClassifier(n_estimators=200, random_state=42))
])

print("Training Random Forest Classifier...")
model_pipeline.fit(X_train, y_train)

accuracy = model_pipeline.score(X_test, y_test)
print(f"Model validation accuracy: {accuracy:.4f}")

os.makedirs(MODEL_DIR, exist_ok=True)
joblib.dump(model_pipeline, MODEL_PATH)

print(f"Model saved successfully at: {MODEL_PATH}")