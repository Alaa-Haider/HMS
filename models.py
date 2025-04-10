from extensions import db
from datetime import datetime
from enum import Enum
from sqlalchemy import DECIMAL, Text, Enum as SQLEnum
from werkzeug.security import generate_password_hash, check_password_hash
# Enum Classes
class Gender(Enum):
    Male = 'Male'
    Female = 'Female'

# Update the UserRole enum to match the database enum values
class UserRole(Enum):
    Receptionist = 'Receptionist'
    Nurse = 'Nurse'
    Doctor = 'Doctor'
    Admin = 'Admin'
    Chemist = 'Chemist'
    Radiologist = 'Radiologist'
    Pharmacist = 'Pharmacist'

# Models
class Departments(db.Model):
    __tablename__ = 'Departments'
    DepartmentID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    DepartmentName = db.Column(db.String(100))
    doctors_in_dept = db.relationship('Doctors', back_populates='department')

    def as_dict(self):
        return {
            'DepartmentID': self.DepartmentID,
            'DepartmentName': self.DepartmentName
        }

class Doctors(db.Model):
    __tablename__ = 'Doctors'
    DoctorID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Name = db.Column(db.String(100))
    Age = db.Column(db.Integer)
    ScientificDegree = db.Column(db.String(100))
    Specialist = db.Column(db.String(100))
    DepartmentID = db.Column(db.Integer, db.ForeignKey('Departments.DepartmentID'))
    Phone = db.Column(db.String(20))
    Email = db.Column(db.String(100))
    department = db.relationship('Departments', back_populates='doctors_in_dept')
    appointments = db.relationship('Appointments', back_populates='doctor')
    def as_dict(self):
        return {
            'DoctorID': self.DoctorID,
            'Name': self.Name   ,  
            "Age": self.Age,
            "ScientificDegree": self.ScientificDegree,
            "Specialist": self.Specialist,
            "DepartmentID": self.DepartmentID,
            "Phone": self.Phone,
            "Email": self.Email,
           
        }

class Supplies(db.Model):
    __tablename__ = 'Supplies'
    SupplyID = db.Column(db.Integer, primary_key=True)
    ItemName = db.Column(db.String(100), nullable=False)
    Quantity = db.Column(db.Integer, nullable=False)
    UnitPrice = db.Column(db.Float, nullable=False)
    usage_records = db.relationship('Patient_Supplies', back_populates='supply')

    def as_dict(self):
        return {
            'SupplyID': self.SupplyID,
            'ItemName': self.ItemName,
            'Quantity': self.Quantity,
            'UnitPrice': self.UnitPrice
        }

class Pharmacy(db.Model):
    __tablename__ = 'Pharmacy'
    MedicineID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    MedicineName = db.Column(db.String(100), unique=True)
    UnitPrice = db.Column(db.Float)
    Quantity = db.Column(db.Integer)
    usage_records = db.relationship('Patient_MedicineUsage', back_populates='medicine')

    def as_dict(self):
        return {
            'MedicineID': self.MedicineID,
            'MedicineName': self.MedicineName,
            'UnitPrice': self.UnitPrice,
            'Quantity': self.Quantity
        }

class Laboratory(db.Model):
    __tablename__ = 'Laboratory'
    TestID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    TestName = db.Column(db.String(100))
    Description = db.Column(db.Text)
    Price = db.Column(DECIMAL(10, 2))

    def as_dict(self):
        return {
            'TestID': self.TestID,
            'TestName': self.TestName,
            'Description': self.Description,
            'Price': str(self.Price)
        }

class Radiology(db.Model):
    __tablename__ = 'Radiology'
    RadiologyID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    TestName = db.Column(db.String(100))
    Description = db.Column(db.Text)
    Price = db.Column(DECIMAL(10, 2))

    def as_dict(self):
        return {
            'RadiologyID': self.RadiologyID,
            'TestName': self.TestName,
            'Description': self.Description,
            'Price': str(self.Price)
        }

class Users(db.Model):
    __tablename__ = 'Users'
    UserID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Name = db.Column(db.String(100))
    #Role = db.Column(SQLEnum(*[role.value for role in UserRole], name='role_enum'))
    Role = db.Column(SQLEnum(UserRole, name='role_enum'), nullable=False)
    Phone = db.Column(db.String(20))
    Email = db.Column(db.String(100))
    PasswordHash = db.Column(db.String(255))

    def set_password(self, password):
        self.PasswordHash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.PasswordHash, password)

class Appointments(db.Model):
    __tablename__ = 'Appointments'
    AppointmentID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    PatientID = db.Column(db.Integer, db.ForeignKey('Patients.PatientID'))
    DoctorID = db.Column(db.Integer, db.ForeignKey('Doctors.DoctorID'))
    AppointmentDate = db.Column(db.DateTime)
    QueueNumber = db.Column(db.Integer)
    AvailableSlots = db.Column(db.Integer)
    patient = db.relationship('Patients', back_populates='appointments')
    doctor = db.relationship('Doctors', back_populates='appointments')
    def as_dict(self):
        return {
            'AppointmentID': self.AppointmentID,
            'PatientID': self.PatientID,
            'DoctorID': self.DoctorID,
            'AppointmentDate': self.AppointmentDate.isoformat() if self.AppointmentDate else None,
            'QueueNumber': self.QueueNumber,
            'AvailableSlots': self.AvailableSlots,
            'patient': self.patient.as_dict() if self.patient else None,
            
        }

class Patients(db.Model):
    __tablename__ = 'Patients'
    PatientID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Name = db.Column(db.String(100))
    NationalID = db.Column(db.String(20), unique=True)
    Age = db.Column(db.Integer)
    Gender = db.Column(db.String(10))
    Weight = db.Column(db.Float)
    Height = db.Column(db.Float)
    Address = db.Column(db.String(200))
    Phone = db.Column(db.String(20))
    Email = db.Column(db.String(100))
    MedicalNotes = db.Column(db.Text)
    Report = db.Column(db.Text)
    Diagnose = db.Column(db.String(200))
    DoctorOrders = db.Column(db.Text)
    Date_admission = db.Column(db.DateTime)
    Date_discharge = db.Column(db.DateTime)
    appointments = db.relationship('Appointments', back_populates='patient')
    medicine_usage = db.relationship('Patient_MedicineUsage', back_populates='patient')
    patient_supplies = db.relationship('Patient_Supplies', back_populates='patient')
    patient_laboratory = db.relationship('Patient_Laboratory', back_populates='patient')
    patient_radiology = db.relationship('Patient_Radiology', back_populates='patient')

    def as_dict(self):
        return {
            'PatientID': self.PatientID,
            'Name': self.Name,
            'NationalID': self.NationalID,
            'Age': self.Age,
            'Gender': self.Gender,
            'Weight': self.Weight,
            'Height': self.Height,
            'Address': self.Address,
            'Phone': self.Phone,
            'Email': self.Email,
            'MedicalNotes': self.MedicalNotes,
            'Report': self.Report,
            'Diagnose': self.Diagnose,
            'DoctorOrders': self.DoctorOrders,
            'Date_admission': self.Date_admission.isoformat() if self.Date_admission else None,
            'Date_discharge': self.Date_discharge.isoformat() if self.Date_discharge else None
    }

class Patient_Radiology(db.Model):
    __tablename__ = 'Patient_Radiology'
    PatientID = db.Column(db.Integer, db.ForeignKey('Patients.PatientID'), primary_key=True)
    RadiologyID = db.Column(db.Integer, db.ForeignKey('Radiology.RadiologyID'), primary_key=True)
    patient = db.relationship('Patients', back_populates='patient_radiology')
    radiology_test = db.relationship('Radiology', backref='patient_tests')

class Patient_Laboratory(db.Model):
    __tablename__ = 'Patient_Laboratory'
    PatientID = db.Column(db.Integer, db.ForeignKey('Patients.PatientID'), primary_key=True)
    TestID = db.Column(db.Integer, db.ForeignKey('Laboratory.TestID'), primary_key=True)
    patient = db.relationship('Patients', back_populates='patient_laboratory')
    laboratory_test = db.relationship('Laboratory', backref='patient_tests')

class Patient_MedicineUsage(db.Model):
    __tablename__ = 'Patient_MedicineUsage'
    PatientID = db.Column(db.Integer, db.ForeignKey('Patients.PatientID'), primary_key=True)
    MedicineID = db.Column(db.Integer, db.ForeignKey('Pharmacy.MedicineID'), primary_key=True)
    UsageDate = db.Column(db.DateTime, primary_key=True, default=datetime.utcnow)
    QuantityUsed = db.Column(db.Integer, nullable=False, default=1)
    DoctorID = db.Column(db.Integer, db.ForeignKey('Doctors.DoctorID'))
    Notes = db.Column(db.Text)
    patient = db.relationship('Patients', back_populates='medicine_usage')
    medicine = db.relationship('Pharmacy', back_populates='usage_records')
    doctor = db.relationship('Doctors', backref='medicine_prescriptions')

class Patient_Supplies(db.Model):
    __tablename__ = 'Patient_Supplies'
    PatientID = db.Column(db.Integer, db.ForeignKey('Patients.PatientID'), primary_key=True)
    SupplyID = db.Column(db.Integer, db.ForeignKey('Supplies.SupplyID'), primary_key=True)
    QuantityUsed = db.Column(db.Integer)
    DoctorID = db.Column(db.Integer, db.ForeignKey('Doctors.DoctorID'))
    DateUsed = db.Column(db.DateTime, default=datetime.utcnow)
    patient = db.relationship('Patients', back_populates='patient_supplies')
    supply = db.relationship('Supplies', back_populates='usage_records')
    doctor = db.relationship('Doctors')