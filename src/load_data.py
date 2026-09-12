import pandas as pd
import mysql.connector

# Load cleaned dataset
df = pd.read_csv("data/telco_customer_churn_cleaned.csv")

# Connect to MySQL
connection = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Devaganga_05",
    database="customer_churn"
)

cursor = connection.cursor()

# Insert customers
customer_query = """
INSERT IGNORE INTO customers
(customer_id, gender, senior_citizen, partner, dependents, tenure)
VALUES (%s, %s, %s, %s, %s, %s)
"""

customer_data = df[
    ['customerID', 'gender', 'SeniorCitizen', 'Partner', 'Dependents', 'tenure']
].values.tolist()

cursor.executemany(customer_query, customer_data)

print("Customers inserted:", cursor.rowcount)
connection.commit()

# Insert services
services_query = """
INSERT IGNORE INTO services
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
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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

cursor.executemany(services_query, services_data)

print("Services inserted:", cursor.rowcount)

connection.commit()

print("CSV loaded:", df.shape)
print("Database connected successfully!")

# -------------------------
# Billing
# -------------------------

billing_query = """
INSERT IGNORE INTO billing
(
    customer_id,
    contract,
    paperless_billing,
    payment_method,
    monthly_charges,
    total_charges
)
VALUES (%s, %s, %s, %s, %s, %s)
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

cursor.executemany(billing_query, billing_data)

print("Billing inserted:", cursor.rowcount)

connection.commit()

# -------------------------
# Churn
# -------------------------

churn_query = """
INSERT IGNORE INTO churn
(
    customer_id,
    churn
)
VALUES (%s, %s)
"""

churn_data = df[
    [
        'customerID',
        'Churn'
    ]
].values.tolist()

cursor.executemany(churn_query, churn_data)

print("Churn inserted:", cursor.rowcount)

connection.commit()