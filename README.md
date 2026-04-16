# BloodBridge: Connecting Donors & Recipients

## Project Overview
BloodBridge is a web-based platform designed to connect blood donors with recipients in real-time during medical emergencies. It eliminates delays caused by traditional methods like phone calls or social media posts by providing a centralized, fast, and reliable system.

The goal is simple:  
Help patients find compatible blood donors quickly and efficiently, ultimately saving lives.

---

## Features

- User Authentication (Login & Registration)
- Donor Registration
- Blood Request System
- Smart Donor Matching
- User Dashboard
- Hospital Selection for Requests

---

## Project Architecture

The project follows a three-tier architecture:

### 1. Frontend
- Built using HTML & CSS
- Responsive and user-friendly interface

### 2. Backend
- Developed using Python (Flask)
- Handles business logic, authentication, and donor matching

### 3. Database
- SQLite (lightweight and serverless)
- Ensures data integrity and reliability

---

## Tech Stack

- Frontend: HTML, CSS  
- Backend: Python (Flask)  
- Database: SQLite  
- Library Used: sqlite3  

---

## Concepts Used

- SQL (DDL & DML)
  - PRIMARY KEY, FOREIGN KEY
  - INSERT, UPDATE, DELETE
  - SELECT with LEFT JOIN
- Database Normalization
- Data Integrity Constraints
- Session Management (Authentication)

---

## Workflow

1. User Authentication  
   - Users sign up or log in  

2. Dashboard Access  
   - Choose to become a donor or request blood  

3. Donor & Request Management  
   - Donor form → stored in database  
   - Blood request → processed for matching  

4. Result Generation  
   - System fetches and displays best-matched donors  

---

## Database Schema

### users
- user_id (PK)
- name
- email (Unique)
- password

### hospitals
- hospital_id (PK)
- name
- address

### donors
- donor_id (PK)
- user_id (FK)
- blood_group
- phone_no
- last_donation_date
- is_active

### blood_requests
- request_id (PK)
- user_id (FK)
- hospital_id (FK)
- patient_name
- required_blood_group

---

## Project Deliverables

- Fully functional BloodBridge web app  
- Secure login & registration system  
- Donor registration and management  
- Blood request and matching system  
- User dashboard  
- Dynamic donor search results  

---

## How to Run the Project

```bash
# Clone the repository
git clone https://github.com/your-username/bloodbridge.git

# Navigate to project folder
cd bloodbridge

# Install dependencies
pip install flask

# Run the application
python app.py
