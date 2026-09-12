import os
import mysql.connector

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CA_CERT_PATH = os.path.join(BASE_DIR, "ca.pem")

def get_connection():
    return mysql.connector.connect(
        host="mysql-2a1f3063-churn-analysis.g.aivencloud.com",
        port=10105,
        user="avnadmin",
        password=os.getenv("AIVEN_PASSWORD"),
        database="defaultdb",
        ssl_ca=CA_CERT_PATH,
        ssl_disabled=False
    )