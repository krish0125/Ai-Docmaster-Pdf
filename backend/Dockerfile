FROM python:3.11-slim

# Install system dependencies for PDF and Image processing, plus OCR
# Note: wkhtmltopdf is no longer in Debian trixie repos, so we install it manually
RUN apt-get update && apt-get install -y \
    poppler-utils \
    libreoffice \
    tesseract-ocr \
    wget \
    xfonts-75dpi \
    xfonts-base \
    fontconfig \
    libxrender1 \
    libxext6 \
    && wget -q https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-3/wkhtmltox_0.12.6.1-3.bookworm_amd64.deb \
    && apt-get install -y ./wkhtmltox_0.12.6.1-3.bookworm_amd64.deb \
    && rm wkhtmltox_0.12.6.1-3.bookworm_amd64.deb \
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
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-5001} --workers 1 --timeout 120 app:app"]