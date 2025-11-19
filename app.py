import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import date, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret-key' 
DATABASE = 'blood_bank.db' 


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row 
    conn.execute("PRAGMA foreign_keys = ON") 
    return conn

def init_db():
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if not cursor.fetchone():
        print("Creating new database tables from schema.sql...")
        with open('schema.sql', 'r') as f:
            conn.executescript(f.read())
        print("Tables created.")
    conn.close()

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if user and user['password'] == password:
            session['loggedin'] = True
            session['user_id'] = user['user_id']
            session['name'] = user['name']
            return redirect(url_for('home'))
        else:
            error_msg = "Incorrect email or password. Please try again."
            return render_template('login.html', error_message=error_msg)
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        existing_user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        
        if existing_user:
            error_msg = "An account with this email address already exists."
            conn.close()
            return render_template('register.html', error_message=error_msg)
        
        conn.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", (name, email, password))
        conn.commit()
        conn.close()
        
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/home')
def home():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    is_donor = conn.execute("SELECT * FROM donors WHERE user_id = ?", (session['user_id'],)).fetchone()
    
    query = """
        SELECT br.request_id, br.patient_name, br.required_blood_group, br.city, br.state, h.name as hospital_name
        FROM blood_requests br
        LEFT JOIN hospitals h ON br.hospital_id = h.hospital_id
        WHERE br.user_id = ? AND br.status = 'Active'
        ORDER BY br.request_date DESC
    """
    user_requests = conn.execute(query, (session['user_id'],)).fetchall()
    conn.close()
    
    return render_template('home.html', requests=user_requests, is_donor=is_donor)

@app.route('/become_donor', methods=['GET', 'POST'])
def become_donor():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        user_id = session['user_id']
        name = request.form['name']
        age = request.form['age']
        gender = request.form['gender']
        blood_group = request.form['blood_group']
        phone_no = request.form['phone_no']
        address_city = request.form['address_city'] 
        state = request.form['state']           
        last_donation = request.form.get('last_donation_date') or None

        if not (phone_no.isdigit() and len(phone_no) == 10):
            flash('Invalid phone number. Please enter a 10-digit mobile number.', 'error')
            return render_template('become_donor.html')

        conn = get_db_connection()
        existing_donor = conn.execute("SELECT * FROM donors WHERE user_id = ?", (user_id,)).fetchone()
        
        if existing_donor:
            sql = """UPDATE donors SET name = ?, age = ?, gender = ?, blood_group = ?, 
                     phone_no = ?, address = ?, state = ?, last_donation_date = ?, is_active = 1 
                     WHERE user_id = ?"""
            values = (name, age, gender, blood_group, phone_no, address_city, state, last_donation, user_id)
        else:
            sql = """INSERT INTO donors (user_id, name, age, gender, blood_group, phone_no, address, state, last_donation_date) 
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"""
            values = (user_id, name, age, gender, blood_group, phone_no, address_city, state, last_donation)
            
        conn.execute(sql, values)
        conn.commit()
        conn.close()
        
        flash('Donor profile updated successfully!', 'success')
        return redirect(url_for('home'))

    return render_template('become_donor.html')

def find_compatible_donors(blood_group_needed, city, state):
    compatibility = {
        'A+': ['A+', 'A-', 'O+', 'O-'], 'A-': ['A-', 'O-'],
        'B+': ['B+', 'B-', 'O+', 'O-'], 'B-': ['B-', 'O-'],
        'AB+': ['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-'],
        'AB-': ['AB-', 'A-', 'B-', 'O-'],
        'O+': ['O+', 'O-'], 'O-': ['O-']
    }
    compatible_types = compatibility.get(blood_group_needed, [])

    city_matches = []
    state_matches = []
    
    if compatible_types:
        conn = get_db_connection()
        placeholders = ', '.join(['?'] * len(compatible_types))
        ninety_days_ago = date.today() - timedelta(days=90)
        
        query_city_match = f"""
            SELECT d.user_id, d.name, d.age, d.gender, d.phone_no, d.address, d.state, d.blood_group, d.last_donation_date, u.email 
            FROM donors d JOIN users u ON d.user_id = u.user_id 
            WHERE d.blood_group IN ({placeholders}) 
              AND LOWER(d.address) = LOWER(?)
              AND LOWER(d.state) = LOWER(?)
              AND d.is_active = 1
              AND d.user_id != ?
              AND (d.last_donation_date IS NULL OR d.last_donation_date <= ?)
        """
        params_city_match = compatible_types + [city, state, session['user_id'], ninety_days_ago]
        city_matches = conn.execute(query_city_match, params_city_match).fetchall()

        matched_user_ids = [d['user_id'] for d in city_matches]
        matched_user_ids.append(session['user_id']) 
        
        id_placeholders = ', '.join(['?'] * len(matched_user_ids))

        query_state_match = f"""
            SELECT d.user_id, d.name, d.age, d.gender, d.phone_no, d.address, d.state, d.blood_group, d.last_donation_date, u.email 
            FROM donors d JOIN users u ON d.user_id = u.user_id 
            WHERE d.blood_group IN ({placeholders}) 
              AND LOWER(d.state) = LOWER(?)
              AND d.user_id NOT IN ({id_placeholders})
              AND d.is_active = 1
              AND (d.last_donation_date IS NULL OR d.last_donation_date <= ?)
        """
        
        params_state_match = tuple(compatible_types + [state] + matched_user_ids + [ninety_days_ago])
        
        state_matches = conn.execute(query_state_match, params_state_match).fetchall()
        
        conn.close()
        
    return city_matches, state_matches

@app.route('/request_blood', methods=['GET', 'POST'])
def request_blood():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    if request.method == 'POST':
        user_id = session['user_id']
        patient_name = request.form['patient_name']
        hospital_id = request.form['hospital_id']
        blood_group_needed = request.form['blood_group']
        quantity = request.form['quantity']
        city = request.form['city']
        state = request.form['state'] 
        
        if hospital_id == 'other':
            new_hospital_name = request.form['new_hospital_name']
            new_hospital_address = request.form['new_hospital_address']
            new_hospital_city = request.form['new_hospital_city']
            new_hospital_state = request.form['new_hospital_state']
            
            if new_hospital_name:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO hospitals (name, address, city, state) VALUES (?, ?, ?, ?)", 
                               (new_hospital_name, new_hospital_address, new_hospital_city, new_hospital_state))
                hospital_id = cursor.lastrowid
            else:
                hospital_id = None
        
        sql = "INSERT INTO blood_requests (user_id, patient_name, hospital_id, required_blood_group, quantity, city, state) VALUES (?, ?, ?, ?, ?, ?, ?)"
        conn.execute(sql, (user_id, patient_name, hospital_id, blood_group_needed, quantity, city, state))
        conn.commit()
        conn.close()
        
        city_matches, state_matches = find_compatible_donors(blood_group_needed, city, state)
        
        return render_template('search_results.html', 
                               city_matches=city_matches, 
                               state_matches=state_matches, 
                               blood_group_needed=blood_group_needed, 
                               city=city, 
                               state=state)

    hospitals = conn.execute("SELECT * FROM hospitals ORDER BY state, city, name").fetchall()
    conn.close()
    return render_template('request_blood.html', hospitals=hospitals)

@app.route('/recheck_donors/<int:request_id>')
def recheck_donors(request_id):
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    request_details = conn.execute("SELECT required_blood_group, city, state FROM blood_requests WHERE request_id = ? AND user_id = ?", (request_id, session['user_id'])).fetchone()
    conn.close()

    if request_details:
        blood_group_needed = request_details['required_blood_group']
        city = request_details['city']
        state = request_details['state'] 
        
        city_matches, state_matches = find_compatible_donors(blood_group_needed, city, state)
        
        return render_template('search_results.html', 
                               city_matches=city_matches, 
                               state_matches=state_matches, 
                               blood_group_needed=blood_group_needed, 
                               city=city, 
                               state=state)
    
    return redirect(url_for('home'))

@app.route('/delete_request/<int:request_id>')
def delete_request(request_id):
    if 'loggedin' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    conn.execute("DELETE FROM blood_requests WHERE request_id = ? AND user_id = ?", (request_id, session['user_id']))
    conn.commit()
    conn.close()
    
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == "__main__":
    init_db() 
    app.run(debug=True)