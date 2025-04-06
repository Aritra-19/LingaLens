FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    # Hindi
    tesseract-ocr-hin \
    # French
    tesseract-ocr-fra \
    # Spanish
    tesseract-ocr-spa \
    # Bengali
    tesseract-ocr-ben \
    # For PDF processing
    poppler-utils \
    && apt-get clean

WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set the startup command
CMD ["gunicorn", "--bind", "0.0.0.0:$PORT", "app:app"]