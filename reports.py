import pandas as pd
from sqlalchemy import func
from db import get_session, User, Target, Surgery
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import matplotlib.pyplot as plt
import io


def get_trend_data(months: list[str]):
    with get_session() as session:
        results = (
            session.query(
                User.username,
                Target.period,
                Target.case_type,
                Target.target_cases,
                func.count(Surgery.id).label("completed_cases"),
            )
            .join(Target, User.id == Target.staff_id)
            .join(Surgery, Surgery.staff_id == User.id, isouter=True)
            .filter(Target.period.in_(months))
            .group_by(User.username, Target.period, Target.case_type, Target.target_cases)
            .all()
        )

    df = pd.DataFrame(results, columns=["Staff", "Period", "Case Type", "Target Cases", "Completed Cases"])
    df["Progress %"] = (df["Completed Cases"] / df["Target Cases"] * 100).round(1)
    return df


def add_trend_chart_to_pdf(doc_elements, df, staff_name):
    staff_df = df[df["Staff"] == staff_name]
    if staff_df.empty:
        return

    pivot = staff_df.pivot_table(
        index="Period",
        columns="Case Type",
        values="Progress %",
        aggfunc="mean"
    ).fillna(0)

    fig, ax = plt.subplots(figsize=(6, 3))
    pivot.plot(kind="line", marker="o", ax=ax)
    ax.set_title(f"Progress Trend - {staff_name}")
    ax.set_ylabel("Progress %")
    ax.set_ylim(0, 110)
    ax.grid(True)

    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)

    doc_elements.append(Image(buf, width=400, height=200))
    doc_elements.append(Spacer(1, 12))


def generate_monthly_report(period: str, months: list[str], excel_path="surgery_report.xlsx", pdf_path="surgery_report.pdf"):
    df = get_trend_data(months)

    # Excel Export
    df.to_excel(excel_path, index=False)

    # PDF Export
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(pdf_path, pagesize=A4)
    elements = []

    elements.append(Paragraph(f"Surgery Target Report - {period}", styles["Title"]))
    elements.append(Spacer(1, 12))

    period_df = df[df["Period"] == period]
    if not period_df.empty:
        table_data = [period_df.columns.to_list()] + period_df.values.tolist()
        table = Table(table_data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.lightblue),
            ("GRID", (0,0), (-1,-1), 0.5, colors.black),
            ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 24))

    for staff in df["Staff"].unique():
        elements.append(Paragraph(f"Trend Analysis: {staff}", styles["Heading2"]))
        add_trend_chart_to_pdf(elements, df, staff)

    doc.build(elements)

    return excel_path, pdf_path
