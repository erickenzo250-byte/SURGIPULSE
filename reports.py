from db import get_session, Staff, Surgery, SurgeryTarget
from sqlalchemy import func

def get_staff_progress():
    """Return staff, their targets, and progress."""
    with get_session() as session:
        results = []
        staff_list = session.query(Staff).all()

        for staff in staff_list:
            targets = session.query(SurgeryTarget).filter(SurgeryTarget.staff_id == staff.id).all()
            surgeries_done = session.query(func.count(Surgery.id)).filter(Surgery.staff_id == staff.id).scalar()

            results.append({
                "name": staff.name,
                "role": staff.role,
                "total_targets": sum(t.target_count for t in targets),
                "achieved": surgeries_done,
            })

        return results
