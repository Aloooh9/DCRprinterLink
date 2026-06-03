# Use the official Playwright image which includes Python and pre-requisite system libs
FROM mcr.microsoft.com/playwright/python:v1.43.0-jammy

# Set active working directory
WORKDIR /app

# Handle dependency installations
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Ensure modern Chromium binaries are downloaded inside the image layer
RUN playwright install chromium

# Copy remaining source modules
COPY . .

# Expose web service endpoint
EXPOSE 5000

# Execute app framework listener
CMD ["python", "app.py"]
