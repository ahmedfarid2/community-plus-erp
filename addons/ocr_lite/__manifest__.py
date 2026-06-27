{
    "name": "Invoice OCR (Lite)",
    "version": "19.0.1.0.0",
    "category": "Accounting/OCR",
    "summary": "Scan vendor invoices with free Tesseract OCR and create draft bills",
    "author": "Farid",
    "license": "LGPL-3",
    "depends": ["account", "mail"],
    "data": ["security/ir.model.access.csv", "views/ocr_views.xml"],
    "external_dependencies": {"python": ["pytesseract", "pdf2image"]},
    "installable": True,
    "application": True,
}
