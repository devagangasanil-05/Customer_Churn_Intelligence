import pandas as pd  # type: ignore[import-not-found]
from psycopg2.extras import execute_values  # type: ignore[import-not-found]
from src.database import get_connection

# Load cleaned dataset
df = pd.read_csv("data/telco_customer_churn_cleaned.csv")

# Connect to PostgreSQL
connection = get_connection()
cursor = connection.cursor()

# Insert customers
customer_query = """
INSERT INTO customers
(customer_id, gender, senior_citizen, partner, dependents, tenure)
VALUES %s
ON CONFLICT (customer_id) DO NOTHING
"""

customer_data = df[
    ['customerID', 'gender', 'SeniorCitizen', 'Partner', 'Dependents', 'tenure']
].values.tolist()

execute_values(cursor, customer_query, customer_data, page_size=500)
print("Customers inserted:", cursor.rowcount)
connection.commit()

# Insert services
services_query = """
INSERT INTO services
(
    customer_id,
    phone_service,
    multiple_lines,
    internet_service,
    online_security,
    online_backup,
    device_protection,
    tech_support,
    streaming_tv,
    streaming_movies
)
VALUES %s
ON CONFLICT (customer_id) DO NOTHING
"""

services_data = df[
    [
        'customerID',
        'PhoneService',
        'MultipleLines',
        'InternetService',
        'OnlineSecurity',
        'OnlineBackup',
        'DeviceProtection',
        'TechSupport',
        'StreamingTV',
        'StreamingMovies'
    ]
].values.tolist()

execute_values(cursor, services_query, services_data, page_size=500)
print("Services inserted:", cursor.rowcount)
connection.commit()

print("CSV loaded:", df.shape)
print("Database connected successfully!")

# -------------------------
# Billing
# -------------------------

billing_query = """
INSERT INTO billing
(
    customer_id,
    contract,
    paperless_billing,
    payment_method,
    monthly_charges,
    total_charges
)
VALUES %s
ON CONFLICT (customer_id) DO NOTHING
"""

billing_data = df[
    [
        'customerID',
        'Contract',
        'PaperlessBilling',
        'PaymentMethod',
        'MonthlyCharges',
        'TotalCharges'
    ]
].values.tolist()

execute_values(cursor, billing_query, billing_data, page_size=500)
print("Billing inserted:", cursor.rowcount)
connection.commit()

# -------------------------
# Churn
# -------------------------

churn_query = """
INSERT INTO churn
(
    customer_id,
    churn
)
VALUES %s
ON CONFLICT (customer_id) DO NOTHING
"""

churn_data = df[
    [
        'customerID',
        'Churn'
    ]
].values.tolist()

execute_values(cursor, churn_query, churn_data, page_size=500)
print("Churn inserted:", cursor.rowcount)
connection.commit()

cursor.close()
connection.close()