from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.employee import Employee, EmployeeFaceTemplate
from app.repositories.base_repository import BaseRepository


class EmployeeRepository(BaseRepository[Employee]):
    def __init__(self, db: Session):
        super().__init__(Employee, db)

    def get_by_code(self, code: str) -> Optional[Employee]:
        return self.db.query(Employee).filter(Employee.employee_code == code).first()

    def add_face_template(
        self, employee_id: int, image_path: str, quality_score: float
    ) -> EmployeeFaceTemplate:
        template = EmployeeFaceTemplate(
            employee_id=employee_id, image_path=image_path, quality_score=quality_score
        )
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        return template

    def get_face_templates(self, employee_id: int) -> List[EmployeeFaceTemplate]:
        return (
            self.db.query(EmployeeFaceTemplate)
            .filter(EmployeeFaceTemplate.employee_id == employee_id)
            .all()
        )
