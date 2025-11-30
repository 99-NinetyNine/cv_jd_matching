from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib import colors
from core.parsing.schema import Resume
import textwrap

class PDFRenderer:
    def __init__(self):
        pass

    def render(self, resume: Resume, output_path: str):
        c = canvas.Canvas(output_path, pagesize=LETTER)
        width, height = LETTER
        
        y = height - 0.5 * inch
        
        # Name
        if resume.basics and resume.basics.name:
            c.setFont("Helvetica-Bold", 24)
            c.drawString(0.5 * inch, y, resume.basics.name)
            y -= 0.4 * inch
        
        # Contact Info
        c.setFont("Helvetica", 10)
        contact_text = []
        if resume.basics:
            if resume.basics.email: contact_text.append(resume.basics.email)
            if resume.basics.phone: contact_text.append(resume.basics.phone)
            if resume.basics.location and resume.basics.location.city:
                loc = resume.basics.location
                contact_text.append(f"{loc.city}, {loc.region or ''}")
        
        c.drawString(0.5 * inch, y, " | ".join(contact_text))
        y -= 0.5 * inch
        
        # Summary
        if resume.basics and resume.basics.summary:
            c.setFont("Helvetica-Bold", 14)
            c.drawString(0.5 * inch, y, "Summary")
            y -= 0.2 * inch
            c.setFont("Helvetica", 10)
            lines = textwrap.wrap(resume.basics.summary, width=90)
            for line in lines:
                c.drawString(0.5 * inch, y, line)
                y -= 0.15 * inch
            y -= 0.3 * inch

        # Experience
        if resume.work:
            c.setFont("Helvetica-Bold", 14)
            c.drawString(0.5 * inch, y, "Experience")
            y -= 0.2 * inch
            
            for work in resume.work:
                if y < 1 * inch:
                    c.showPage()
                    y = height - 0.5 * inch
                    
                c.setFont("Helvetica-Bold", 12)
                title = f"{work.position} at {work.name}"
                c.drawString(0.5 * inch, y, title)
                
                # Date
                date_str = f"{work.startDate or ''} - {work.endDate or 'Present'}"
                c.setFont("Helvetica-Oblique", 10)
                c.drawRightString(width - 0.5 * inch, y, date_str)
                y -= 0.2 * inch
                
                if work.summary:
                    c.setFont("Helvetica", 10)
                    lines = textwrap.wrap(work.summary, width=90)
                    for line in lines:
                        c.drawString(0.7 * inch, y, line)
                        y -= 0.15 * inch
                
                if work.highlights:
                    for highlight in work.highlights:
                        c.drawString(0.7 * inch, y, f"- {highlight}")
                        y -= 0.15 * inch
                
                y -= 0.2 * inch

        # Education
        if resume.education:
            if y < 1 * inch:
                c.showPage()
                y = height - 0.5 * inch
                
            c.setFont("Helvetica-Bold", 14)
            c.drawString(0.5 * inch, y, "Education")
            y -= 0.2 * inch
            
            for edu in resume.education:
                c.setFont("Helvetica-Bold", 12)
                c.drawString(0.5 * inch, y, f"{edu.institution}")
                c.setFont("Helvetica", 10)
                c.drawRightString(width - 0.5 * inch, y, f"{edu.startDate or ''} - {edu.endDate or ''}")
                y -= 0.15 * inch
                c.drawString(0.5 * inch, y, f"{edu.studyType} in {edu.area}")
                y -= 0.25 * inch

        # Skills
        if resume.skills:
            if y < 1 * inch:
                c.showPage()
                y = height - 0.5 * inch
                
            c.setFont("Helvetica-Bold", 14)
            c.drawString(0.5 * inch, y, "Skills")
            y -= 0.2 * inch
            
            c.setFont("Helvetica", 10)
            for skill in resume.skills:
                skill_text = f"{skill.name}: {', '.join(skill.keywords)}"
                c.drawString(0.5 * inch, y, skill_text)
                y -= 0.15 * inch

        c.save()
