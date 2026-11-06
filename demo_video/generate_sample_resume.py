from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)


OUTPUT = Path(__file__).parent / "assets" / "sample_resume_fictional.pdf"


def build_sample_resume() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="DemoBanner",
            parent=styles["Normal"],
            alignment=TA_CENTER,
            textColor=colors.HexColor("#9a3412"),
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            spaceAfter=12,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ResumeName",
            parent=styles["Title"],
            alignment=TA_CENTER,
            textColor=colors.HexColor("#0f172a"),
            fontSize=21,
            leading=24,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ResumeSection",
            parent=styles["Heading2"],
            textColor=colors.HexColor("#0f766e"),
            fontSize=12,
            leading=14,
            spaceBefore=12,
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ResumeBody",
            parent=styles["BodyText"],
            fontSize=9.5,
            leading=13,
            spaceAfter=4,
        )
    )

    content = [
        Paragraph("FICTIONAL DEMO RESUME — NO REAL APPLICANT", styles["DemoBanner"]),
        Paragraph("Jordan Example", styles["ResumeName"]),
        Paragraph(
            "Early-career software engineering student",
            ParagraphStyle(
                name="ResumeSubtitle",
                parent=styles["Normal"],
                alignment=TA_CENTER,
                textColor=colors.HexColor("#475569"),
                fontSize=10,
                leading=13,
            ),
        ),
        Spacer(1, 0.08 * inch),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1")),
        Paragraph("PROFILE", styles["ResumeSection"]),
        Paragraph(
            "Software engineering student interested in dependable web applications, "
            "accessible interfaces, and clear technical documentation. This fictional "
            "profile is created only to demonstrate the SkillProofAI workflow.",
            styles["ResumeBody"],
        ),
        Paragraph("EDUCATION", styles["ResumeSection"]),
        Paragraph(
            "<b>Bachelor of Software Engineering</b> — Sample University (fictional)<br/>"
            "Expected graduation: 2026",
            styles["ResumeBody"],
        ),
        Paragraph("SELECTED PROJECTS", styles["ResumeSection"]),
        KeepTogether(
            [
                Paragraph("<b>Evidence Portfolio Tracker</b>", styles["ResumeBody"]),
                Paragraph(
                    "• Developed a React dashboard to organize project evidence and role requirements.<br/>"
                    "• Built a Python FastAPI REST API backed by a SQLite database.<br/>"
                    "• Wrote automated pytest checks for 18 API cases and improved request validation.<br/>"
                    "• Used Git branches and peer review to coordinate project changes.<br/>"
                    "• Participated in weekly Agile planning and recorded technical decisions.<br/>"
                    "• Team planning discussions covered Docker, cloud deployment, release checklists, "
                    "operational monitoring, scaling tradeoffs, platform access, version compatibility, "
                    "and maintenance.",
                    styles["ResumeBody"],
                ),
            ]
        ),
        Spacer(1, 0.07 * inch),
        KeepTogether(
            [
                Paragraph("<b>Accessibility Notes Mini-site</b>", styles["ResumeBody"]),
                Paragraph(
                    "• Created a responsive React interface with keyboard navigation and readable contrast.<br/>"
                    "• Tested form validation and documented follow-up improvements.",
                    styles["ResumeBody"],
                ),
            ]
        ),
        Paragraph("SKILLS USED IN PROJECTS", styles["ResumeSection"]),
        Paragraph(
            "Python, React, FastAPI, REST APIs, SQL, SQLite, Git, pytest, "
            "Agile teamwork, HTML, CSS.",
            styles["ResumeBody"],
        ),
    ]

    document = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title="Fictional SkillProofAI Demo Resume",
        author="Synthetic demo content",
        subject="Safe fictional resume for a SkillProofAI product demonstration",
    )
    document.build(content)
    print(f"Generated fictional demo resume: {OUTPUT}")


if __name__ == "__main__":
    build_sample_resume()
