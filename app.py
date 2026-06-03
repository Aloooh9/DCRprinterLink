import os
import re
import time
import zipfile
from io import BytesIO
from flask import Flask, render_template, request, send_file
from playwright.sync_api import sync_playwright

app = Flask(__name__)

def extract_request_number(page):
    try:
        # Give the network time to settle down completely
        page.wait_for_load_state("networkidle", timeout=20000)
    except Exception:
        # If networkidle times out due to persistent background trackers, we proceed anyway
        pass
    
    try:
        # Grab all rendered text on the page
        body_text = page.locator("body").text_content()
        
        # UPDATED REGEX: Captures alphanumeric blocks separated by spaces, dashes, or slashes
        # This safely captures formats like "2026 - 123456" or "2026-123456"
        pattern = r'(?:رقم الطلب|Request Number|Reference No|Reference Number|رقم المرجع)[\s:-]*([A-Za-z0-9]+(?:\s*[-/]\s*[A-Za-z0-9]+)*)'
        match = re.search(pattern, body_text)
        
        if match:
            return match.group(1).strip()
    except Exception as e:
        print(f"Extraction error: {e}")
    
    # Fallback if the page is unresponsive or the specific label isn't found
    return f"request_{int(time.time() * 1000)}"

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        urls = request.form.get('urls', '').splitlines()
        urls = [url.strip() for url in urls if url.strip()]
        
        if not urls:
            return "Please provide at least one valid URL.", 400

        # Create zip container directly in memory to keep the Docker container lightweight
        memory_file = BytesIO()
        
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            with sync_playwright() as p:
                # Launch headless browser with sandbox flags optimized for Docker environments
                browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
                context = browser.new_context()
                page = context.new_page()
                
                for idx, url in enumerate(urls):
                    try:
                        # Increased timeout to 60 seconds to accommodate slower portal responses
                        page.goto(url, timeout=60000)
                        
                        # Soft pause to ensure all server-side components/fonts finish rendering
                        page.wait_for_timeout(3000) 
                        
                        # Extract naming token and sanitize illegal file characters
                        filename = extract_request_number(page)
                        filename = re.sub(r'[\\/*?:"<>|]', "", filename)
                        
                        # Print exactly to A4
                        pdf_data = page.pdf(
                            format="A4",
                            print_background=True,
                            margin={"top": "10mm", "bottom": "10mm", "left": "10mm", "right": "10mm"}
                        )
                        
                        # Commit file byte content straight to zip entry
                        zipf.writestr(f"{filename}.pdf", pdf_data)
                        
                    except Exception as e:
                        # Ensures one bad link doesn't crash the whole batch execution
                        zipf.writestr(f"error_link_{idx+1}.txt", f"Failed URL: {url}\nError Info: {str(e)}")
                
                browser.close()
        
        memory_file.seek(0)
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name='dubai_court_receipts.zip'
        )

    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
