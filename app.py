import streamlit as st
import pandas as pd
from db import init_db, get_session, Staff, SurgeryTarget
from reports import get_staff_progress

# Initialize DB
init_db()

st.set_page_config(page_title="Surgery Dashboard", layout="wide")
st.title("🏥 Surgery Targets Dashboard")

# ------------------------
# Admin: Assign targets
# ------------------------
st.sidebar.header("Admin Panel")

with st.sidebar.form("assign_target_form"):
    staff_name = st.text_input("Staff Name")
    staff_role = st.text_input("Role (e.g. Surgeon, Nurse)")
    month = st.text_input("Month (YYYY-MM)", "2025-09")
    target_count = st.number_input("Target Surgeries", min_value=1, value=5)
    submitted = st.form_submit_button("Assign Target")

    if submitted:
        with get_session() as session:
            # Ensure staff exists
            staff = session.query(Staff).filter(Staff.name == staff_name).first()
            if not staff:
                staff = Staff(name=staff_name, role=staff_role)
                session.add(staff)
                session.commit()
                session.refresh(staff)

            # Assign target
            target = SurgeryTarget(staff_id=staff.id, month=month, target_count=target_count)
            session.add(target)
            session.commit()
            st.success(f"✅ Target of {target_count} surgeries assigned to {staff_name} for {month}")

# ------------------------
# Reports & Progress
# ------------------------
st.header("📊 Staff Surgery Progress")

progress_data = get_staff_progress()
df = pd.DataFrame(progress_data)

if not df.empty:
    st.dataframe(df)

    # Charts
    col1, col2 = st.columns(2)
    with col1:
        st.bar_chart(df.set_index("name")[["achieved"]])
    with col2:
        st.bar_chart(df.set_index("name")[["total_targets"]])
else:
    st.info("No staff or targets assigned yet.")
