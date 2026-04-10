import os
import numpy as np
import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from app.repositories.employee_repository import EmployeeRepository
from app.models.employee import Employee, EmployeeFaceTemplate
from app.ai.face_recognizer import FaceRecognizer
from app.config import settings

logger = logging.getLogger(__name__)


class EmployeeService:
    """
    Coordinates employee management and face template enrollment.
    """

    def __init__(self, db: Session):
        self.db = db
        self.repo = EmployeeRepository(db)
        self.face_rec = FaceRecognizer(settings.FACE_MODEL_DIR)

    def register_employee(self, data: dict) -> Employee:
        # Map front-end 'employee_id' to back-end 'employee_code'
        if not data.get("employee_code") and data.get("employee_id"):
            data["employee_code"] = data.pop("employee_id")
        else:
            data.pop("employee_id", None)  # Remove if both present but we use code

        # Map 'role' to 'designation'
        if "role" in data and data["role"]:
            data["designation"] = data.pop("role")

        # Extract images
        face_base64 = data.pop("face_image_base64", None)
        images_list = data.pop("images", [])
        if face_base64:
            images_list.insert(0, face_base64)

        # Remove other non-model fields
        data.pop("has_face_enrolled", None)

        # Create employee
        employee = self.repo.create(Employee(**data))

        # Process all provided images
        for idx, img_b64 in enumerate(images_list):
            try:
                import base64
                import cv2
                import numpy as np

                if "," in img_b64:
                    img_b64 = img_b64.split(",")[1]

                img_data = base64.b64decode(img_b64)
                nparr = np.frombuffer(img_data, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if img is not None:
                    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    self.enroll_face(employee.id, img_rgb)
            except Exception as e:
                logger.error(f"[EmployeeService] Failed to process image {idx}: {e}")

        return employee

    def enroll_face(
        self, employee_id: int, image_np: np.ndarray
    ) -> Optional[EmployeeFaceTemplate]:
        """Process an image and save a face template for an employee."""
        # 1. Compute embedding
        embedding = self.face_rec.get_embedding(image_np)
        if embedding is None:
            logger.warning(
                f"[EmployeeService] No face detected for employee {employee_id}"
            )
            return None

        # 2. Save image to disk
        filename = f"face_{employee_id}_{int(os.path.getmtime(settings.FACES_DIR))}.jpg"
        img_path = os.path.join(settings.FACES_DIR, filename)

        try:
            # Note: image_np should be converted to BGR for OpenCV
            import cv2

            cv2.imwrite(img_path, cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR))
        except Exception as e:
            logger.error(f"[EmployeeService] Failed to save image: {e}")
            return None

        # 3. Save to database
        return self.repo.add_face_template(
            employee_id, img_path, 1.0
        )  # Quality 1.0 for now

    def list_employees(self) -> List[Employee]:
        return self.repo.get_all()
