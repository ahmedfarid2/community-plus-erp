# Community Plus Odoo image: stock Odoo + free OCR stack (Tesseract).
# Powers the ocr_lite module (invoice scanning) with no paid AI service.
ARG ODOO_TAG=19.0
FROM odoo:${ODOO_TAG}

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr poppler-utils \
    && pip3 install --no-cache-dir --break-system-packages pytesseract pdf2image \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
USER odoo
