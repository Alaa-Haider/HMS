from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
# Remove this line:
# from flask_wtf.csrf import CSRFProtect
import os
import json 
from datetime import datetime
from dotenv import load_dotenv
from extensions import db, init_extensions
from models import *
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from models import UserRole
from flask_migrate import Migrate
from config import config

# Initialize Flask ap
def create_app(config_name='default'):
    app = Flask(__name__, 
                static_folder='static',
                template_folder='templates')

# Load configuration
    app.config.from_object(config[config_name])
    
    # Initialize Extensions
    init_extensions(app)
    
    # Initialize Flask-Migrate
    migrate = Migrate(app, db)
    
    return app

app = create_app(os.environ.get('FLASK_ENV', 'default'))

# Role-based access control decorator
def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page', 'danger')
                return redirect(url_for('login'))
            
            if session.get('user_role') not in roles:
                flash('You do not have permission to access this page', 'danger')
                return redirect(url_for('index'))
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Import and Register Blueprints
from routes import (
    patients_bp,
    doctors_bp,
    departments_bp,
    laboratory_bp,
    radiology_bp,
    supplies_bp,
    pharmacy_bp,
    users_bp,
    appointments_bp,
    auth_bp,
)

app.register_blueprint(patients_bp)
app.register_blueprint(doctors_bp)
app.register_blueprint(departments_bp)
app.register_blueprint(laboratory_bp)
app.register_blueprint(radiology_bp)
app.register_blueprint(supplies_bp)
app.register_blueprint(pharmacy_bp)
app.register_blueprint(users_bp)
app.register_blueprint(appointments_bp)
app.register_blueprint(auth_bp)


# Create Tables
with app.app_context():
    db.create_all()

# Routes
# Update the index route to handle the Patient role
@app.route('/')
def index():
    if 'user_id' in session:
        role = session.get('user_role')
        if role == 'Admin':
            return redirect(url_for('admin_dashboard'))
        elif role == 'Doctor':
            return redirect(url_for('doctor_dashboard'))
        elif role == 'Nurse':
            return redirect(url_for('nurse_dashboard'))
        elif role == 'Receptionist':
            return redirect(url_for('receptionist_dashboard'))
        elif role == 'Chemist':
            return redirect(url_for('laboratory_dashboard'))
        elif role == 'Radiologist':
            return redirect(url_for('radiology_dashboard'))
        elif role == 'Pharmacist':
            return redirect(url_for('pharmacy_dashboard'))
        elif role == 'Admin':
            return redirect(url_for('supplies_dashboard'))     
        elif role == 'Patient':
            return redirect(url_for('patient_dashboard'))
    return render_template('index.html')

# Add a patient dashboard route
@app.route('/patient/dashboard')
@role_required('Patient')
def patient_dashboard():
    # Get the current user's patient record
    user_id = session.get('user_id')
    user = Users.query.get(user_id)
    
    # Find the patient record associated with this user
    patient = Patients.query.filter_by(Email=user.Email).first()
    
    if not patient:
        flash('Patient record not found', 'danger')
        return redirect(url_for('index'))
    
    # Get appointments for this patient
    appointments = Appointments.query.filter_by(PatientID=patient.PatientID).all()
    
    # Calculate time remaining for each appointment
    now = datetime.now()
    current_date = now.strftime('%Y-%m-%d %H:%M')
    
    for appointment in appointments:
        if appointment.AppointmentDate and appointment.AppointmentDate > now:
            # Calculate time difference
            time_diff = appointment.AppointmentDate - now
            
            # Format the time difference
            days = time_diff.days
            hours, remainder = divmod(time_diff.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            if days > 0:
                appointment.time_remaining = f"{days} days, {hours} hours"
            elif hours > 0:
                appointment.time_remaining = f"{hours} hours, {minutes} minutes"
            else:
                appointment.time_remaining = f"{minutes} minutes"
                
            # Update status based on time remaining
            if days > 0:
                appointment.Status = "Upcoming"
            elif hours > 0:
                appointment.Status = "Soon"
            else:
                appointment.Status = "Imminent"
        elif appointment.AppointmentDate and appointment.AppointmentDate <= now:
            appointment.time_remaining = "Passed"
            appointment.Status = "Completed"
        else:
            appointment.time_remaining = "Unknown"
    
    # If patient.Report is None, set it to an empty string to avoid template errors
    if patient.Report is None:
        patient.Report = ""
    
    return render_template('patient_dashboard.html', 
                          patient=patient, 
                          appointments=appointments,
                          current_date=current_date)

# Update the login route to handle the Patient role
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = Users.query.filter_by(Email=email).first()
        
        if user and check_password_hash(user.PasswordHash, password):
            # Store user information in session
            session['user_id'] = user.UserID
            
            # Handle the role properly - store as string value if it's an enum
            if hasattr(user.Role, 'value'):
                session['user_role'] = user.Role.value  # For Enum objects
            else:
                session['user_role'] = user.Role  # For string values
                
            session['user_name'] = user.Name
            
            flash('Login successful!', 'success')
            
            # Redirect based on role
            if session['user_role'] == 'Admin':
                return redirect(url_for('admin_dashboard'))
            elif session['user_role'] == 'Doctor':
                return redirect(url_for('doctor_dashboard'))
            elif session['user_role'] == 'Nurse':
                return redirect(url_for('nurse_dashboard'))
            elif session['user_role'] == 'Receptionist':
                return redirect(url_for('receptionist_dashboard'))
            elif session['user_role'] == 'Chemist':
                return redirect(url_for('laboratory_dashboard'))
            elif session['user_role'] == 'Radiologist':
                return redirect(url_for('radiology_dashboard'))
            elif session['user_role'] == 'Pharmacist':
                return redirect(url_for('pharmacy_dashboard'))
            elif session['user_role'] == 'Patient':
                return redirect(url_for('patient_dashboard'))
            else:
                return redirect(url_for('index'))
        else:
            flash('Invalid email or password!', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        role = request.form.get('role')  # Get the role from the form
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Debug print
        print(f"Received role: {role}")

        # Validate input
        if not name or not email or not role or not password:
            flash('All fields are required!', 'danger')
            return render_template('register.html')

        existing_user = Users.query.filter_by(Email=email).first()
        if existing_user:
            flash('Email already registered. Please use a different email.', 'danger')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return render_template('register.html', UserRole=UserRole)

        try:
            # Hash the password for security
            password_hash = generate_password_hash(password)
            
            # Create new user with role directly as string
            # This matches what's in the database enum
            new_user = Users(
                Name=name,
                Email=email,
                Phone=phone,
                Role=role,  # Use the string value directly from the form
                PasswordHash=password_hash
            )
            
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error during registration: {str(e)}', 'danger')
            print(f"Registration error: {str(e)}")  # Debug print

    return render_template('register.html', UserRole=UserRole)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_role', None)
    session.pop('user_name', None)
    flash('You have been logged out!', 'success')
    return redirect(url_for('login'))

# Dashboard routes for different roles
@app.route('/admin/dashboard')
@role_required('Admin')
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/doctor/dashboard')
@role_required('Doctor')
def doctor_dashboard():
    return render_template('doctor_dashboard.html')

@app.route('/nurse/dashboard')
@role_required('Nurse')
def nurse_dashboard():
    return render_template('nurse_dashboard.html')

@app.route('/receptionist/dashboard')
@role_required('Receptionist')
def receptionist_dashboard():
    return render_template('receptionist_dashboard.html')

@app.route('/laboratory/dashboard')
@role_required('Chemist')
def laboratory_dashboard():
    return render_template('laboratory_dashboard.html')

@app.route('/radiology/dashboard')
@role_required('Radiologist')
def radiology_dashboard():
    return render_template('radiology_dashboard.html')

@app.route('/pharmacy/dashboard')
@role_required('Pharmacist')
def pharmacy_dashboard():
    return render_template('pharmacy_dashboard.html')

@app.route('/supplies/dashboard')
@role_required('Admin')
def supplies_dashboard():
    return render_template('supplies_dashboard.html')

# User management routes (Admin only)
@app.route('/users')
@role_required('Admin')
def manage_users():
    users = Users.query.all()
    return render_template('users.html', users=users)

@app.route('/users/delete/<int:id>', methods=['POST'])
@role_required('Admin')
def delete_user(id):
    user = Users.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    flash('User deleted successfully', 'success')
    return redirect(url_for('manage_users'))

# Patient routes
@app.route('/patients')
@role_required('Admin', 'Receptionist', 'Doctor', 'Nurse', 'Chemist', 'Radiologist', 'Pharmacist')
def get_patients():
    patients = Patients.query.all()
    return render_template('patients.html', patients=patients)

@app.route('/patients/<int:id>')
@role_required('Admin', 'Receptionist', 'Doctor', 'Nurse', 'Chemist', 'Radiologist', 'Pharmacist')
def get_patient(id):
    patient = Patients.query.get_or_404(id)
    return render_template('patient_details.html', patient=patient)

@app.route('/patients/add', methods=['GET', 'POST'])
@role_required('Admin', 'Receptionist')
def add_patient():
    if request.method == 'POST':
        # Process form data
        try:
            new_patient = Patients(
                Name=request.form.get('name'),
                DateOfBirth=datetime.strptime(request.form.get('dob'), '%Y-%m-%d'),
                Gender=request.form.get('gender'),
                Address=request.form.get('address'),
                Phone=request.form.get('phone'),
                Email=request.form.get('email')
            )
            db.session.add(new_patient)
            db.session.commit()
            flash('Patient added successfully', 'success')
            return redirect(url_for('get_patients'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding patient: {str(e)}', 'danger')
    
    return render_template('add_patient.html')

@app.route('/patients/edit/<int:id>', methods=['GET', 'POST'])
@role_required('Admin', 'Receptionist', 'Doctor', 'Nurse', 'Chemist', 'Radiologist', 'Pharmacist')
def edit_patient(id):
    patient = Patients.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            patient.Name = request.form.get('name')
            patient.DateOfBirth = datetime.strptime(request.form.get('dob'), '%Y-%m-%d')
            patient.Gender = request.form.get('gender')
            patient.Address = request.form.get('address')
            patient.Phone = request.form.get('phone')
            patient.Email = request.form.get('email')
            
            db.session.commit()
            flash('Patient updated successfully', 'success')
            return redirect(url_for('get_patient', id=patient.PatientID))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating patient: {str(e)}', 'danger')
    
    return render_template('edit_patient.html', patient=patient)

@app.route('/patients/delete/<int:id>', methods=['POST'])
@role_required('Admin', 'Receptionist')
def delete_patient(id):
    patient = Patients.query.get_or_404(id)
    db.session.delete(patient)
    db.session.commit()
    flash('Patient deleted successfully', 'success')
    return redirect(url_for('get_patients'))

# Appointment routes
@app.route('/appointments')
@role_required('Admin', 'Receptionist', 'Doctor')
def get_appointments():
    appointments = Appointments.query.all()
    return render_template('appointments.html', appointments=appointments)

@app.route('/appointments/<int:id>')
@role_required('Admin', 'Receptionist', 'Doctor')
def get_appointment(id):
    appointment = Appointments.query.get_or_404(id)
    return render_template('appointment_details.html', appointment=appointment)

@app.route('/appointments/add', methods=['GET', 'POST'])
@role_required('Admin', 'Receptionist')
def add_appointment():
    if request.method == 'POST':
        try:
            new_appointment = Appointments(
                PatientID=request.form.get('patient_id'),
                DoctorID=request.form.get('doctor_id'),
                AppointmentDate=datetime.strptime(request.form.get('date'), '%Y-%m-%d %H:%M'),
                QueueNumber=request.form.get('queue_number'),
                AvailableSlots=request.form.get('available_slots')
            )
            db.session.add(new_appointment)
            db.session.commit()
            flash('Appointment added successfully', 'success')
            return redirect(url_for('get_appointments'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding appointment: {str(e)}', 'danger')
    
    patients = Patients.query.all()
    doctors = Doctors.query.all()
    return render_template('add_appointment.html', patients=patients, doctors=doctors)

@app.route('/appointments/edit/<int:id>', methods=['GET', 'POST'])
@role_required('Admin', 'Receptionist', 'Doctor')
def edit_appointment(id):
    appointment = Appointments.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            appointment.PatientID = request.form.get('patient_id')
            appointment.DoctorID = request.form.get('doctor_id')
            appointment.AppointmentDate = datetime.strptime(request.form.get('date'), '%Y-%m-%d %H:%M')
            appointment.QueueNumber = request.form.get('queue_number')
            appointment.AvailableSlots = request.form.get('available_slots')
            
            db.session.commit()
            flash('Appointment updated successfully', 'success')
            return redirect(url_for('get_appointment', id=appointment.AppointmentID))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating appointment: {str(e)}', 'danger')
    
    patients = Patients.query.all()
    doctors = Doctors.query.all()
    return render_template('edit_appointment.html', appointment=appointment, patients=patients, doctors=doctors)

@app.route('/appointments/delete/<int:id>', methods=['POST'])
@role_required('Admin', 'Receptionist')
def delete_appointment(id):
    appointment = Appointments.query.get_or_404(id)
    db.session.delete(appointment)
    db.session.commit()
    flash('Appointment deleted successfully', 'success')
    return redirect(url_for('get_appointments'))

# Pharmacy routes
@app.route('/pharmacy')
@role_required('Admin', 'Receptionist', 'Pharmacist')
def get_pharmacy():
    medicines = Pharmacy.query.all()
    return render_template('pharmacy.html', medicines=medicines)

@app.route('/pharmacy/<int:id>')
@role_required('Admin', 'Receptionist', 'Pharmacist')
def get_medicine(id):
    medicine = Pharmacy.query.get_or_404(id)
    return render_template('medicine_details.html', medicine=medicine)

@app.route('/pharmacy/add', methods=['GET', 'POST'])
@role_required('Admin', 'Receptionist', 'Pharmacist')
def add_medicine():
    if request.method == 'POST':
        try:
            new_medicine = Pharmacy(
                Name=request.form.get('name'),
                Description=request.form.get('description'),
                Quantity=request.form.get('quantity'),
                Price=request.form.get('price')
            )
            db.session.add(new_medicine)
            db.session.commit()
            flash('Medicine added successfully', 'success')
            return redirect(url_for('get_pharmacy'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding medicine: {str(e)}', 'danger')
    
    return render_template('add_medicine.html')

@app.route('/pharmacy/edit/<int:id>', methods=['GET', 'POST'])
@role_required('Admin', 'Receptionist', 'Pharmacist')
def edit_medicine(id):
    medicine = Pharmacy.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            medicine.Name = request.form.get('name')
            medicine.Description = request.form.get('description')
            medicine.Quantity = request.form.get('quantity')
            medicine.Price = request.form.get('price')
            
            db.session.commit()
            flash('Medicine updated successfully', 'success')
            return redirect(url_for('get_medicine', id=medicine.MedicineID))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating medicine: {str(e)}', 'danger')
    
    return render_template('edit_medicine.html', medicine=medicine)

@app.route('/pharmacy/delete/<int:id>', methods=['POST'])
@role_required('Admin', 'Receptionist')
def delete_medicine(id):
    medicine = Pharmacy.query.get_or_404(id)
    db.session.delete(medicine)
    db.session.commit()
    flash('Medicine deleted successfully', 'success')
    return redirect(url_for('get_pharmacy'))
# Add route for viewing patients with a specific medicine
@app.route('/pharmacy/medicines/<int:medicine_id>/patients')
@role_required('Admin', 'Doctor', 'Pharmacist')
def view_medicine_patients(medicine_id):
    # Get the medicine details
    medicine = Pharmacy.query.get_or_404(medicine_id)
    
    # Find all patients who have this medicine in their doctor orders
    patients_with_medicine = []
    all_patients = Patients.query.all()
    
    for patient in all_patients:
        if patient.DoctorOrders:
            try:
                orders = json.loads(patient.DoctorOrders)
                if 'medications' in orders and orders['medications']:
                    # Check if this medicine is in the patient's medications
                    for medication in orders['medications']:
                        if str(medication.get('id')) == str(medicine_id):
                            # Get doctor name
                            doctor_name = "N/A"
                            if patient.Doctor:
                                doctor = Doctors.query.get(patient.Doctor)
                                if doctor:
                                    doctor_name = doctor.Name
                            
                            # Get prescription date (using admission date as an approximation)
                            prescription_date = patient.Date_admission
                            if prescription_date:
                                prescription_date = prescription_date.strftime('%Y-%m-%d %H:%M')
                            else:
                                prescription_date = "N/A"
                            
                            # Add patient to the list with additional info
                            patient_info = {
                                'PatientID': patient.PatientID,
                                'Name': patient.Name,
                                'Gender': patient.Gender,
                                'Age': patient.Age,
                                'DoctorName': doctor_name,
                                'PrescriptionDate': prescription_date
                            }
                            patients_with_medicine.append(patient_info)
                            break
            except json.JSONDecodeError:
                # Skip patients with invalid JSON in DoctorOrders
                continue
    
    return render_template('medicine_patients.html', medicine=medicine, patients=patients_with_medicine)    
#_________________________________________________________
# Similar routes for Laboratory, Radiology, and Supplies
# Laboratory routes
@app.route('/laboratory')
@role_required('Admin', 'Receptionist', 'Chemist')
def get_laboratory():
    lab_tests = Laboratory.query.all()
    return render_template('laboratory.html', lab_tests=lab_tests)
@app.route('/laboratory/tests/<int:test_id>/patients')
@role_required('Admin', 'Doctor', 'Chemist')
def view_test_patients(test_id):
    # Get the test details
    test = Laboratory.query.get_or_404(test_id)
    
    # Find all patients who have this test in their doctor orders
    patients_with_test = []
    all_patients = Patients.query.all()
    
    for patient in all_patients:
        if patient.DoctorOrders:
            try:
                orders = json.loads(patient.DoctorOrders)
                if 'labTests' in orders and orders['labTests']:
                    # Check if this test is in the patient's lab tests
                    for lab_test in orders['labTests']:
                        if str(lab_test.get('id')) == str(test_id):
                            # Get doctor name
                            doctor_name = "N/A"
                            if patient.Doctor:
                                doctor = Doctors.query.get(patient.Doctor)
                                if doctor:
                                    doctor_name = doctor.Name
                            
                            # Get test date (using admission date as an approximation)
                            test_date = patient.Date_admission
                            if test_date:
                                test_date = test_date.strftime('%Y-%m-%d %H:%M')
                            else:
                                test_date = "N/A"
                            
                            # Add patient to the list with additional info
                            patient_info = {
                                'PatientID': patient.PatientID,
                                'Name': patient.Name,
                                'Gender': patient.Gender,
                                'Age': patient.Age,
                                'DoctorName': doctor_name,
                                'TestDate': test_date
                            }
                            patients_with_test.append(patient_info)
                            break
            except json.JSONDecodeError:
                # Skip patients with invalid JSON in DoctorOrders
                continue
    
    return render_template('test_patients.html', test=test, patients=patients_with_test)



#___________________________________________________
# Radiology routes
@app.route('/radiology')
@role_required('Admin', 'Receptionist', 'Radiologist')
def get_radiology():
    rad_tests = Radiology.query.all()
    return render_template('radiology.html', rad_tests=rad_tests)

# Add API endpoint for radiology tests
@app.route('/api/radiology/')
def api_get_radiology():
    rad_tests = Radiology.query.all()
    result = []
    for test in rad_tests:
        result.append({
            'TestID': test.TestID,
            'TestName': test.TestName,
            'Description': test.Description,
            'Price': float(test.Price) if test.Price else 0
        })
    return jsonify(result)

# Add route for viewing patients with a specific radiology test
@app.route('/radiology/tests/<int:test_id>/patients')
@role_required('Admin', 'Doctor', 'Radiologist')
def view_radiology_patients(test_id):
    # Get the test details
    test = Radiology.query.get_or_404(test_id)
    
    # Find all patients who have this test in their doctor orders
    patients_with_test = []
    all_patients = Patients.query.all()
    
    for patient in all_patients:
        if patient.DoctorOrders:
            try:
                orders = json.loads(patient.DoctorOrders)
                if 'radiologyTests' in orders and orders['radiologyTests']:
                    # Check if this test is in the patient's radiology tests
                    for rad_test in orders['radiologyTests']:
                        if str(rad_test.get('id')) == str(test_id):
                            # Get doctor name
                            doctor_name = "N/A"
                            if patient.Doctor:
                                doctor = Doctors.query.get(patient.Doctor)
                                if doctor:
                                    doctor_name = doctor.Name
                            
                            # Get test date (using admission date as an approximation)
                            test_date = patient.Date_admission
                            if test_date:
                                test_date = test_date.strftime('%Y-%m-%d %H:%M')
                            else:
                                test_date = "N/A"
                            
                            # Add patient to the list with additional info
                            patient_info = {
                                'PatientID': patient.PatientID,
                                'Name': patient.Name,
                                'Gender': patient.Gender,
                                'Age': patient.Age,
                                'DoctorName': doctor_name,
                                'TestDate': test_date
                            }
                            patients_with_test.append(patient_info)
                            break
            except json.JSONDecodeError:
                # Skip patients with invalid JSON in DoctorOrders
                continue
    
    return render_template('radiology_patients.html', test=test, patients=patients_with_test)    
#____________________________________________________
# Add this API endpoint to get doctor details by ID
@app.route('/api/doctors/<int:doctor_id>')
def get_doctor_by_id(doctor_id):
    doctor = Doctors.query.get_or_404(doctor_id)
    return jsonify(doctor.as_dict())

# Add route for handling radiology test deletion directly
@app.route('/radiology/delete/<int:test_id>', methods=['POST'])
@role_required('Admin', 'Receptionist', 'Radiologist')
def delete_radiology_test(test_id):
    try:
        test = Radiology.query.get_or_404(test_id)
        db.session.delete(test)
        db.session.commit()
        flash('Radiology test deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting radiology test: {str(e)}', 'danger')
    
    return redirect(url_for('radiology.get_radiology_tests'))

@app.route('/supplies')
@role_required('Admin', 'Receptionist')
def get_supplies():
    supplies = Supplies.query.all()
    return render_template('supplies.html', supplies=supplies)

@app.route('/supplies/<int:id>')
@role_required('Admin', 'Receptionist')
def get_supply(id):
    supply = Supplies.query.get_or_404(id)
    return render_template('supply_details.html', supply=supply)

@app.route('/supplies/add', methods=['GET', 'POST'])
@role_required('Admin', 'Receptionist')
def add_supply():
    if request.method == 'POST':
        try:
            new_supply = Supplies(
                ItemName=request.form.get('ItemName'),
                Quantity=request.form.get('Quantity'),
                UnitPrice=request.form.get('UnitPrice')
            )
            db.session.add(new_supply)
            db.session.commit()
            flash('Supply added successfully', 'success')
            return redirect(url_for('get_supplies'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding supply: {str(e)}', 'danger')
    
    return render_template('add_supply.html')

@app.route('/supplies/edit/<int:id>', methods=['GET', 'POST'])
@role_required('Admin', 'Receptionist')
def edit_supply(id):
    supply = Supplies.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            supply.ItemName = request.form.get('ItemName')
            supply.Quantity = request.form.get('Quantity')
            supply.UnitPrice = request.form.get('UnitPrice')
            
            db.session.commit()
            flash('Supply updated successfully', 'success')
            return redirect(url_for('get_supply', id=supply.SupplyID))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating supply: {str(e)}', 'danger')
    
    return render_template('edit_supply.html', supply=supply)

@app.route('/supplies/delete/<int:id>', methods=['POST'])
@role_required('Admin', 'Receptionist')
def delete_supply(id):
    supply = Supplies.query.get_or_404(id)
    db.session.delete(supply)
    db.session.commit()
    flash('Supply deleted successfully', 'success')
    return redirect(url_for('get_supplies'))

# Add route for viewing patients with a specific supply
@app.route('/supplies/<int:supply_id>/patients')
@role_required('Admin', 'Doctor', 'Nurse')
def view_supply_patients(supply_id):
    # Get the supply details
    supply = Supplies.query.get_or_404(supply_id)
    
    # Find all patients who have this supply in their doctor orders
    patients_with_supply = []
    all_patients = Patients.query.all()
    
    for patient in all_patients:
        if patient.DoctorOrders:
            try:
                orders = json.loads(patient.DoctorOrders)
                if 'supplies' in orders and orders['supplies']:
                    # Check if this supply is in the patient's supplies
                    for item in orders['supplies']:
                        if str(item.get('id')) == str(supply_id):
                            # Get doctor name
                            doctor_name = "N/A"
                            if patient.Doctor:
                                doctor = Doctors.query.get(patient.Doctor)
                                if doctor:
                                    doctor_name = doctor.Name
                            
                            # Get order date (using admission date as an approximation)
                            order_date = patient.Date_admission
                            if order_date:
                                order_date = order_date.strftime('%Y-%m-%d %H:%M')
                            else:
                                order_date = "N/A"
                            
                            # Add patient to the list with additional info
                            patient_info = {
                                'PatientID': patient.PatientID,
                                'Name': patient.Name,
                                'Gender': patient.Gender,
                                'Age': patient.Age,
                                'DoctorName': doctor_name,
                                'OrderDate': order_date
                            }
                            patients_with_supply.append(patient_info)
                            break
            except json.JSONDecodeError:
                # Skip patients with invalid JSON in DoctorOrders
                continue
    
    return render_template('supply_patients.html', supply=supply, patients=patients_with_supply)    
#_________________________________________
@app.route('/users/view/<int:id>')
@role_required('Admin')
def view_user(id):
    user = Users.query.get_or_404(id)
    return render_template('view_user.html', user=user)

@app.route('/users/edit/<int:id>', methods=['GET', 'POST'])
@role_required('Admin')
def edit_user(id):
    user = Users.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            user.Name = request.form.get('name')
            user.Email = request.form.get('email')
            user.Phone = request.form.get('phone')
            
            # Only update role if it's changed
            new_role = request.form.get('role')
            if new_role and new_role != user.Role:
                for role in UserRole:
                    if role.value == new_role:
                        user.Role = role
                        break
            
            # Update password if provided
            new_password = request.form.get('password')
            if new_password:
                user.PasswordHash = generate_password_hash(new_password)
            
            db.session.commit()
            flash('User updated successfully', 'success')
            return redirect(url_for('manage_users'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating user: {str(e)}', 'danger')
    
    return render_template('edit_user.html', user=user, UserRole=UserRole)

# API route for departments without token verification
@app.route('/api/departments/')
def api_get_departments():
    departments = Departments.query.all()
    result = []
    for dept in departments:
        result.append({
            'DepartmentID': dept.DepartmentID,
            'DepartmentName': dept.DepartmentName,
            # Add other fields as needed
        })
    return jsonify(result)

# Add this route to redirect to the departments API endpoint
@app.route('/departments')
def departments_page():
    departments = Departments.query.all()
    return render_template('department.html', departments=departments)
# Add these routes for department CRUD operations
@app.route('/departments/create', methods=['POST'])
@role_required('Admin')
def create_department():
    try:
        department_name = request.form.get('DepartmentName')
        if not department_name:
            flash('Department name is required', 'danger')
            return redirect(url_for('get_departments_page'))
            
        new_department = Departments(DepartmentName=department_name)
        db.session.add(new_department)
        db.session.commit()
        flash('Department added successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding department: {str(e)}', 'danger')
    
    return redirect(url_for('get_departments_page'))

@app.route('/departments/update/<int:department_id>', methods=['POST'])
@role_required('Admin')
def update_department(department_id):
    try:
        department = Departments.query.get_or_404(department_id)
        department_name = request.form.get('DepartmentName')
        
        if not department_name:
            flash('Department name is required', 'danger')
            return redirect(url_for('get_departments_page'))
            
        department.DepartmentName = department_name
        db.session.commit()
        flash('Department updated successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating department: {str(e)}', 'danger')
    
    return redirect(url_for('get_departments_page'))

@app.route('/departments/delete/<int:department_id>', methods=['POST'])
@role_required('Admin')
def delete_department(department_id):
    try:
        
        department = Departments.query.get_or_404(department_id)
        db.session.delete(department)
        db.session.commit()
        flash('Department deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting department: {str(e)}', 'danger')
    
    return redirect(url_for('get_departments_page'))

# Add this route to redirect to the doctors API endpoint
@app.route('/doctors')
def doctors_page():
    return redirect(url_for('doctors.get_doctors'))

# Add this route to handle doctor deletion from the web interface
# Update the doctor deletion route to avoid conflicts
@app.route('/doctors/delete_web/<int:doctor_id>', methods=['POST'])
@role_required('Admin')
def delete_doctor_web(doctor_id):
    try:
        doctor = Doctors.query.get_or_404(doctor_id)
        print(f"Deleting doctor: {doctor.Name} (ID: {doctor.DoctorID})")
        
        # Check for related records and delete them first if needed
        # For example, if there are appointments linked to this doctor
        appointments = Appointments.query.filter_by(DoctorID=doctor_id).all()
        for appointment in appointments:
            db.session.delete(appointment)
        
        # Now delete the doctor
        db.session.delete(doctor)
        db.session.commit()
        flash('Doctor deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting doctor: {str(e)}")
        flash(f'Error deleting doctor: {str(e)}', 'danger')
    
    return redirect(url_for('doctors.get_doctors'))
#_____________________________________________________________________
@app.route('/departments/<int:department_id>/doctors')
@role_required('Admin', 'Receptionist')
def view_doctors_by_department(department_id):
    department = Departments.query.get_or_404(department_id)
    doctors = Doctors.query.filter_by(DepartmentID=department_id).all()
    return render_template('doctors_by_department.html', department=department, doctors=doctors)

@app.route('/doctors/view/<int:doctor_id>')
@role_required('Admin', 'Receptionist', 'Doctor')
def view_doctor(doctor_id):
    doctor = Doctors.query.get_or_404(doctor_id)
    appointments = Appointments.query.filter_by(DoctorID=doctor_id).all()
    return render_template('doctor_details.html', doctor=doctor, appointments=appointments)




if __name__ == '__main__':
    app.run(debug=True)
