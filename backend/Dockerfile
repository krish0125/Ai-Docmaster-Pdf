FROM python:3.11-slim

# Install system dependencies for PDF and Image processing, plus OCR
RUN apt-get update && apt-get install -y \
    poppler-utils \
    libreoffice \
    wkhtmltopdf \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy the requirements file and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend application code
COPY . .

# Create the uploads directory for temporary file processing
RUN mkdir -p uploads

# Expose the port (Render provides this via the PORT environment variable, defaults to 5001)
EXPOSE 5001

# Command to run the application using Gunicorn for production
# Gunicorn binds to the PORT environment variable
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-5001} --workers 2 --timeout 120 app:app"]
