-- Create enum types
CREATE TYPE gender_enum AS ENUM ('Male', 'Female');
CREATE TYPE role_enum AS ENUM ('Receptionist', 'Nurse', 'Doctor', 'Admin', 'Chemist', 'Radiologist', 'Pharmacist');

-- Create Departments table
CREATE TABLE "Departments" (
    "DepartmentID" SERIAL PRIMARY KEY,
    "DepartmentName" VARCHAR(100)
);

-- Create Doctors table
CREATE TABLE "Doctors" (
    "DoctorID" SERIAL PRIMARY KEY,
    "Name" VARCHAR(100),
    "Age" INTEGER,
    "ScientificDegree" VARCHAR(100),
    "Specialist" VARCHAR(100),
    "DepartmentID" INTEGER REFERENCES "Departments"("DepartmentID"),
    "Phone" VARCHAR(20),
    "Email" VARCHAR(100)
);

-- Create Supplies table
CREATE TABLE "Supplies" (
    "SupplyID" INTEGER PRIMARY KEY,
    "ItemName" VARCHAR(100) NOT NULL,
    "Quantity" INTEGER NOT NULL,
    "UnitPrice" FLOAT NOT NULL
);

-- Create Pharmacy table
CREATE TABLE "Pharmacy" (
    "MedicineID" SERIAL PRIMARY KEY,
    "MedicineName" VARCHAR(100) UNIQUE,
    "UnitPrice" FLOAT,
    "Quantity" INTEGER
);

-- Create Laboratory table
CREATE TABLE "Laboratory" (
    "TestID" SERIAL PRIMARY KEY,
    "TestName" VARCHAR(100),
    "Description" TEXT,
    "Price" DECIMAL(10, 2)
);

-- Create Radiology table
CREATE TABLE "Radiology" (
    "RadiologyID" SERIAL PRIMARY KEY,
    "TestName" VARCHAR(100),
    "Description" TEXT,
    "Price" DECIMAL(10, 2)
);

-- Create Users table
CREATE TABLE "Users" (
    "UserID" SERIAL PRIMARY KEY,
    "Name" VARCHAR(100),
    "Role" role_enum NOT NULL,
    "Phone" VARCHAR(20),
    "Email" VARCHAR(100),
    "PasswordHash" VARCHAR(255)
);

-- Create Patients table
CREATE TABLE "Patients" (
    "PatientID" SERIAL PRIMARY KEY,
    "Name" VARCHAR(100),
    "NationalID" VARCHAR(20) UNIQUE,
    "Age" INTEGER,
    "Gender" gender_enum,
    "Address" VARCHAR(255),
    "Phone" VARCHAR(20),
    "Email" VARCHAR(100),
    "Date_admission" TIMESTAMP,
    "Date_discharge" TIMESTAMP,
    "Doctor" INTEGER REFERENCES "Doctors"("DoctorID"),
    "DoctorOrders" TEXT,
    "MedicalHistory" TEXT
);

-- Create Appointments table
CREATE TABLE "Appointments" (
    "AppointmentID" SERIAL PRIMARY KEY,
    "PatientID" INTEGER REFERENCES "Patients"("PatientID"),
    "DoctorID" INTEGER REFERENCES "Doctors"("DoctorID"),
    "AppointmentDate" TIMESTAMP,
    "QueueNumber" INTEGER,
    "AvailableSlots" INTEGER
);

-- Create Patient_MedicineUsage table (many-to-many relationship)
CREATE TABLE "Patient_MedicineUsage" (
    "PatientID" INTEGER REFERENCES "Patients"("PatientID"),
    "MedicineID" INTEGER REFERENCES "Pharmacy"("MedicineID"),
    "Dosage" VARCHAR(100),
    "Frequency" VARCHAR(100),
    "StartDate" TIMESTAMP,
    "EndDate" TIMESTAMP,
    PRIMARY KEY ("PatientID", "MedicineID")
);

-- Create Patient_Supplies table (many-to-many relationship)
CREATE TABLE "Patient_Supplies" (
    "PatientID" INTEGER REFERENCES "Patients"("PatientID"),
    "SupplyID" INTEGER REFERENCES "Supplies"("SupplyID"),
    "Quantity" INTEGER,
    "DateUsed" TIMESTAMP,
    PRIMARY KEY ("PatientID", "SupplyID")
);

-- Create indexes for better performance
CREATE INDEX idx_doctors_department ON "Doctors"("DepartmentID");
CREATE INDEX idx_patients_doctor ON "Patients"("Doctor");
CREATE INDEX idx_appointments_patient ON "Appointments"("PatientID");
CREATE INDEX idx_appointments_doctor ON "Appointments"("DoctorID");
CREATE INDEX idx_patient_medicine_patient ON "Patient_MedicineUsage"("PatientID");
CREATE INDEX idx_patient_medicine_medicine ON "Patient_MedicineUsage"("MedicineID");
CREATE INDEX idx_patient_supplies_patient ON "Patient_Supplies"("PatientID");
CREATE INDEX idx_patient_supplies_supply ON "Patient_Supplies"("SupplyID");