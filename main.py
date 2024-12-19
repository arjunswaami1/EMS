import streamlit as st
import psycopg2
from psycopg2 import sql
from datetime import datetime
import re
from dotenv import load_dotenv
import os
import json
import time

load_dotenv()

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT")
}


def load_users():
    with open("users.json", "r") as file:
        data = json.load(file)
        return data["admins"], data["users"]


admins, users = load_users()


def load_departments():
    with open("departments.json", "r") as file:
        data = json.load(file)
        return data["departments"]


departments = load_departments()

if "form_data" not in st.session_state:
    st.session_state["form_data"] = {
        "name": "",
        "employee_id": "",
        "email": "",
        "phone_number": "",
        "department": departments[0],
        "date_of_joining": datetime.today().date(),
        "role": ""
    }

if "is_admin" not in st.session_state:
    st.session_state["is_admin"] = False

if "success_message" not in st.session_state:
    st.session_state["success_message"] = None


def validate_admin_login(username, password):
    for admin in admins:
        if username == admin["username"] and password == admin["password"]:
            return True
    return False


def validate_user_login(username, password):
    for user in users:
        if username == user["username"] and password == user["password"]:
            return True
    return False


def validate_inputs(form_data):
    if len(form_data["phone_number"]) != 10 or not form_data["phone_number"].isdigit():
        return "Phone number must be a 10-digit numeric value."

    email_regex = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
    if not re.match(email_regex, form_data["email"]):
        return "Invalid email format."

    if form_data["date_of_joining"] is None:
        return "Date of Joining cannot be empty."

    if isinstance(form_data["date_of_joining"], str):
        try:
            form_data["date_of_joining"] = datetime.strptime(form_data["date_of_joining"], "%Y-%m-%d").date()
        except ValueError:
            return "Invalid Date of Joining format. Please use YYYY-MM-DD."

    if form_data["date_of_joining"] > datetime.now().date():
        return "Date of Joining cannot be in the future."

    return None


def check_duplicate_employee(employee_details):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        check_query = sql.SQL("""
            SELECT COUNT(*) FROM employees
            WHERE employee_id = %s
        """)
        cur.execute(check_query, (employee_details["employee_id"],))

        count = cur.fetchone()[0]
        cur.close()
        conn.close()

        return count > 0
    except psycopg2.Error:
        return False

        count = cur.fetchone()[0]
        cur.close()
        conn.close()

        return count > 0
    except psycopg2.Error:
        return False


def insert_employee_to_db(employee_details):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        insert_query = sql.SQL("""
            INSERT INTO employees (name, employee_id, email, phone_number, department, date_of_joining, role)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """)
        cur.execute(insert_query, (
            employee_details["name"],
            employee_details["employee_id"],
            employee_details["email"],
            employee_details["phone_number"],
            employee_details["department"],
            employee_details["date_of_joining"],
            employee_details["role"]
        ))
        conn.commit()
        cur.close()
        conn.close()
        return None
    except psycopg2.Error as e:
        return str(e)


def reset_form():
    # Ensure departments is populated
    if departments:
        st.session_state["form_data"] = {
            "name": "",
            "employee_id": "",
            "email": "",
            "phone_number": "",
            "department": departments[0],  # Default to the first department
            "date_of_joining": datetime.today().date(),
            "role": ""
        }
    else:
        st.error("Departments are not loaded. Please check the data source.")


st.title("Employee Management System")

if not st.session_state["is_admin"]:
    st.subheader("Admin Login")

    with st.form("admin_login"):
        admin_username = st.text_input("Username", key="username")
        admin_password = st.text_input("Password", type="password", key="password")
        login_button = st.form_submit_button("Login", help="Login as an Admin")

    if login_button:
        if validate_admin_login(admin_username, admin_password):
            st.session_state["is_admin"] = True
            st.success("Admin Access Granted! Redirecting...")
            time.sleep(2)
            st.rerun()
        elif validate_user_login(admin_username, admin_password):
            st.error("Access Denied. You are not an Admin.")
        else:
            st.error("Invalid credentials. Please try again.")

if st.session_state["is_admin"]:
    st.subheader("Add New Employee")

    with st.form("employee_form"):
        # Form elements where form data is stored in session_state
        st.session_state["form_data"]["name"] = st.text_input("Name (First and Last Name)",
                                                              st.session_state["form_data"]["name"])
        st.session_state["form_data"]["employee_id"] = st.text_input("Employee ID (max 10 characters)",
                                                                     st.session_state["form_data"]["employee_id"])
        st.session_state["form_data"]["email"] = st.text_input("Email", st.session_state["form_data"]["email"])
        st.session_state["form_data"]["phone_number"] = st.text_input("Phone Number (10 digits)",
                                                                      st.session_state["form_data"]["phone_number"])
        st.session_state["form_data"]["department"] = st.selectbox("Department", departments, index=departments.index(
            st.session_state["form_data"]["department"]))
        st.session_state["form_data"]["date_of_joining"] = st.date_input("Date of Joining",
                                                                         value=st.session_state["form_data"][
                                                                             "date_of_joining"])
        st.session_state["form_data"]["role"] = st.text_input("Role (e.g., Manager, Developer)",
                                                              st.session_state["form_data"]["role"])

        submit = st.form_submit_button("Submit", help="Submit employee details")

    reset = st.button("Reset", help="Reset the form")
    if reset:
        reset_form()

    logout = st.button("Logout", help="Logout from admin panel")
    if logout:
        st.session_state["is_admin"] = False
        st.rerun()

    if submit:
        # Check if all fields are filled
        form_data = st.session_state["form_data"]

        if any(value == "" or value is None for value in form_data.values()):
            st.error("All fields must be filled out before submitting the form.")
        else:
            error = validate_inputs(form_data)

            if error:
                st.error(error)
            else:
                if check_duplicate_employee(form_data):
                    st.warning("This employee ID already exists in the system.")
                else:
                    result = insert_employee_to_db(form_data)

                    if result:
                        st.error(f"Error inserting employee data: {result}")
                    else:
                        st.session_state["success_message"] = "Employee added successfully!"
                        reset_form()  # reset after successful insertion
