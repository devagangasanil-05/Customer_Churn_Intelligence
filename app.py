from dotenv import load_dotenv
load_dotenv()
import csv
import io
import os
from pathlib import Path

import joblib
import importlib

pd = importlib.import_module("pandas") if importlib.util.find_spec("pandas") else None

try:
    psycopg2_extras = importlib.import_module("psycopg2.extras")
    RealDictCursor = psycopg2_extras.RealDictCursor
except ImportError:
    RealDictCursor = None

flask = importlib.import_module("flask")
Flask = flask.Flask
Response = flask.Response
render_template = flask.render_template
request = flask.request
from src.database import get_connection

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "models" / "churn_model.pkl"

app = Flask(__name__)


def to_float(value, default=0.0):
    if value is None or value == "":
        return float(default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def to_int(value, default=0):
    if value is None or value == "":
        return int(default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


if MODEL_PATH.exists():
    model_pipeline = joblib.load(MODEL_PATH)
else:
    model_pipeline = None


@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/dashboard")
def dashboard():
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    total_customers = 0
    churned_customers = 0
    churn_rate = 0.0
    avg_monthly_charge = 0.0
    contract_data = []
    payment_data = []
    internet_data = []
    watchlist = []

    try:
        cursor.execute("SELECT COUNT(*) AS total_customers FROM customers")
        row = cursor.fetchone()
        total_customers = to_int(row["total_customers"] if row else 0, 0)

        cursor.execute(
            "SELECT COUNT(*) AS churned_customers FROM churn WHERE churn = 'Yes'"
        )
        row = cursor.fetchone()
        churned_customers = to_int(row["churned_customers"] if row else 0, 0)

        churn_rate = (
            round((churned_customers / total_customers) * 100, 2)
            if total_customers
            else 0.0
        )

        cursor.execute(
            "SELECT AVG(monthly_charges) AS avg_monthly_charge FROM billing"
        )
        row = cursor.fetchone()
        avg_monthly_charge = to_float(
            row["avg_monthly_charge"] if row else 0.0, 0.0
        )

        cursor.execute("""
            SELECT
                b.contract AS contract,
                ROUND((SUM(CASE WHEN ch.churn = 'Yes' THEN 1 ELSE 0 END) * 100.0 / COUNT(*))::numeric, 2) AS churn_rate
            FROM billing b
            JOIN churn ch ON b.customer_id = ch.customer_id
            GROUP BY b.contract
        """)
        contract_data = cursor.fetchall() or []

        cursor.execute("""
            SELECT
                b.payment_method AS payment_method,
                ROUND((SUM(CASE WHEN ch.churn = 'Yes' THEN 1 ELSE 0 END) * 100.0 / COUNT(*))::numeric, 2) AS churn_rate
            FROM billing b
            JOIN churn ch ON b.customer_id = ch.customer_id
            GROUP BY b.payment_method
            ORDER BY churn_rate DESC
        """)
        payment_data = cursor.fetchall() or []

        cursor.execute("""
            SELECT
                s.internet_service AS internet_service,
                ROUND((SUM(CASE WHEN ch.churn = 'Yes' THEN 1 ELSE 0 END) * 100.0 / COUNT(*))::numeric, 2) AS churn_rate
            FROM services s
            JOIN churn ch ON s.customer_id = ch.customer_id
            GROUP BY s.internet_service
            ORDER BY churn_rate DESC
        """)
        internet_data = cursor.fetchall() or []

        # High-Risk Watchlist: Active, Month-to-month, High monthly charges
        cursor.execute("""
            SELECT 
                c.customer_id,
                c.gender,
                c.senior_citizen,
                c.partner,
                c.dependents,
                c.tenure,
                b.contract,
                b.monthly_charges,
                b.paperless_billing,
                b.payment_method,
                s.internet_service,
                s.online_security,
                s.tech_support
            FROM customers c
            JOIN billing b ON c.customer_id = b.customer_id
            JOIN services s ON c.customer_id = s.customer_id
            JOIN churn ch ON c.customer_id = ch.customer_id
            WHERE ch.churn = 'No' AND b.contract = 'Month-to-month'
            ORDER BY b.monthly_charges DESC, c.tenure ASC
            LIMIT 5
        """)
        watchlist = cursor.fetchall() or []

    finally:
        cursor.close()
        conn.close()

    kpis = {
        "total_customers": total_customers,
        "churned_customers": churned_customers,
        "churn_rate": churn_rate,
        "avg_monthly_charge": round(avg_monthly_charge, 2),
    }

    return render_template(
        "dashboard.html",
        kpis=kpis,
        contract_data=contract_data,
        payment_data=payment_data,
        internet_data=internet_data,
        watchlist=watchlist,
    )


@app.route("/customers")
def customers():
    search_query = request.args.get("search", "").strip()
    contract_filter = request.args.get("contract", "").strip()
    churn_filter = request.args.get("churn", "").strip()

    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    customer_records = []

    try:
        base_query = """
            SELECT 
                c.customer_id,
                c.gender,
                c.senior_citizen,
                c.partner,
                c.dependents,
                c.tenure,
                b.contract,
                b.monthly_charges,
                b.paperless_billing,
                b.payment_method,
                s.internet_service,
                s.online_security,
                s.tech_support,
                ch.churn
            FROM customers c
            JOIN billing b ON c.customer_id = b.customer_id
            JOIN services s ON c.customer_id = s.customer_id
            JOIN churn ch ON c.customer_id = ch.customer_id
            WHERE 1=1
        """
        params = []

        if search_query:
            base_query += " AND c.customer_id LIKE %s"
            params.append(f"%{search_query}%")

        if contract_filter:
            base_query += " AND b.contract = %s"
            params.append(contract_filter)

        if churn_filter:
            base_query += " AND ch.churn = %s"
            params.append(churn_filter)

        base_query += " ORDER BY c.tenure DESC LIMIT 100"

        if params:
            cursor.execute(base_query, tuple(params))
        else:
            cursor.execute(base_query)

        customer_records = cursor.fetchall() or []

    finally:
        cursor.close()
        conn.close()

    return render_template(
        "customers.html",
        customers=customer_records,
        search_query=search_query,
        contract_filter=contract_filter,
        churn_filter=churn_filter,
    )


@app.route("/customers/export")
def export_customers():
    search_query = request.args.get("search", "").strip()
    contract_filter = request.args.get("contract", "").strip()
    churn_filter = request.args.get("churn", "").strip()

    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        base_query = """
            SELECT 
                c.customer_id,
                c.gender,
                c.senior_citizen,
                c.partner,
                c.dependents,
                c.tenure,
                b.contract,
                b.monthly_charges,
                b.payment_method,
                s.internet_service,
                ch.churn
            FROM customers c
            JOIN billing b ON c.customer_id = b.customer_id
            JOIN services s ON c.customer_id = s.customer_id
            JOIN churn ch ON c.customer_id = ch.customer_id
            WHERE 1=1
        """
        params = []

        if search_query:
            base_query += " AND c.customer_id LIKE %s"
            params.append(f"%{search_query}%")
        if contract_filter:
            base_query += " AND b.contract = %s"
            params.append(contract_filter)
        if churn_filter:
            base_query += " AND ch.churn = %s"
            params.append(churn_filter)

        base_query += " ORDER BY c.tenure DESC LIMIT 500"

        cursor.execute(base_query, tuple(params) if params else None)
        records = cursor.fetchall() or []

    finally:
        cursor.close()
        conn.close()

    output = io.StringIO()
    writer = csv.writer(output)

    # CSV Header
    writer.writerow([
        "Customer ID",
        "Gender",
        "Senior Citizen",
        "Partner",
        "Dependents",
        "Tenure (Months)",
        "Contract",
        "Monthly Charges",
        "Payment Method",
        "Internet Service",
        "Churn Status",
    ])

    for row in records:
        writer.writerow([
            row["customer_id"],
            row["gender"],
            "Yes" if row["senior_citizen"] == 1 else "No",
            row["partner"],
            row["dependents"],
            row["tenure"],
            row["contract"],
            row["monthly_charges"],
            row["payment_method"],
            row["internet_service"],
            row["churn"],
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=churniq_export.csv"},
    )


@app.route("/risk", methods=["GET", "POST"])
def risk():
    prediction_result = None

    is_eval_request = request.method == "POST" or (
        request.method == "GET" and request.args.get("customer_id")
    )

    # Provide safe default values for GET requests so the template has values to bind to
    default_form = {
        "gender": "Female",
        "senior_citizen": 0,
        "partner": "No",
        "dependents": "No",
        "tenure": 1,
        "contract": "Month-to-month",
        "paperless_billing": "Yes",
        "payment_method": "Electronic check",
        "monthly_charges": 50.0,
        "internet_service": "Fiber optic",
        "online_security": "No",
        "tech_support": "No",
    }

    if is_eval_request:
        if model_pipeline is None:
            prediction_result = {
                "error": "Model file not found. Please verify models/churn_model.pkl exists.",
                "inputs": {},
            }
            return render_template("risk.html", result=prediction_result, form_data=default_form)

        source = request.form if request.method == "POST" else request.args

        form_data = {
            "gender": source.get("gender", "Female"),
            "senior_citizen": int(source.get("senior_citizen", 0)),
            "partner": source.get("partner", "No"),
            "dependents": source.get("dependents", "No"),
            "tenure": int(source.get("tenure", 1)),
            "contract": source.get("contract", "Month-to-month"),
            "paperless_billing": source.get("paperless_billing", "Yes"),
            "payment_method": source.get("payment_method", "Electronic check"),
            "monthly_charges": float(source.get("monthly_charges", 50.0)),
            "internet_service": source.get("internet_service", "Fiber optic"),
            "online_security": source.get("online_security", "No"),
            "tech_support": source.get("tech_support", "No"),
        }

        input_df = pd.DataFrame([form_data])

        try:
            churn_probability = model_pipeline.predict_proba(input_df)[0][1]
            risk_percentage = round(float(churn_probability) * 100, 1)
        except Exception:
            prediction_result = {
                "error": "Model input mismatch. Verify feature types and names.",
                "inputs": form_data,
            }
            return render_template("risk.html", result=prediction_result, form_data=form_data)

        # Risk Factors Detection
        drivers = []
        if form_data["contract"] == "Month-to-month":
            drivers.append("Month-to-month Contract (High Flexibility)")
        if form_data["tenure"] <= 6:
            drivers.append("Tenure < 6 Months (Early Onboarding Friction)")
        if form_data["payment_method"] == "Electronic check":
            drivers.append("Electronic Check (High Historical Attrition)")
        if (
            form_data["internet_service"] == "Fiber optic"
            and form_data["tech_support"] == "No"
        ):
            drivers.append("Fiber Optic without Dedicated Tech Support")
        if form_data["monthly_charges"] >= 75.0:
            drivers.append("Premium Tier Billing (Sensitivity to Price)")

        if not drivers:
            drivers.append("Favorable long-term commitment indicators")

        if risk_percentage >= 65:
            risk_tier = "High"
            badge_class = "danger"
            recommendation = "Immediate intervention needed. Offer a 1-year contract discount and assign a success manager."
        elif risk_percentage >= 35:
            risk_tier = "Medium"
            badge_class = "warning"
            recommendation = "Moderate risk. Offer security/tech support bundles and review payment behavior."
        else:
            risk_tier = "Low"
            badge_class = "safe"
            recommendation = "Account is healthy. Good candidate for loyalty or upgrade promotions."

        prediction_result = {
            "customer_id": source.get("customer_id"),
            "probability": risk_percentage,
            "tier": risk_tier,
            "badge_class": badge_class,
            "drivers": drivers[:3],
            "recommendation": recommendation,
            "inputs": form_data,
        }

        return render_template("risk.html", result=prediction_result, form_data=form_data)

    # Initial GET request: pass default form data dictionary
    return render_template("risk.html", result=None, form_data=default_form)

    

@app.route("/insights")
def insights():
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    fiber_risk = {"churn_rate": 0.0, "monthly_revenue_risk": 0.0}
    financial_impact = {"high_value_churned": 0, "lost_mrr": 0.0}
    tenure_cohorts = []

    try:
        cursor.execute("""
            SELECT 
                ROUND((SUM(CASE WHEN ch.churn = 'Yes' THEN 1 ELSE 0 END) * 100.0 / COUNT(*))::numeric, 2) AS churn_rate,
                ROUND(SUM(b.monthly_charges)::numeric, 2) AS monthly_revenue_risk
            FROM billing b
            JOIN services s ON b.customer_id = s.customer_id
            JOIN churn ch ON b.customer_id = ch.customer_id
            WHERE b.contract = 'Month-to-month' AND s.internet_service = 'Fiber optic'
        """)
        row = cursor.fetchone()
        if row:
            fiber_risk = {
                "churn_rate": to_float(row.get("churn_rate"), 0.0),
                "monthly_revenue_risk": to_float(
                    row.get("monthly_revenue_risk"), 0.0
                ),
            }

        cursor.execute("""
            SELECT 
                COUNT(*) AS high_value_churned,
                ROUND(SUM(b.monthly_charges)::numeric, 2) AS lost_mrr
            FROM billing b
            JOIN churn ch ON b.customer_id = ch.customer_id
            WHERE ch.churn = 'Yes' AND b.monthly_charges >= 80.0
        """)
        row = cursor.fetchone()
        if row:
            financial_impact = {
                "high_value_churned": to_int(row.get("high_value_churned"), 0),
                "lost_mrr": to_float(row.get("lost_mrr"), 0.0),
            }

        cursor.execute("""
            SELECT 
                CASE 
                    WHEN c.tenure <= 6 THEN '0–6 Months'
                    WHEN c.tenure <= 12 THEN '7–12 Months'
                    WHEN c.tenure <= 24 THEN '13–24 Months'
                    ELSE '25+ Months'
                END AS tenure_bracket,
                COUNT(*) AS total_count,
                ROUND((SUM(CASE WHEN ch.churn = 'Yes' THEN 1 ELSE 0 END) * 100.0 / COUNT(*))::numeric, 2) AS churn_rate
            FROM customers c
            JOIN churn ch ON c.customer_id = ch.customer_id
            GROUP BY tenure_bracket
            ORDER BY churn_rate DESC
        """)
        tenure_cohorts = cursor.fetchall() or []

    finally:
        cursor.close()
        conn.close()

    return render_template(
        "insights.html",
        fiber_risk=fiber_risk,
        financial_impact=financial_impact,
        tenure_cohorts=tenure_cohorts,
    )


if __name__ == "__main__":
    app.run(debug=True)