"""
==================================================
.ACCDB DATABASE SETUP INSTRUCTIONS
==================================================

1. Create a new Microsoft Access database file named "database.accdb" inside the /backend directory.
2. Important: You MUST have the "Microsoft Access Database Engine 2016 Redistributable" installed
   (either 32-bit or 64-bit depending on your Python installation architecture).

TABLE SUMMARIES:

Table: Employees
Columns:
- ID (AutoNumber, Primary Key)
- EmployeeID (Short Text)
- Name (Short Text)
- Department (Short Text)
- Role (Short Text)
- HasFaceEnrolled (Yes/No)
- IsActive (Yes/No)

Table: Cameras
- ID (AutoNumber, Primary Key)
- CameraID (Short Text)
- Name (Short Text)
- Status (Short Text)
- FeedUrl (Short Text)

Table: AttendanceRecords
- ID (AutoNumber, Primary Key)
- EmployeeID (Short Text)
- RecordDate (Date/Time)
- CheckInTime (Date/Time)
- CheckOutTime (Date/Time)
- Status (Short Text)

Table: ArchiveRecords
- ID (AutoNumber, Primary Key)
- ArchiveID (Short Text)
- CameraID (Short Text)
- RecordType (Short Text)
- Duration (Short Text)
- FileSize (Short Text)
- FilePath (Short Text)
- StartTime (Date/Time)

Table: Admins
- ID (AutoNumber, Primary Key)
- Username (Short Text)
- PasswordHash (Short Text)
- Role (Short Text)
"""
