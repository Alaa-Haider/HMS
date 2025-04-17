from flask import (
    request, jsonify, Blueprint, session, render_template, 
    flash, redirect, url_for
)
from extensions import db
from models import *
from datetime import datetime
import jwt
import os
import json
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
# Session-based Authentication Decorator
def session_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'message': 'Login required!'}), 401
        
        current_user = Users.query.filter_by(UserID=session['user_id']).first()
        if not current_user:
            return jsonify({'message': 'User not found!'}), 401
            
        return f(current_user, *args, **kwargs)
    return decorated

# Blueprints
patients_bp = Blueprint('patients', __name__, url_prefix='/api/patients')
doctors_bp = Blueprint('doctors', __name__, url_prefix='/api/doctors')
departments_bp = Blueprint('departments', __name__, url_prefix='/api/departments')
laboratory_bp = Blueprint('laboratory', __name__, url_prefix='/api/laboratory')
radiology_bp = Blueprint('radiology', __name__, url_prefix='/api/radiology')
supplies_bp = Blueprint('supplies', __name__, url_prefix='/api/supplies')
pharmacy_bp = Blueprint('pharmacy', __name__, url_prefix='/api/pharmacy')
users_bp = Blueprint('users', __name__, url_prefix='/api/users')
appointments_bp = Blueprint('appointments', __name__, url_prefix='/api/appointments')
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# Auth Routes
@auth_bp.route('/login', methods=['POST'])
def login():
    auth = request.json
    if not auth or not auth.get('email') or not auth.get('password'):
        return jsonify({'message': 'Could not verify', 'WWW-Authenticate': 'Basic realm="Login required!"'}), 401
    user = Users.query.filter_by(Email=auth.get('email')).first()
    if not user:
        return jsonify({'message': 'User not found!'}), 404
    if check_password_hash(user.PasswordHash, auth.get('password')):
        # Store user info in session instead of generating token
        session['user_id'] = user.UserID
        session['user_role'] = user.Role.value if hasattr(user.Role, 'value') else user.Role
        session['user_name'] = user.Name
        
        return jsonify({
            'message': 'Login successful',
            'user': {
                'id': user.UserID,
                'name': user.Name,
                'role': user.Role.value if hasattr(user.Role, 'value') else user.Role
            }
        })
    return jsonify({'message': 'Invalid credentials!'}), 401


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.json
    if not data or not data.get('email') or not data.get('password') or not data.get('name') or not data.get('role'):
        return jsonify({'message': 'Missing required fields!'}), 400
    existing_user = Users.query.filter_by(Email=data.get('email')).first()
    if existing_user:
        return jsonify({'message': 'User already exists!'}), 409
    hashed_password = generate_password_hash(data.get('password'))
    
    # Find the matching enum by value instead of trying to create it directly
    role_value = data.get('role')
    role_enum = None
    for role in UserRole:
        if role.value == role_value:
            role_enum = role
            break
    
    if not role_enum:
        return jsonify({'message': f'Invalid role: {role_value}'}), 400
        
    new_user = Users(
        Name=data.get('name'),
        Email=data.get('email'),
        Phone=data.get('phone', ''),
        Role=role_enum,
        PasswordHash=hashed_password
    )
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User created successfully!'}), 201



#  add a patient dashboard route:
@auth_bp.route('/patient-dashboard')
@session_required
def patient_dashboard(current_user):
    if current_user.Role != UserRole.Patient and current_user.Role.value != 'Patient':
        return jsonify({'message': 'Access denied'}), 403
    
    # Get patient data
    patient = Patients.query.filter_by(Email=current_user.Email).first()
    if not patient:
        return jsonify({'message': 'Patient record not found'}), 404
    
    return jsonify({
        'patient': patient.as_dict(),
        'message': 'Patient dashboard data retrieved successfully'
    })    
#______________________________________________________________
# Patients Routes
@patients_bp.route('/', methods=['GET'])
def get_patients():
    patients = Patients.query.all()
    doctors = Doctors.query.all()  # Get all doctors for the dropdown
    
    # Get supplies, medicines, and lab tests for doctor orders
    supplies = Supplies.query.all()
    medicines = Pharmacy.query.all()
    lab_tests = Laboratory.query.all()
    # Add this line to fetch radiology tests
    radiology_tests = Radiology.query.all()
    
    # For API requests, return JSON
    if request.headers.get('Accept') == 'application/json':
        return jsonify([p.as_dict() for p in patients])
    
    # For web requests, render template
    return render_template('patients.html', 
                          patients=patients, 
                          doctors=doctors, 
                          supplies=supplies,
                          medicines=medicines,
                          lab_tests=lab_tests,
                          radiology_tests=radiology_tests)

@patients_bp.route('/<int:patient_id>', methods=['GET'])
def get_patient(patient_id):
    patient = Patients.query.get_or_404(patient_id)
    patient_dict = patient.as_dict()
    
    # If there's a doctor assigned, get the doctor's name
    if patient.Doctor:
        doctor = Doctors.query.get(patient.Doctor)
        if doctor:
            patient_dict['DoctorName'] = doctor.Name
    
    return jsonify(patient_dict)

@patients_bp.route('/create', methods=['POST'])
def create_patient():
    try:
        # Handle form data
        new_patient = Patients(
            Name=request.form.get('Name'),
            NationalID=request.form.get('NationalID'),
            Gender=request.form.get('Gender'),
            Age=request.form.get('Age'),
            Phone=request.form.get('Phone'),
            Email=request.form.get('Email'),
            Address=request.form.get('Address'),
            Height=request.form.get('Height'),
            Weight=request.form.get('Weight'),
            Date_admission=request.form.get('Date_admission'),
            Date_discharge=request.form.get('Date_discharge'),
            Diagnose=request.form.get('Diagnose'),
            MedicalNotes=request.form.get('MedicalNotes'),
            Report=request.form.get('Report'),
            BloodType=request.form.get('BloodType'),
            Doctor=request.form.get('Doctor')
        )
        
        # Handle doctor orders
        selected_supplies = request.form.get('selectedSupplies')
        selected_medicines = request.form.get('selectedMedicines')
        selected_lab_tests = request.form.get('selectedLabTests')
        
        # Combine all doctor orders into a single JSON object
        doctor_orders = {
            'supplies': json.loads(selected_supplies) if selected_supplies else [],
            'medicines': json.loads(selected_medicines) if selected_medicines else [],
            'labTests': json.loads(selected_lab_tests) if selected_lab_tests else [],
            # Add this line to include radiology tests
            'radiologyTests': json.loads(selected_radiology_tests) if selected_radiology_tests else [],
            'dosageInstructions': request.form.get('medicineDosageInstructions', ''),
            'labTestNotes': request.form.get('labtestNotes', ''),
            # Add this line to include radiology notes
            'radiologyNotes': request.form.get('radiologyNotes', '')
        }
        
        new_patient.DoctorOrders = json.dumps(doctor_orders)
        
        db.session.add(new_patient)
        db.session.commit()
        flash('Patient added successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding patient: {str(e)}', 'danger')
    
    return redirect(url_for('patients.get_patients'))

@patients_bp.route('/update/<int:patient_id>', methods=['POST'])
def update_patient(patient_id):
    patient = Patients.query.get_or_404(patient_id)
    try:
        patient.Name = request.form.get('Name')
        patient.NationalID = request.form.get('NationalID')
        patient.Gender = request.form.get('Gender')
        patient.Age = request.form.get('Age')
        patient.Phone = request.form.get('Phone')
        patient.Email = request.form.get('Email')
        patient.Address = request.form.get('Address')
        patient.Height = request.form.get('Height')
        patient.Weight = request.form.get('Weight')
        patient.Date_admission = request.form.get('Date_admission')
        patient.Date_discharge = request.form.get('Date_discharge')
        patient.Diagnose = request.form.get('Diagnose')
        patient.MedicalNotes = request.form.get('MedicalNotes')
        patient.Report = request.form.get('Report')
        patient.BloodType = request.form.get('BloodType')
        patient.Doctor = request.form.get('Doctor')
        
        # Handle doctor orders
        selected_supplies = request.form.get('selectedSupplies')
        selected_medicines = request.form.get('selectedMedicines')
        selected_lab_tests = request.form.get('selectedLabTests')
        # Add this line to get selected radiology tests
        selected_radiology_tests = request.form.get('selectedRadiologyTests')
        
        # Combine all doctor orders into a single JSON object
        doctor_orders = {
            'supplies': json.loads(selected_supplies) if selected_supplies else [],
            'medicines': json.loads(selected_medicines) if selected_medicines else [],
            'labTests': json.loads(selected_lab_tests) if selected_lab_tests else [],
            # Add this line to include radiology tests
            'radiologyTests': json.loads(selected_radiology_tests) if selected_radiology_tests else [],
            'dosageInstructions': request.form.get('medicineDosageInstructions', ''),
            'labTestNotes': request.form.get('labtestNotes', ''),
            # Add this line to include radiology notes
            'radiologyNotes': request.form.get('radiologyNotes', '')
        }
        
        patient.DoctorOrders = json.dumps(doctor_orders)
        
        db.session.commit()
        flash('Patient updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating patient: {str(e)}', 'danger')
    
    return redirect(url_for('patients.get_patients'))

@patients_bp.route('/delete/<int:patient_id>', methods=['POST'])
def delete_patient(patient_id):
    patient = Patients.query.get_or_404(patient_id)
    try:
        db.session.delete(patient)
        db.session.commit()
        flash('Patient deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting patient: {str(e)}', 'danger')
    
    return redirect(url_for('patients.get_patients'))

# Doctors Routes
doctors_bp = Blueprint('doctors', __name__, url_prefix='/api/doctors')

@doctors_bp.route('/', methods=['GET'])
def get_doctors():
    doctors = Doctors.query.all()
    departments = Departments.query.all()
    
    # For API requests, return JSON
    if request.headers.get('Accept') == 'application/json':
        return jsonify([d.as_dict() for d in doctors])
    
    # For web requests, render template
    return render_template('doctor.html', doctors=doctors, departments=departments)

@doctors_bp.route('/<int:doctor_id>', methods=['GET'])
def get_doctor(doctor_id):
    doctor = Doctors.query.get_or_404(doctor_id)
    return jsonify(doctor.as_dict())

@doctors_bp.route('/', methods=['POST'])
def create_doctor():
    # Handle both JSON and form data
    if request.is_json:
        data = request.json
        new_doctor = Doctors(**data)
    else:
        # Handle form data
        new_doctor = Doctors(
            Name=request.form.get('Name'),
            Specialist=request.form.get('Specialization'),  # Changed from Specialization to Specialist
            Phone=request.form.get('Phone'),
            Email=request.form.get('Email'),
            DepartmentID=request.form.get('DepartmentID'),
            Age=request.form.get('Age', None),  # Added with default None
            ScientificDegree=request.form.get('ScientificDegree', '')  # Added with default empty string
        )
    
    db.session.add(new_doctor)
    db.session.commit()
    
    # Return appropriate response based on request type
    if request.is_json:
        return jsonify({'message': 'Doctor created!', 'DoctorID': new_doctor.DoctorID}), 201
    else:
        from flask import flash, redirect, url_for
        flash('Doctor added successfully', 'success')
        return redirect(url_for('doctors.get_doctors'))

@doctors_bp.route('/<int:doctor_id>', methods=['PUT', 'POST'])
def update_doctor(doctor_id):
    doctor = Doctors.query.get_or_404(doctor_id)
    
    if request.is_json:
        data = request.json
        for key, value in data.items():
            setattr(doctor, key, value)
    else:
        # Handle form data
        doctor.Name = request.form.get('Name')
        doctor.Specialist = request.form.get('Specialization')  # Changed from Specialization to Specialist
        doctor.Phone = request.form.get('Phone')
        doctor.Email = request.form.get('Email')
        doctor.DepartmentID = request.form.get('DepartmentID')
        if request.form.get('Age'):
            doctor.Age = request.form.get('Age')
        if request.form.get('ScientificDegree'):
            doctor.ScientificDegree = request.form.get('ScientificDegree')
    
    db.session.commit()
    
    if request.is_json:
        return jsonify({'message': 'Doctor updated!'})
    else:
        from flask import flash, redirect, url_for
        flash('Doctor updated successfully', 'success')
        return redirect(url_for('doctors.get_doctors'))

@doctors_bp.route('/<int:doctor_id>', methods=['DELETE', 'POST'])
def delete_doctor(doctor_id):
    if request.method == 'POST' and not request.is_json:
        # Handle form submission for delete
        doctor = Doctors.query.get_or_404(doctor_id)
        db.session.delete(doctor)
        db.session.commit()
        
        from flask import flash, redirect, url_for
        flash('Doctor deleted successfully', 'success')
        return redirect(url_for('doctors.get_doctors'))
    else:
        # Handle API request
        doctor = Doctors.query.get_or_404(doctor_id)
        db.session.delete(doctor)
        db.session.commit()
        return jsonify({'message': 'Doctor deleted!'})

# Departments Routes
@departments_bp.route('/', methods=['GET'])
def get_departments():
    departments = Departments.query.all()
    # For API requests, return JSON
    if request.headers.get('Accept') == 'application/json':
        return jsonify([dept.as_dict() for dept in departments])
    # For web requests, render template
    return render_template('department.html', departments=departments)

@departments_bp.route('/<int:department_id>', methods=['GET'])
def get_department(department_id):
    department = Departments.query.get_or_404(department_id)
    return jsonify(department.as_dict())

@departments_bp.route('/', methods=['POST'])
def create_department():
    # Handle both JSON and form data
    if request.is_json:
        data = request.json
        new_department = Departments(**data)
    else:
        # Handle form data
        department_name = request.form.get('DepartmentName')
        new_department = Departments(DepartmentName=department_name)
    
    db.session.add(new_department)
    db.session.commit()
    
    # Return appropriate response based on request type
    if request.is_json:
        return jsonify({'message': 'Department created!', 'DepartmentID': new_department.DepartmentID}), 201
    else:
        from flask import flash, redirect, url_for
        flash('Department added successfully', 'success')
        return redirect(url_for('departments.get_departments'))

@departments_bp.route('/<int:department_id>', methods=['PUT', 'POST'])
def update_department(department_id):
    department = Departments.query.get_or_404(department_id)
    
    if request.is_json:
        data = request.json
        for key, value in data.items():
            setattr(department, key, value)
    else:
        # Handle form data
        department_name = request.form.get('DepartmentName')
        department.DepartmentName = department_name
    
    db.session.commit()
    
    if request.is_json:
        return jsonify({'message': 'Department updated!'})
    else:
        from flask import flash, redirect, url_for
        flash('Department updated successfully', 'success')
        return redirect(url_for('departments.get_departments'))

@departments_bp.route('/delete/<int:department_id>', methods=['POST'])
def delete_department(department_id):
    # Handle form submission for delete
    department = Departments.query.get_or_404(department_id)
    try:
        # First update any doctors in this department to have no department
        doctors = Doctors.query.filter_by(DepartmentID=department_id).all()
        for doctor in doctors:
            doctor.DepartmentID = None
        
        # Now delete the department
        db.session.delete(department)
        db.session.commit()
        
        flash('Department deleted successfully', 'success')
        return redirect(url_for('departments.get_departments'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting department: {str(e)}', 'danger')
        return redirect(url_for('departments.get_departments'))
    
        

# Laboratory Routes
@laboratory_bp.route('/', methods=['GET'])
def get_laboratory_tests():
    tests = Laboratory.query.all()
    # For API requests, return JSON
    if request.headers.get('Accept') == 'application/json':
        return jsonify([t.as_dict() for t in tests])
    # For web requests, render template
    return render_template('laboratory.html', lab_tests=tests)

@laboratory_bp.route('/', methods=['POST'])
def create_laboratory_test():
    if request.is_json:
        data = request.json
        try:
            new_test = Laboratory(
                TestName=data.get('TestName'),
                Description=data.get('Description'),
                Price=data.get('Price')
            )
        except Exception as e:
            return jsonify({'message': f'Error creating laboratory test: {str(e)}'}), 400
    else:
        # Handle form data
        try:
            new_test = Laboratory(
                TestName=request.form.get('TestName'),
                Description=request.form.get('Description'),
                Price=request.form.get('Price')
            )
        except Exception as e:
            from flask import flash, redirect, url_for
            flash(f'Error adding laboratory test: {str(e)}', 'danger')
            return redirect(url_for('laboratory.get_laboratory_tests'))
    
    db.session.add(new_test)
    db.session.commit()
    
    if request.is_json:
        return jsonify({'message': 'Laboratory test created successfully', 'TestID': new_test.TestID}), 201
    else:
        from flask import flash, redirect, url_for
        flash('Laboratory test added successfully', 'success')
        return redirect(url_for('laboratory.get_laboratory_tests'))

@laboratory_bp.route('/<int:test_id>', methods=['GET'])
def get_laboratory_test(test_id):
    test = Laboratory.query.get_or_404(test_id)
    return jsonify(test.as_dict())

@laboratory_bp.route('/<int:test_id>', methods=['PUT', 'POST'])
def update_laboratory_test(test_id):
    test = Laboratory.query.get_or_404(test_id)
    
    if request.is_json:
        data = request.json
        try:
            for key, value in data.items():
                setattr(test, key, value)
        except Exception as e:
            db.session.rollback()
            return jsonify({'message': f'Error updating laboratory test: {str(e)}'}), 400
    else:
        # Handle form data
        try:
            test.TestName = request.form.get('TestName')
            test.Description = request.form.get('Description')
            test.Price = request.form.get('Price')
        except Exception as e:
            db.session.rollback()
            from flask import flash, redirect, url_for
            flash(f'Error updating laboratory test: {str(e)}', 'danger')
            return redirect(url_for('laboratory.get_laboratory_tests'))
    
    db.session.commit()
    
    if request.is_json:
        return jsonify({'message': 'Laboratory test updated successfully'}), 200
    else:
        from flask import flash, redirect, url_for
        flash('Laboratory test updated successfully', 'success')
        return redirect(url_for('laboratory.get_laboratory_tests'))

@laboratory_bp.route('/delete/<int:test_id>', methods=['POST'])
def delete_laboratory_test(test_id):
    # Handle form submission for delete
    test = Laboratory.query.get_or_404(test_id)
    try:
        # Delete any related records if needed
        # For example, if there are test results linked to this test
        
        # Now delete the laboratory test
        db.session.delete(test)
        db.session.commit()
        
        flash('Laboratory test deleted successfully', 'success')
        return redirect(url_for('laboratory.get_laboratory_tests'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting laboratory test: {str(e)}', 'danger')
        return redirect(url_for('laboratory.get_laboratory_tests'))
    

# Radiology Routes
@radiology_bp.route('/', methods=['GET'])
def get_radiology_tests():
    rad_tests = Radiology.query.all()
    
    # For API requests, return JSON
    if request.headers.get('Accept') == 'application/json':
        return jsonify([test.as_dict() for test in rad_tests])
    
    # For web requests, render template
    return render_template('radiology.html', rad_tests=rad_tests)


@radiology_bp.route('/<int:test_id>', methods=['GET'])
def get_radiology_test(test_id):
    test = Radiology.query.get_or_404(test_id)
    return jsonify(test.as_dict())

@radiology_bp.route('/create', methods=['POST'])
def create_radiology_test():
    if request.is_json:
        data = request.json
        try:
            # Handle JSON data
            new_test = Radiology(
                TestName=data.get('TestName'),
                Description=data.get('Description'),
                Price=data.get('Price')
            )
        except Exception as e:
            return jsonify({'message': f'Error creating radiology test: {str(e)}'}), 400    
    else:
        try:
            # Handle form data
            new_test = Radiology(
                TestName=request.form.get('TestName'),
                Description=request.form.get('Description'),
                Price=request.form.get('Price')
            ) 
        except Exception as e:
            flash(f'Error adding radiology test: {str(e)}', 'danger')
            return redirect(url_for('radiology.get_radiology_tests')) 

        # Move database operations outside the if/else blocks
        db.session.add(new_test)
        db.session.commit()
        
        if request.is_json:
            return jsonify({'message': 'Radiology test created successfully', 'RadiologyID': new_test.RadiologyID}), 201   
        else:
            flash('Radiology test added successfully', 'success')
            return redirect(url_for('radiology.get_radiology_tests'))
        
        

@radiology_bp.route('/update/<int:test_id>', methods=['POST'])
def update_radiology_test(test_id):
    test = Radiology.query.get_or_404(test_id)
    try:
        test.TestName = request.form.get('TestName')
        test.Description = request.form.get('Description')
        test.Price = request.form.get('Price')
        
        db.session.commit()
        flash('Radiology test updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating radiology test: {str(e)}', 'danger')
    
    return redirect(url_for('radiology.get_radiology_tests'))

@radiology_bp.route('/delete/<int:test_id>', methods=['POST'])
def delete_radiology_test(test_id):
    test = Radiology.query.get_or_404(test_id)
    try:
        db.session.delete(test)
        db.session.commit()
        flash('Radiology test deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting radiology test: {str(e)}', 'danger')
    
    return redirect(url_for('radiology.get_radiology_tests'))


# Supplies Routes
@supplies_bp.route('/', methods=['GET'])
def get_supplies():
    supplies = Supplies.query.all()
    # For API requests, return JSON
    if request.headers.get('Accept') == 'application/json':
        return jsonify([s.as_dict() for s in supplies])
    # For web requests, render template
    return render_template('supplies.html', supplies=supplies)

@supplies_bp.route('/create', methods=['POST'])
def create_supply():
    try:
        # Update field names to match the Supplies model
        new_supply = Supplies(
            ItemName=request.form.get('ItemName'),
            Quantity=request.form.get('Quantity'),
            UnitPrice=request.form.get('UnitPrice')
        )
        db.session.add(new_supply)
        db.session.commit()
        flash('Supply added successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding supply: {str(e)}', 'danger')
    
    return redirect(url_for('supplies.get_supplies'))

@supplies_bp.route('/update/<int:supply_id>', methods=['POST'])
def update_supply(supply_id):
    supply = Supplies.query.get_or_404(supply_id)
    try:
        # Update field names to match the Supplies model
        supply.ItemName = request.form.get('ItemName')
        supply.Quantity = request.form.get('Quantity')
        supply.UnitPrice = request.form.get('UnitPrice')
        
        db.session.commit()
        flash('Supply updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating supply: {str(e)}', 'danger')
    
    return redirect(url_for('supplies.get_supplies'))

@supplies_bp.route('/delete/<int:supply_id>', methods=['POST'])
def delete_supply(supply_id):
    supply = Supplies.query.get_or_404(supply_id)
    try:
        db.session.delete(supply)
        db.session.commit()
        flash('Supply deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting supply: {str(e)}', 'danger')
    
    return redirect(url_for('supplies.get_supplies'))

# Pharmacy Routes
@pharmacy_bp.route('/', methods=['GET'])
def get_pharmacy_items():
    medicines = Pharmacy.query.all()
    return render_template('pharmacy.html', medicines=medicines)

@pharmacy_bp.route('/create', methods=['POST'])
def create_pharmacy_item():
    try:
        # Update field names to match the Pharmacy model
        new_medicine = Pharmacy(
            MedicineName=request.form.get('MedicineName'),
            Quantity=request.form.get('Quantity'),
            UnitPrice=request.form.get('UnitPrice')
        )
        db.session.add(new_medicine)
        db.session.commit()
        flash('Medicine added successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding medicine: {str(e)}', 'danger')
    
    return redirect(url_for('pharmacy.get_pharmacy_items'))

@pharmacy_bp.route('/update/<int:medicine_id>', methods=['POST'])
def update_pharmacy_item(medicine_id):
    medicine = Pharmacy.query.get_or_404(medicine_id)
    try:
        # Update field names to match the Pharmacy model
        medicine.MedicineName = request.form.get('MedicineName')
        medicine.Quantity = request.form.get('Quantity')
        medicine.UnitPrice = request.form.get('UnitPrice')
        
        db.session.commit()
        flash('Medicine updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating medicine: {str(e)}', 'danger')
    
    return redirect(url_for('pharmacy.get_pharmacy_items'))

@pharmacy_bp.route('/delete/<int:medicine_id>', methods=['POST'])
def delete_pharmacy_item(medicine_id):
    medicine = Pharmacy.query.get_or_404(medicine_id)
    try:
        db.session.delete(medicine)
        db.session.commit()
        flash('Medicine deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting medicine: {str(e)}', 'danger')
    
    return redirect(url_for('pharmacy.get_pharmacy_items'))

# Appointments Routes
@appointments_bp.route('/', methods=['GET'])
def get_appointments():
    appointments = Appointments.query.all()
    patients = Patients.query.all()
    doctors = Doctors.query.all()
    
    # For API requests, return JSON
    if request.headers.get('Accept') == 'application/json':
        return jsonify([a.as_dict() for a in appointments])
    
    # For web requests, render template
    return render_template('appointments.html', appointments=appointments, patients=patients, doctors=doctors)

@appointments_bp.route('/<int:appointment_id>', methods=['GET'])
def get_appointment(appointment_id):
    appointment = Appointments.query.get_or_404(appointment_id)
    return jsonify(appointment.as_dict())

@appointments_bp.route('/', methods=['POST'])
def create_appointment():
    # Handle both JSON and form data
    if request.is_json:
        data = request.json
        try:
            new_appointment = Appointments(
                PatientID=data.get('PatientID'),
                DoctorID=data.get('DoctorID'),
                AppointmentDate=datetime.strptime(data.get('AppointmentDate'), '%Y-%m-%d %H:%M'),
                QueueNumber=data.get('QueueNumber'),
                AvailableSlots=data.get('AvailableSlots')
            )
        except Exception as e:
            return jsonify({'message': f'Error creating appointment: {str(e)}'}), 400
    else:
        # Handle form data
        try:
            new_appointment = Appointments(
                PatientID=request.form.get('patient_id'),
                DoctorID=request.form.get('doctor_id'),
                AppointmentDate=datetime.strptime(request.form.get('date'), '%Y-%m-%dT%H:%M'),
                QueueNumber=request.form.get('queue_number'),
                AvailableSlots=request.form.get('available_slots')
            )
        except Exception as e:
            from flask import flash, redirect, url_for
            flash(f'Error adding appointment: {str(e)}', 'danger')
            return redirect(url_for('appointments.get_appointments'))
    
    db.session.add(new_appointment)
    db.session.commit()
    
    # Return appropriate response based on request type
    if request.is_json:
        return jsonify({'message': 'Appointment created!', 'AppointmentID': new_appointment.AppointmentID}), 201
    else:
        from flask import flash, redirect, url_for
        flash('Appointment added successfully', 'success')
        return redirect(url_for('appointments.get_appointments'))

@appointments_bp.route('/<int:appointment_id>', methods=['PUT', 'POST'])
def update_appointment(appointment_id):
    appointment = Appointments.query.get_or_404(appointment_id)
    
    if request.is_json:
        data = request.json
        try:
            for key, value in data.items():
                if key == 'AppointmentDate' and value:
                    setattr(appointment, key, datetime.strptime(value, '%Y-%m-%d %H:%M'))
                else:
                    setattr(appointment, key, value)
        except Exception as e:
            db.session.rollback()
            return jsonify({'message': f'Error updating appointment: {str(e)}'}), 400
    else:
        # Handle form data
        try:
            appointment.PatientID = request.form.get('patient_id')
            appointment.DoctorID = request.form.get('doctor_id')
            appointment.AppointmentDate = datetime.strptime(request.form.get('date'), '%Y-%m-%dT%H:%M')
            appointment.QueueNumber = request.form.get('queue_number')
            appointment.AvailableSlots = request.form.get('available_slots')
        except Exception as e:
            db.session.rollback()
            from flask import flash, redirect, url_for
            flash(f'Error updating appointment: {str(e)}', 'danger')
            return redirect(url_for('appointments.get_appointments'))
    
    db.session.commit()
    
    if request.is_json:
        return jsonify({'message': 'Appointment updated!'})
    else:
        from flask import flash, redirect, url_for
        flash('Appointment updated successfully', 'success')
        return redirect(url_for('appointments.get_appointments'))

@appointments_bp.route('/delete/<int:appointment_id>', methods=[ 'POST'])
def delete_appointment(appointment_id):
    
    appointment = Appointments.query.get_or_404(appointment_id)
       
    try:
        db.session.delete(appointment)
        db.session.commit()
        
        from flask import flash, redirect, url_for
        flash('Appointment deleted successfully', 'success')
        return redirect(url_for('appointments.get_appointments'))
    except Exception as e:
        db.session.rollback()
        from flask import flash, redirect, url_for
        flash(f'Error deleting appointment: {str(e)}', 'danger')
    return redirect(url_for('appointments.get_appointments'))
