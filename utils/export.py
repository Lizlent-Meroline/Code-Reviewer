"""Export analysis reports to various formats."""
import json
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors


def export_json(data: dict) -> str:
    """Export analysis data as formatted JSON string."""
    return json.dumps(data, indent=2, default=str)


def export_pdf(data: dict) -> bytes:
    """Export analysis data as PDF report."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1e293b'),
        spaceAfter=30,
    )
    story.append(Paragraph("Code Analysis Report", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Repository Info
    story.append(Paragraph(f"<b>Repository:</b> {data.get('repo_url', 'N/A')}", styles['Normal']))
    story.append(Paragraph(f"<b>Branch:</b> {data.get('branch', 'N/A')}", styles['Normal']))
    story.append(Paragraph(f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    # Summary
    summary = data.get('summary', {})
    story.append(Paragraph("<b>Summary</b>", styles['Heading2']))
    summary_data = [
        ['Metric', 'Count'],
        ['Total Files', str(summary.get('total', 0))],
        ['Code Files', str(summary.get('code', 0))],
        ['Documentation Files', str(summary.get('docs', 0))],
        ['Other Files', str(summary.get('other', 0))],
        ['Total Issues', str(summary.get('issues', 0))],
    ]
    
    summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Code Issues
    code_files = data.get('code', [])
    files_with_issues = [f for f in code_files if f.get('issues')]
    
    if files_with_issues:
        story.append(Paragraph("<b>Files with Issues</b>", styles['Heading2']))
        story.append(Spacer(1, 0.1*inch))
        
        for file in files_with_issues[:20]:  # Limit to first 20
            story.append(Paragraph(f"<b>{file['path']}</b>", styles['Heading3']))
            for issue in file['issues'][:5]:  # Limit to 5 issues per file
                story.append(Paragraph(f"• {issue}", styles['Normal']))
            story.append(Spacer(1, 0.1*inch))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
