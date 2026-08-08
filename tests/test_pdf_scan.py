from reportlab.pdfgen import canvas
import requests
import time

print("[1/3] Generating simulated Bank Statement PDF...")
c = canvas.Canvas("dummy_statement.pdf")
c.drawString(50, 800, "CONFIDENTIAL ENTERPRISE DOCUMENT")
c.drawString(50, 780, "Employee: John Smith")
c.drawString(50, 760, "Internal Assignment: Project Titan")
c.drawString(50, 740, "Aadhaar Registration: 1234 5678 9012")
c.drawString(50, 720, "Direct Deposit Account: 987654321098")
c.drawString(50, 700, "Please do not leak this PDF outside the corporate intranet.")
c.save()

print("[2/3] Uploading dummy_statement.pdf to SSS Backend DLP Scanner...")
try:
    url = "http://127.0.0.1:5000/scan-document"
    with open("dummy_statement.pdf", "rb") as f:
        files = {"document": ("dummy_statement.pdf", f, "application/pdf")}
        response = requests.post(url, files=files)
        
    print("[3/3] SSS Backend OCR Response:")
    print(f"  -> Status Code: {response.status_code}")
    print(f"  -> Extracted Payload: {response.json()}")
except Exception as e:
    print(f"  -> Error calling endpoint: {e}")
