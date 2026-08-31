#!/usr/bin/env python3
"""Generate the PLODA portal PDF documents."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase.acroform import AcroForm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "documents"
OUT.mkdir(parents=True, exist_ok=True)

GREEN_950 = colors.HexColor("#082F28")
GREEN_900 = colors.HexColor("#0D493D")
GREEN_700 = colors.HexColor("#227565")
GOLD_700 = colors.HexColor("#A97925")
GOLD_500 = colors.HexColor("#D0AA5D")
GOLD_300 = colors.HexColor("#EAD7A6")
CREAM = colors.HexColor("#FBF7ED")
CREAM_2 = colors.HexColor("#F4EDDD")
INK = colors.HexColor("#15221E")
MUTED = colors.HexColor("#69766F")
LINE = colors.HexColor("#D9DED8")
WHITE = colors.white


def draw_seal(c: canvas.Canvas, x: float, y: float, radius: float = 12 * mm, inverse: bool = False) -> None:
    c.saveState()
    c.setFillColor(WHITE if inverse else GREEN_900)
    c.setStrokeColor(GOLD_300 if inverse else GOLD_500)
    c.setLineWidth(0.8)
    c.circle(x, y, radius, fill=1, stroke=1)
    c.setStrokeColor(GOLD_300 if inverse else colors.Color(1, 1, 1, alpha=0.5))
    c.circle(x, y, radius - 2.2 * mm, fill=0, stroke=1)
    c.setFillColor(GREEN_950 if inverse else GOLD_300)
    c.setFont("Times-Bold", 13)
    c.drawCentredString(x, y - 4, "PL")
    c.setFillColor(GOLD_500)
    c.circle(x, y + radius - 3.2 * mm, 0.8 * mm, fill=1, stroke=0)
    c.circle(x, y - radius + 3.2 * mm, 0.8 * mm, fill=1, stroke=0)
    c.restoreState()


def constitution_page(c: canvas.Canvas, doc: BaseDocTemplate) -> None:
    width, height = A4
    c.saveState()
    c.setFillColor(CREAM)
    c.rect(0, 0, width, height, fill=1, stroke=0)
    c.setFillColor(GREEN_950)
    c.rect(0, height - 21 * mm, width, 21 * mm, fill=1, stroke=0)
    draw_seal(c, 19 * mm, height - 10.5 * mm, 7 * mm)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 8.4)
    c.drawString(31 * mm, height - 9.5 * mm, "PLODA")
    c.setFillColor(colors.HexColor("#BFCFC8"))
    c.setFont("Helvetica", 5.9)
    c.drawString(31 * mm, height - 13 * mm, "PEOPLE'S LAND OWNERSHIP & DEVELOPMENT ASSOCIATION")
    c.setStrokeColor(GOLD_500)
    c.line(19 * mm, 15 * mm, width - 19 * mm, 15 * mm)
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 6.5)
    c.drawString(19 * mm, 10.5 * mm, "PLODA Constitution - Portal Reference Edition")
    c.drawRightString(width - 19 * mm, 10.5 * mm, f"Page {doc.page}")
    c.restoreState()


def build_constitution() -> Path:
    output = OUT / "PLODA_Constitution_Portal_Reference.pdf"
    doc = BaseDocTemplate(
        str(output),
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=30 * mm,
        bottomMargin=23 * mm,
        title="PLODA Constitution - Portal Reference Edition",
        author="People's Land Ownership and Development Association",
        subject="Member portal reference edition",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates([PageTemplate(id="constitution", frames=[frame], onPage=constitution_page)])

    styles = getSampleStyleSheet()
    cover_title = ParagraphStyle("CoverTitle", fontName="Times-Roman", fontSize=34, leading=36, textColor=GREEN_950, alignment=TA_CENTER, spaceAfter=12)
    cover_sub = ParagraphStyle("CoverSub", fontName="Helvetica", fontSize=8.5, leading=13, textColor=MUTED, alignment=TA_CENTER)
    cover_label = ParagraphStyle("CoverLabel", fontName="Helvetica-Bold", fontSize=7.4, leading=10, textColor=GOLD_700, alignment=TA_CENTER, spaceAfter=10)
    h1 = ParagraphStyle("H1", fontName="Times-Roman", fontSize=25, leading=27, textColor=GREEN_950, spaceBefore=5, spaceAfter=13)
    h2 = ParagraphStyle("H2", fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=GREEN_900, spaceBefore=16, spaceAfter=6)
    body = ParagraphStyle("Body", fontName="Helvetica", fontSize=8.7, leading=14.2, textColor=INK, spaceAfter=8)
    body_muted = ParagraphStyle("BodyMuted", parent=body, textColor=MUTED)
    clause = ParagraphStyle("Clause", parent=body, leftIndent=8 * mm, firstLineIndent=-8 * mm, spaceAfter=6)
    callout = ParagraphStyle("Callout", fontName="Helvetica", fontSize=8, leading=12.5, textColor=colors.HexColor("#604C27"))
    quote = ParagraphStyle("Quote", fontName="Times-Italic", fontSize=14, leading=20, textColor=GREEN_700, alignment=TA_CENTER, leftIndent=15 * mm, rightIndent=15 * mm)

    story = []
    story.extend([
        Spacer(1, 24 * mm),
        KeepTogether([
            Paragraph("PORTAL REFERENCE EDITION", cover_label),
            Paragraph("PLODA<br/>Constitution", cover_title),
            Paragraph("People's Land Ownership and Development Association", cover_sub),
        ]),
        Spacer(1, 13 * mm),
        Table([["LAND", "DEVELOPMENT", "PROSPERITY"]], colWidths=[doc.width / 3] * 3, style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), GREEN_950),
            ("TEXTCOLOR", (0, 0), (-1, -1), GOLD_300),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 11),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 11),
            ("LINEBEFORE", (1, 0), (-1, -1), .5, colors.HexColor("#4D766C")),
        ])),
        Spacer(1, 14 * mm),
        Paragraph("A people-centred framework for inclusive land ownership, productive communities and sustainable national development.", quote),
        Spacer(1, 18 * mm),
        Table([[Paragraph("IMPORTANT STATUS NOTICE", ParagraphStyle("NoticeHead", fontName="Helvetica-Bold", fontSize=7, textColor=GOLD_700)), Paragraph("This document is a professionally formatted portal reference based on the current PLODA mandate and recorded amendments. It is not represented as the signed legal master constitution. The signed master constitution should replace this file before formal legal reliance or public launch.", callout)]], colWidths=[40 * mm, doc.width - 40 * mm], style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F2E7CB")),
            ("BOX", (0, 0), (-1, -1), .6, GOLD_500),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 11),
            ("RIGHTPADDING", (0, 0), (-1, -1), 11),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ])),
        Spacer(1, 13 * mm),
        Paragraph("Office: 23 Richwell Avenue, Meyrick Park, Mabelreign, Harare, Zimbabwe<br/>Email: info@ploda.org", cover_sub),
        PageBreak(),
    ])

    sections = [
        ("Foreword", [
            "PLODA is founded on the conviction that access to land, when matched with responsible development, can unlock dignity, food security, enterprise, job creation and generational prosperity.",
            "The Association supports the national aspiration for inclusive growth and recognises the development leadership of His Excellency, President Emmerson Dambudzo Mnangagwa. Its programmes seek to complement Zimbabwe's development direction through productive settlements, empowerment, social protection and balanced regional development.",
            "This constitutional reference presents PLODA as a disciplined, transparent and people-centred institution whose work must always be conducted lawfully, accountably and in the long-term interests of members and communities.",
        ]),
        ("Section 1 - Name, nature and legal identity", [
            "1.1 The organisation shall be known as the People's Land Ownership and Development Association, abbreviated as PLODA.",
            "1.2 PLODA is a voluntary, non-partisan and development-oriented membership association established to promote lawful land ownership, responsible development and member empowerment.",
            "1.3 The Association shall conduct its affairs in accordance with applicable Zimbabwean law, its approved policies and the signed master constitution.",
            "1.4 The principal office shall be situated at 23 Richwell Avenue, Meyrick Park, Mabelreign, Harare, Zimbabwe, or at another address lawfully approved by the Association.",
        ]),
        ("Section 2 - Vision, mission and values", [
            "2.1 Vision: Inclusive and prosperous communities where land ownership creates dignity, stability and enduring economic opportunity.",
            "2.2 Mission: To facilitate responsible pathways to land access, promote productive use and coordinate development programmes that strengthen households and communities.",
            "2.3 Core values: integrity, equity, accountability, transparency, empowerment, sustainability, service, unity and respect for the law.",
            "2.4 PLODA shall promote participation without unlawful discrimination and shall uphold the dignity and legitimate interests of its members.",
        ]),
        ("Section 3 - Objectives and functions", [
            "3.1 Facilitate structured and transparent member pathways for lawful access to land and development opportunities.",
            "3.2 Promote agro-residential settlement models that combine dignified living with productive agriculture, livestock and household resilience.",
            "3.3 Support food security, enterprise, job creation, skills development and the economic empowerment of members and communities.",
            "3.4 Develop partnerships with public institutions, private-sector organisations, development agencies and communities where these partnerships advance PLODA's lawful objectives.",
            "3.5 Promote social protection, environmental responsibility and balanced regional development across Zimbabwe.",
        ]),
        ("Section 4 - Membership", [
            "4.1 Membership shall be open to persons who meet the approved eligibility criteria, support the objectives of PLODA and complete the prescribed registration and verification process.",
            "4.2 Every applicant shall provide complete and accurate personal, identification and contact information, and shall consent to lawful verification.",
            "4.3 A non-refundable joining fee of US$200 shall apply, subject to the approved official membership form and payment rules. Payment shall be made only through verified PLODA channels.",
            "4.4 Members shall protect their portal credentials, maintain current information, preserve official payment evidence and comply with PLODA policies and lawful decisions.",
            "4.5 Membership may be suspended or terminated for fraud, deliberate misrepresentation, misuse of funds or resources, serious misconduct, unlawful activity, or material breach of the signed master constitution, subject to fair procedure.",
        ]),
        ("Section 5 - Governance and leadership", [
            "5.1 PLODA shall maintain a governance structure that clearly separates strategic leadership, oversight, administration and operational responsibilities.",
            "5.2 Founder: Archibold Tapiwa Chigwende.",
            "5.3 Patron: ........................................................",
            "5.4 The offices of Founder and Patron are distinct and shall not be treated as interchangeable roles.",
            "5.5 Executive office-bearers shall meet the approved suitability, integrity and police-vetting requirements. Valid police clearance may be required as a condition of appointment.",
            "5.6 Committees and office-bearers shall keep proper records, declare conflicts of interest and act in the best interests of the Association and its members.",
        ]),
        ("Section 6 - Development framework", [
            "6.1 PLODA programmes shall support national development priorities through economic growth, value creation, infrastructure, human-capital development, environmental sustainability and institutional accountability.",
            "6.2 Programme design shall give attention to NDS2-aligned themes including inclusive growth, job creation, empowerment, social protection, food security, housing and regional development.",
            "6.3 Land development shall be planned, lawful, transparent and supported by appropriate technical, environmental, financial and community safeguards.",
            "6.4 Programme opportunities shall be communicated fairly, with eligibility conditions, fees, risks and member responsibilities clearly explained.",
        ]),
        ("Section 7 - Agro-residential stands, food security and livestock", [
            "7.1 Agro-residential initiatives shall combine residential use with responsible small-scale agricultural production where the applicable planning and land-use approvals permit.",
            "7.2 Members shall be encouraged to pursue suitable crop production, livestock development, water conservation, soil protection and climate-resilient practices.",
            "7.3 PLODA may coordinate training, shared services, market linkages and partnerships that support food security and household income.",
            "7.4 No member shall conduct an activity that unlawfully harms neighbours, public infrastructure, natural resources or approved settlement planning.",
        ]),
        ("Section 8 - Finance, payments and accountability", [
            "8.1 All money received or paid on behalf of PLODA shall be supported by authorised records and processed through approved channels.",
            "8.2 Members shall receive an official reference or receipt for a valid payment. The portal record does not remove the need to retain provider receipts and supporting documentation.",
            "8.3 PLODA shall maintain appropriate accounting records, payment approval controls, reconciliations and reporting to support accountability.",
            "8.4 Card details, one-time passwords and portal passwords shall never be requested through support chat, ordinary email or unverified telephone communication.",
            "8.5 Conflicts of interest, suspected fraud and irregular transactions shall be promptly reported and independently reviewed.",
        ]),
        ("Section 9 - Meetings, records and member communication", [
            "9.1 Meetings shall be convened and recorded in accordance with the signed master constitution and approved governance procedures.",
            "9.2 PLODA shall preserve appropriate registers, minutes, resolutions, membership records, financial records and project documentation.",
            "9.3 Official information may be communicated through the member portal, approved email channels, formal notices or other verified methods.",
            "9.4 Members are responsible for monitoring official communications and ensuring that their contact details remain current.",
        ]),
        ("Section 10 - Ethics, dispute resolution and amendment", [
            "10.1 Members and office-bearers shall act honestly, avoid abuse of position and respect the rights, property and dignity of others.",
            "10.2 Complaints and disputes shall be handled promptly, fairly and confidentially through approved internal procedures before external remedies are pursued where appropriate.",
            "10.3 Amendments shall be proposed, considered and approved only through the procedure established by the signed master constitution.",
            "10.4 If this portal reference conflicts with the duly signed master constitution, the signed master constitution shall prevail.",
        ]),
    ]

    for index, (title, paragraphs) in enumerate(sections):
        story.append(Paragraph(title, h1))
        if index == 0:
            story.append(HRFlowable(width="100%", thickness=.8, color=GOLD_500, spaceAfter=13))
        for item in paragraphs:
            if re_clause := (len(item) > 3 and item[0].isdigit() and "." in item[:5]):
                clause_no, remainder = item.split(" ", 1)
                story.append(Paragraph(f"<b>{clause_no}</b> {remainder}", clause))
            else:
                story.append(Paragraph(item, body))
        if index in {2, 5, 7}:
            story.append(PageBreak())
        else:
            story.append(Spacer(1, 5 * mm))

    story.extend([
        PageBreak(),
        Spacer(1, 20 * mm),
        Paragraph("Member acknowledgement", h1),
        Paragraph("Every member is expected to read the signed master constitution, approved policies, official membership documents and programme-specific terms. Registration in the portal does not by itself create an entitlement to land or a particular project opportunity.", body),
        Spacer(1, 10 * mm),
        Table([
            ["Member full name", ""],
            ["Member number", ""],
            ["Signature", ""],
            ["Date", ""],
        ], colWidths=[45 * mm, doc.width - 45 * mm], rowHeights=[16 * mm] * 4, style=TableStyle([
            ("BOX", (0, 0), (-1, -1), .6, LINE),
            ("INNERGRID", (0, 0), (-1, -1), .4, LINE),
            ("BACKGROUND", (0, 0), (0, -1), CREAM_2),
            ("TEXTCOLOR", (0, 0), (0, -1), GREEN_900),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ])),
        Spacer(1, 13 * mm),
        Paragraph("Institutional reference", h2),
        Paragraph("Founder: Archibold Tapiwa Chigwende<br/>Patron: ........................................................<br/>Registered office: 23 Richwell Avenue, Meyrick Park, Mabelreign, Harare, Zimbabwe<br/>Portal: ploda.org<br/>Email: info@ploda.org", body_muted),
    ])
    doc.build(story)
    return output


def form_header(c: canvas.Canvas, title: str, subtitle: str, page_no: int) -> None:
    width, height = A4
    c.setFillColor(CREAM)
    c.rect(0, 0, width, height, fill=1, stroke=0)
    c.setFillColor(GREEN_950)
    c.rect(0, height - 42 * mm, width, 42 * mm, fill=1, stroke=0)
    draw_seal(c, 22 * mm, height - 19 * mm, 10 * mm)
    c.setFillColor(WHITE)
    c.setFont("Times-Bold", 18)
    c.drawString(38 * mm, height - 16 * mm, title)
    c.setFillColor(colors.HexColor("#C7D6D0"))
    c.setFont("Helvetica", 7)
    c.drawString(38 * mm, height - 22 * mm, subtitle)
    c.setFillColor(GOLD_300)
    c.setFont("Helvetica-Bold", 6.5)
    c.drawRightString(width - 18 * mm, height - 16 * mm, f"PAGE {page_no} OF 3")
    c.setStrokeColor(GOLD_500)
    c.line(18 * mm, 14 * mm, width - 18 * mm, 14 * mm)
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 6.2)
    c.drawString(18 * mm, 9.5 * mm, "PLODA Member Joining Form | 23 Richwell Avenue, Meyrick Park, Mabelreign, Harare")
    c.drawRightString(width - 18 * mm, 9.5 * mm, "info@ploda.org | ploda.org")


def section_heading(c: canvas.Canvas, text: str, y: float) -> float:
    c.setFillColor(GREEN_900)
    c.roundRect(18 * mm, y - 9 * mm, A4[0] - 36 * mm, 9 * mm, 2 * mm, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 7.4)
    c.drawString(22 * mm, y - 5.8 * mm, text.upper())
    return y - 14 * mm


def label(c: canvas.Canvas, text: str, x: float, y: float, required: bool = False) -> None:
    c.setFillColor(GREEN_950)
    c.setFont("Helvetica-Bold", 6.6)
    c.drawString(x, y, text + (" *" if required else ""))


def text_field(c: canvas.Canvas, name: str, x: float, y: float, width: float, height: float = 9 * mm, multiline: bool = False) -> None:
    # PDF text-field flag bit 13 enables multiline entry.
    flags = 4096 if multiline else 0
    c.acroForm.textfield(
        name=name,
        x=x,
        y=y,
        width=width,
        height=height,
        borderWidth=.7,
        borderColor=colors.HexColor("#BFC9C4"),
        fillColor=WHITE,
        textColor=INK,
        forceBorder=True,
        fontName="Helvetica",
        fontSize=8,
        fieldFlags=flags,
    )


def checkbox(c: canvas.Canvas, name: str, label_text: str, x: float, y: float, checked: bool = False) -> None:
    c.acroForm.checkbox(name=name, x=x, y=y - 2.2 * mm, size=4 * mm, checked=checked, buttonStyle="check", borderColor=GREEN_700, fillColor=WHITE, textColor=GREEN_900, forceBorder=True)
    c.setFillColor(INK)
    c.setFont("Helvetica", 7)
    c.drawString(x + 6 * mm, y - .5 * mm, label_text)


def build_joining_form() -> Path:
    output = OUT / "PLODA_Member_Joining_Form.pdf"
    c = canvas.Canvas(str(output), pagesize=A4, pageCompression=1)
    c.setTitle("PLODA Member Joining Form")
    c.setAuthor("People's Land Ownership and Development Association")
    width, height = A4
    margin = 18 * mm
    field_width = (width - 2 * margin - 8 * mm) / 2

    form_header(c, "Member Joining Form", "People's Land Ownership & Development Association", 1)
    y = height - 50 * mm
    c.setFillColor(colors.HexColor("#604C27"))
    c.roundRect(margin, y - 16 * mm, width - 2 * margin, 16 * mm, 2 * mm, fill=1, stroke=0)
    c.setFillColor(CREAM)
    c.setFont("Helvetica-Bold", 7)
    c.drawString(margin + 4 * mm, y - 5.5 * mm, "MEMBERSHIP NOTICE")
    c.setFont("Helvetica", 6.5)
    c.drawString(margin + 4 * mm, y - 10.5 * mm, "A US$200 non-refundable joining fee applies. Pay only through verified PLODA channels after official guidance.")
    y -= 22 * mm
    y = section_heading(c, "A. Personal information", y)

    label(c, "Full legal name", margin, y, True)
    text_field(c, "full_name", margin, y - 11 * mm, width - 2 * margin)
    y -= 20 * mm
    label(c, "National ID / Passport", margin, y, True)
    label(c, "Date of birth (DD/MM/YYYY)", margin + field_width + 8 * mm, y, True)
    text_field(c, "national_id", margin, y - 11 * mm, field_width)
    text_field(c, "date_of_birth", margin + field_width + 8 * mm, y - 11 * mm, field_width)
    y -= 20 * mm
    label(c, "Gender", margin, y)
    label(c, "Marital status", margin + field_width + 8 * mm, y)
    text_field(c, "gender", margin, y - 11 * mm, field_width)
    text_field(c, "marital_status", margin + field_width + 8 * mm, y - 11 * mm, field_width)
    y -= 20 * mm
    label(c, "Occupation", margin, y, True)
    label(c, "Employer / Business", margin + field_width + 8 * mm, y)
    text_field(c, "occupation", margin, y - 11 * mm, field_width)
    text_field(c, "employer_business", margin + field_width + 8 * mm, y - 11 * mm, field_width)
    y -= 22 * mm
    y = section_heading(c, "B. Contact information", y)
    label(c, "Mobile number", margin, y, True)
    label(c, "Alternative number", margin + field_width + 8 * mm, y)
    text_field(c, "mobile_number", margin, y - 11 * mm, field_width)
    text_field(c, "alternative_number", margin + field_width + 8 * mm, y - 11 * mm, field_width)
    y -= 20 * mm
    label(c, "Email address", margin, y, True)
    label(c, "Province", margin + field_width + 8 * mm, y, True)
    text_field(c, "email", margin, y - 11 * mm, field_width)
    text_field(c, "province", margin + field_width + 8 * mm, y - 11 * mm, field_width)
    y -= 20 * mm
    label(c, "Residential address", margin, y, True)
    text_field(c, "residential_address", margin, y - 20 * mm, width - 2 * margin, 18 * mm, multiline=True)
    c.showPage()

    form_header(c, "Member Joining Form", "Programme interests and next-of-kin information", 2)
    y = height - 50 * mm
    y = section_heading(c, "C. Next of kin", y)
    label(c, "Full name", margin, y, True)
    label(c, "Relationship", margin + field_width + 8 * mm, y, True)
    text_field(c, "next_of_kin_name", margin, y - 11 * mm, field_width)
    text_field(c, "next_of_kin_relationship", margin + field_width + 8 * mm, y - 11 * mm, field_width)
    y -= 20 * mm
    label(c, "Phone number", margin, y, True)
    label(c, "Residential address", margin + field_width + 8 * mm, y)
    text_field(c, "next_of_kin_phone", margin, y - 11 * mm, field_width)
    text_field(c, "next_of_kin_address", margin + field_width + 8 * mm, y - 11 * mm, field_width)
    y -= 23 * mm
    y = section_heading(c, "D. Membership and programme interests", y)
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 7)
    c.drawString(margin, y, "Select all areas that apply:")
    y -= 10 * mm
    checkbox(c, "interest_land", "Land ownership facilitation", margin, y)
    checkbox(c, "interest_agro", "Agro-residential development", margin + 86 * mm, y)
    y -= 10 * mm
    checkbox(c, "interest_agriculture", "Agriculture and food security", margin, y)
    checkbox(c, "interest_livestock", "Livestock development", margin + 86 * mm, y)
    y -= 10 * mm
    checkbox(c, "interest_enterprise", "Enterprise and empowerment", margin, y)
    checkbox(c, "interest_partnership", "Community development partnership", margin + 86 * mm, y)
    y -= 14 * mm
    label(c, "Briefly describe your membership interests and development goals", margin, y)
    text_field(c, "membership_goals", margin, y - 28 * mm, width - 2 * margin, 26 * mm, multiline=True)
    y -= 38 * mm
    y = section_heading(c, "E. Supporting information", y)
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 6.8)
    c.drawString(margin, y, "Indicate the supporting documents attached to this form:")
    y -= 10 * mm
    checkbox(c, "attached_id", "Certified ID / Passport copy", margin, y)
    checkbox(c, "attached_address", "Proof of residential address", margin + 86 * mm, y)
    y -= 10 * mm
    checkbox(c, "attached_photo", "Passport-size photograph", margin, y)
    checkbox(c, "attached_other", "Other supporting information", margin + 86 * mm, y)
    y -= 15 * mm
    label(c, "Other supporting information", margin, y)
    text_field(c, "other_supporting_information", margin, y - 15 * mm, width - 2 * margin, 13 * mm, multiline=True)
    c.showPage()

    form_header(c, "Member Joining Form", "Declaration, signatures and office use", 3)
    y = height - 50 * mm
    y = section_heading(c, "F. Applicant declaration", y)
    declaration = (
        "I declare that the information supplied in this application is true and complete. I understand that membership is subject to verification, the signed PLODA constitution, approved policies and programme-specific requirements. I acknowledge that registration does not by itself create an entitlement to land or any particular project opportunity. I consent to lawful verification of the information submitted and agree to use only officially verified PLODA payment channels."
    )
    text = c.beginText(margin, y)
    text.setFont("Helvetica", 7.3)
    text.setFillColor(INK)
    text.setLeading(12)
    words = declaration.split()
    line = ""
    for word in words:
        test = (line + " " + word).strip()
        if c.stringWidth(test, "Helvetica", 7.3) > width - 2 * margin:
            text.textLine(line)
            line = word
        else:
            line = test
    if line:
        text.textLine(line)
    c.drawText(text)
    y -= 37 * mm
    checkbox(c, "declaration_accepted", "I accept the applicant declaration above.", margin, y)
    y -= 15 * mm
    label(c, "Applicant full name", margin, y, True)
    text_field(c, "declaration_name", margin, y - 11 * mm, width - 2 * margin)
    y -= 21 * mm
    label(c, "Applicant signature", margin, y, True)
    label(c, "Date", margin + field_width + 8 * mm, y, True)
    text_field(c, "applicant_signature", margin, y - 12 * mm, field_width)
    text_field(c, "applicant_date", margin + field_width + 8 * mm, y - 12 * mm, field_width)
    y -= 25 * mm
    c.setFillColor(GREEN_900)
    c.roundRect(margin, y - 61 * mm, width - 2 * margin, 61 * mm, 3 * mm, fill=1, stroke=0)
    c.setFillColor(GOLD_300)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(margin + 5 * mm, y - 8 * mm, "FOR OFFICIAL PLODA USE ONLY")
    c.setFillColor(colors.HexColor("#C7D6D0"))
    c.setFont("Helvetica", 6.5)
    c.drawString(margin + 5 * mm, y - 14 * mm, "This section must be completed by an authorised PLODA officer.")
    label_x = margin + 5 * mm
    y2 = y - 22 * mm
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 6.2)
    c.drawString(label_x, y2, "Application reference")
    c.drawString(label_x + 84 * mm, y2, "Date received")
    text_field(c, "office_reference", label_x, y2 - 11 * mm, 75 * mm)
    text_field(c, "office_date_received", label_x + 84 * mm, y2 - 11 * mm, 72 * mm)
    y2 -= 20 * mm
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 6.2)
    c.drawString(label_x, y2, "Verification status")
    c.drawString(label_x + 84 * mm, y2, "Authorised officer")
    text_field(c, "office_status", label_x, y2 - 11 * mm, 75 * mm)
    text_field(c, "office_authorised_officer", label_x + 84 * mm, y2 - 11 * mm, 72 * mm)
    y -= 72 * mm
    c.setFillColor(colors.HexColor("#604C27"))
    c.roundRect(margin, y - 18 * mm, width - 2 * margin, 18 * mm, 2 * mm, fill=1, stroke=0)
    c.setFillColor(CREAM)
    c.setFont("Helvetica-Bold", 6.6)
    c.drawString(margin + 4 * mm, y - 6 * mm, "PAYMENT SAFETY")
    c.setFont("Helvetica", 6.3)
    c.drawString(margin + 4 * mm, y - 11.5 * mm, "Never disclose your password or OTP. Retain your provider receipt and PLODA reference. Verify any change of payment instructions.")
    c.save()
    return output


if __name__ == "__main__":
    print(build_constitution())
    print(build_joining_form())
