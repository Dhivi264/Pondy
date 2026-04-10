from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.db import get_db
from app.auth import get_current_user
from app.services.employee_service import EmployeeService
from app.schemas import EmployeeResponse, EmployeeCreate
from app.models.user import User

router = APIRouter(tags=["Employees"])


@router.get("/", response_model=List[EmployeeResponse])
async def list_employees(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    service = EmployeeService(db)
    employees = service.list_employees()
    # Populate has_face_enrolled dynamically
    for emp in employees:
        emp.has_face_enrolled = len(emp.face_templates) > 0
    return employees


@router.post("/", response_model=EmployeeResponse)
async def create_employee(
    employee: EmployeeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Check if admin
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    service = EmployeeService(db)
    return service.register_employee(employee.dict())


@router.post("/{employee_id}/register-face")
async def register_face(
    employee_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    import cv2
    import numpy as np

    # Read image
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    service = EmployeeService(db)
    result = service.enroll_face(employee_id, img_rgb)
    if not result:
        raise HTTPException(status_code=400, detail="Could not process face")
    return {"message": "Face registered successfully"}


@router.delete("/{employee_id}")
async def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    from app.models.employee import Employee
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    db.delete(emp)
    db.commit()
    return {"message": "Employee deleted successfully"}

@router.get("/captured-faces")
async def get_captured_faces(current_user: User = Depends(get_current_user)):
    import os
    from app.config import settings

    if not os.path.exists(settings.CAPTURED_FACES_DIR):
        return []
    files = os.listdir(settings.CAPTURED_FACES_DIR)
    files.sort(
        key=lambda x: os.path.getmtime(os.path.join(settings.CAPTURED_FACES_DIR, x)),
        reverse=True,
    )
    return [{"filename": f, "url": f"/captured_faces/{f}"} for f in files[:20]]
