
from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
from datetime import date, timedelta 

app = Flask(__name__)
app.config['SECRET_KEY'] = 'a-super-secret-key-that-should-be-changed'
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '12345' 
app.config['MYSQL_DB'] = 'blood_bank_users'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
mysql = MySQL(app)


@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", [email])
        user = cur.fetchone()
        cur.close()

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
        
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", [email])
        if cur.fetchone():
            error_msg = "An account with this email address already exists."
            return render_template('register.html', error_message=error_msg)
        
        cur.execute("INSERT INTO users (name, email, password) VALUES (%s, %s, %s)", (name, email, password))
        mysql.connection.commit()
        cur.close()
        
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/home')
def home():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    
    cur = mysql.connection.cursor()
    
    cur.execute("SELECT * FROM donors WHERE user_id = %s", [session['user_id']])
    is_donor = cur.fetchone()
    
    query = """
        SELECT br.request_id, br.patient_name, br.required_blood_group, h.name as hospital_name
        FROM blood_requests br
        LEFT JOIN hospitals h ON br.hospital_id = h.hospital_id
        WHERE br.user_id = %s AND br.status = 'Active'
        ORDER BY br.request_date DESC
    """
    cur.execute(query, [session['user_id']])
    user_requests = cur.fetchall()
    cur.close()
    
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
        address = request.form['address']
        last_donation = request.form['last_donation_date'] or None

        cur = mysql.connection.cursor()
        sql = "INSERT INTO donors (user_id, name, age, gender, blood_group, phone_no, address, last_donation_date) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        values = (user_id, name, age, gender, blood_group, phone_no, address, last_donation)
        cur.execute(sql, values)
        mysql.connection.commit()
        cur.close()

        return redirect(url_for('home'))

    return render_template('become_donor.html')

def find_compatible_donors(blood_group_needed):
    compatibility = {'A+':['A+','A-','O+','O-'],'A-':['A-','O-'],'B+':['B+','B-','O+','O-'],'B-':['B-','O-'],'AB+':['A+','A-','B+','B-','O+','O-','AB+','AB-'],'AB-':['AB-','A-','B-','O-'],'O+':['O+','O-'],'O-':['O-']}
    compatible_types = compatibility.get(blood_group_needed, [])

    matching_donors = []
    if compatible_types:
        cur = mysql.connection.cursor()
        placeholders = ', '.join(['%s'] * len(compatible_types))
        
        ninety_days_ago = date.today() - timedelta(days=90)
        
        query = f"""
            SELECT d.name, d.age, d.gender, d.phone_no, d.address, d.blood_group, d.last_donation_date, u.email 
            FROM donors d JOIN users u ON d.user_id = u.user_id 
            WHERE d.blood_group IN ({placeholders}) 
              AND d.is_active = TRUE 
              AND d.user_id != %s
              AND (d.last_donation_date IS NULL OR d.last_donation_date <= %s)
        """
        params = compatible_types + [session['user_id'], ninety_days_ago]
        cur.execute(query, params)
        matching_donors = cur.fetchall()
        cur.close()
        
    return matching_donors

@app.route('/request_blood', methods=['GET', 'POST'])
def request_blood():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        user_id = session['user_id']
        patient_name = request.form['patient_name']
        hospital_id = request.form['hospital_id']
        blood_group_needed = request.form['blood_group']
        quantity = request.form['quantity']
        
        cur = mysql.connection.cursor()
        if hospital_id == 'other':
            new_hospital_name = request.form['new_hospital_name']
            new_hospital_address = request.form['new_hospital_address']
            if new_hospital_name:
                cur.execute("INSERT INTO hospitals (name, address) VALUES (%s, %s)", (new_hospital_name, new_hospital_address))
                mysql.connection.commit()
                hospital_id = cur.lastrowid
            else:
                hospital_id = None
        
        sql = "INSERT INTO blood_requests (user_id, patient_name, hospital_id, required_blood_group, quantity) VALUES (%s, %s, %s, %s, %s)"
        cur.execute(sql, (user_id, patient_name, hospital_id, blood_group_needed, quantity))
        mysql.connection.commit()
        cur.close()
        
        donors = find_compatible_donors(blood_group_needed)
        return render_template('search_results.html', donors=donors, blood_group_needed=blood_group_needed)

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM hospitals ORDER BY name")
    hospitals = cur.fetchall()
    cur.close()
    return render_template('request_blood.html', hospitals=hospitals)

@app.route('/recheck_donors/<int:request_id>')
def recheck_donors(request_id):
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT required_blood_group FROM blood_requests WHERE request_id = %s AND user_id = %s", (request_id, session['user_id']))
    request_details = cur.fetchone()
    cur.close()

    if request_details:
        blood_group_needed = request_details['required_blood_group']
        donors = find_compatible_donors(blood_group_needed)
        return render_template('search_results.html', donors=donors, blood_group_needed=blood_group_needed)
    
    return redirect(url_for('home'))

@app.route('/delete_request/<int:request_id>')
def delete_request(request_id):
    if 'loggedin' not in session:
        return redirect(url_for('login'))
        
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM blood_requests WHERE request_id = %s AND user_id = %s", (request_id, session['user_id']))
    mysql.connection.commit()
    cur.close()
    
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)

