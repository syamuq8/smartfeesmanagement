import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from config import Config

def generate_receipt(student, payment, receipt_num):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
        rightMargin=20*mm, leftMargin=20*mm,
        topMargin=15*mm, bottomMargin=15*mm)

    styles = getSampleStyleSheet()
    PRIMARY  = colors.HexColor('#1a3c6e')
    LIGHT_BG = colors.HexColor('#f0f4f8')
    TEXT_DARK = colors.HexColor('#2d3748')

    def sty(name, **kw):
        return ParagraphStyle(name, parent=styles['Normal'], **kw)

    s_title    = sty('t', fontSize=20, fontName='Helvetica-Bold', textColor=PRIMARY, alignment=TA_CENTER, spaceAfter=2)
    s_sub      = sty('s', fontSize=9,  textColor=colors.HexColor('#718096'), alignment=TA_CENTER, spaceAfter=2)
    s_rec_no   = sty('r', fontSize=11, fontName='Helvetica-Bold', textColor=colors.white, alignment=TA_CENTER)
    s_label    = sty('l', fontSize=9,  textColor=colors.HexColor('#718096'))
    s_value    = sty('v', fontSize=10, fontName='Helvetica-Bold', textColor=TEXT_DARK)
    s_footer   = sty('f', fontSize=8,  textColor=colors.HexColor('#a0aec0'), alignment=TA_CENTER)

    paid_at = payment.get('paid_at', datetime.now())
    if isinstance(paid_at, str):
        paid_at = datetime.strptime(paid_at, '%Y-%m-%d %H:%M:%S')

    elems = []

    # Header
    elems += [
        Paragraph(Config.COLLEGE_NAME, s_title),
        Paragraph(Config.COLLEGE_ADDRESS, s_sub),
        Paragraph(f"Phone: {Config.COLLEGE_PHONE}  |  Email: {Config.COLLEGE_EMAIL}", s_sub),
        Spacer(1, 4*mm),
        HRFlowable(width="100%", thickness=2, color=PRIMARY),
        Spacer(1, 3*mm),
    ]

    # Receipt number banner
    banner = Table([[Paragraph(f"FEE RECEIPT  |  #REC-{str(receipt_num).upper()[:8]}", s_rec_no)]], colWidths=[170*mm])
    banner.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), PRIMARY),
        ('TOPPADDING', (0,0), (-1,-1), 8), ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    elems += [banner, Spacer(1, 5*mm)]

    # Meta row
    meta = Table([
        [Paragraph('Date of Payment', s_label), Paragraph('Payment Mode', s_label), Paragraph('Academic Year', s_label)],
        [Paragraph(paid_at.strftime('%d %B %Y, %I:%M %p'), s_value),
         Paragraph(str(payment.get('payment_mode', 'Cash')), s_value),
         Paragraph(f"{paid_at.year}–{paid_at.year+1}", s_value)]
    ], colWidths=[60*mm, 55*mm, 55*mm])
    meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), LIGHT_BG), ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6), ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('INNERGRID', (0,0), (-1,-1), 0.3, colors.HexColor('#e2e8f0')),
    ]))
    elems += [meta, Spacer(1, 5*mm)]

    # Student details
    sd = Table([
        ['STUDENT DETAILS', '', '', ''],
        ['Name',        student.get('name',''),         'Roll Number', student.get('roll_number','')],
        ['Branch',      student.get('branch',''),       'Year',        str(student.get('year',''))],
        ['Email',       student.get('email',''),        'Phone',       student.get('phone','')],
        ['Parent Email', student.get('parent_email',''), '', ''],
    ], colWidths=[30*mm, 65*mm, 30*mm, 45*mm])
    sd.setStyle(TableStyle([
        ('SPAN',(0,0),(-1,0)), ('BACKGROUND',(0,0),(-1,0), PRIMARY),
        ('TEXTCOLOR',(0,0),(-1,0), colors.white), ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
        ('FONTSIZE',(0,0),(-1,0), 10), ('TOPPADDING',(0,0),(-1,-1),6),
        ('BOTTOMPADDING',(0,0),(-1,-1),6), ('LEFTPADDING',(0,0),(-1,-1),8),
        ('TEXTCOLOR',(0,1),(0,-1), colors.HexColor('#718096')),
        ('TEXTCOLOR',(2,1),(2,-1), colors.HexColor('#718096')),
        ('FONTNAME',(1,1),(1,-1),'Helvetica-Bold'), ('FONTNAME',(3,1),(3,-1),'Helvetica-Bold'),
        ('FONTSIZE',(0,1),(-1,-1), 9),
        ('BOX',(0,0),(-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('INNERGRID',(0,1),(-1,-1), 0.3, colors.HexColor('#e2e8f0')),
        ('SPAN',(0,4),(1,4)), ('SPAN',(2,4),(3,4)),
    ]))
    elems += [sd, Spacer(1, 5*mm)]

    # Fee summary
    total_fee   = float(student.get('total_fee', 0))
    paid_now    = float(payment.get('amount', 0))
    paid_before = float(student.get('paid_amount', 0)) - paid_now
    balance     = float(student.get('balance', 0))

    fs = Table([
        ['FEE SUMMARY', '', ''],
        ['Total Fees',       '', f"₹ {total_fee:,.2f}"],
        ['Previously Paid',  '', f"₹ {paid_before:,.2f}"],
        ['Amount Paid Now',  '', f"₹ {paid_now:,.2f}"],
        ['Balance Due',      '', f"₹ {balance:,.2f}"],
    ], colWidths=[90*mm, 40*mm, 40*mm])
    fs.setStyle(TableStyle([
        ('SPAN',(0,0),(-1,0)), ('BACKGROUND',(0,0),(-1,0), PRIMARY),
        ('TEXTCOLOR',(0,0),(-1,0), colors.white), ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
        ('FONTSIZE',(0,0),(-1,0), 10), ('ALIGN',(2,0),(2,-1),'RIGHT'),
        ('TOPPADDING',(0,0),(-1,-1),6), ('BOTTOMPADDING',(0,0),(-1,-1),6),
        ('LEFTPADDING',(0,0),(-1,-1),8), ('RIGHTPADDING',(0,0),(-1,-1),8),
        ('FONTSIZE',(0,1),(-1,-1),10),
        ('BACKGROUND',(0,3),(-1,3), colors.HexColor('#ebfbf1')),
        ('TEXTCOLOR',(0,3),(-1,3), colors.HexColor('#276749')),
        ('FONTNAME',(0,3),(-1,3),'Helvetica-Bold'),
        ('BACKGROUND',(0,4),(-1,4), LIGHT_BG),
        ('BOX',(0,0),(-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('INNERGRID',(0,1),(-1,-1), 0.3, colors.HexColor('#e2e8f0')),
    ]))
    elems += [fs, Spacer(1, 6*mm)]

    if payment.get('remarks'):
        rt = Table([['Remarks', payment['remarks']]], colWidths=[30*mm, 140*mm])
        rt.setStyle(TableStyle([
            ('TEXTCOLOR',(0,0),(0,0), colors.HexColor('#718096')),
            ('FONTSIZE',(0,0),(-1,-1),9), ('TOPPADDING',(0,0),(-1,-1),4),
        ]))
        elems += [rt, Spacer(1, 4*mm)]

    # Signatures
    sig = Table([['Received By', '', 'Authorised Signatory']], colWidths=[60*mm, 50*mm, 60*mm])
    sig.setStyle(TableStyle([
        ('TOPPADDING',(0,0),(-1,-1),20), ('BOTTOMPADDING',(0,0),(-1,-1),4),
        ('FONTSIZE',(0,0),(-1,-1),9), ('TEXTCOLOR',(0,0),(-1,-1), colors.HexColor('#718096')),
        ('LINEABOVE',(0,0),(0,0), 0.5, colors.HexColor('#a0aec0')),
        ('LINEABOVE',(2,0),(2,0), 0.5, colors.HexColor('#a0aec0')),
    ]))
    elems += [sig, Spacer(1,5*mm),
        HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#e2e8f0')),
        Spacer(1,3*mm),
        Paragraph("This is a computer-generated receipt and does not require a physical signature.", s_footer),
        Paragraph(f"Generated on {datetime.now().strftime('%d %B %Y at %I:%M %p')}", s_footer),
    ]

    doc.build(elems)
    buffer.seek(0)
    return buffer
