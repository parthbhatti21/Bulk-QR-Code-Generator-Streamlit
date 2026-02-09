from flask import Flask, render_template, request, jsonify, send_file
import qrcode
from qrcode.image.pil import PilImage
import io
import base64
import string
import random
from datetime import datetime
import os

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Simple in-memory storage (use database for production)
# For production, use PostgreSQL or MongoDB
qr_storage = {}

def generate_short_id(length=6):
    """Generate a short random ID for the QR code"""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def generate_html_with_links(links):
    """Generate HTML content with all the links"""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Links from QR Code</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }
            .container {
                background: white;
                border-radius: 12px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                padding: 30px;
                max-width: 500px;
                width: 100%;
            }
            h1 {
                color: #333;
                text-align: center;
                margin-bottom: 10px;
                font-size: 28px;
            }
            .subtitle {
                text-align: center;
                color: #666;
                margin-bottom: 30px;
                font-size: 14px;
            }
            .links-container {
                display: flex;
                flex-direction: column;
                gap: 12px;
            }
            a {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 16px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                text-decoration: none;
                border-radius: 8px;
                transition: all 0.3s ease;
                font-weight: 500;
                overflow: hidden;
            }
            a:active, a:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
            }
            a .link-text {
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                flex: 1;
                margin-right: 10px;
            }
            a .arrow {
                font-size: 18px;
                flex-shrink: 0;
            }
            .link-number {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                width: 24px;
                height: 24px;
                background: rgba(255,255,255,0.2);
                border-radius: 50%;
                margin-right: 10px;
                flex-shrink: 0;
                font-size: 12px;
                font-weight: bold;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📱 Your Links</h1>
            <p class="subtitle">Tap any link below to open it</p>
            <div class="links-container">
    """
    
    for idx, link in enumerate(links, 1):
        if link.strip():
            safe_link = link.strip()
            if not safe_link.startswith(('http://', 'https://')):
                safe_link = 'https://' + safe_link
            html_content += f'                <a href="{safe_link}" target="_blank"><span class="link-number">{idx}</span><span class="link-text">{link.strip()}</span><span class="arrow">→</span></a>\n'
    
    html_content += """
            </div>
        </div>
    </body>
    </html>
    """
    return html_content

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/generate', methods=['POST'])
def generate_qr():
    """Generate QR code and store links"""
    try:
        data = request.json
        links = data.get('links', [])
        
        # Validate input
        if not links or not any(link.strip() for link in links):
            return jsonify({'error': 'Please enter at least one link'}), 400
        
        # Filter empty links
        links = [link.strip() for link in links if link.strip()]
        
        # Generate unique ID
        qr_id = generate_short_id()
        while qr_id in qr_storage:
            qr_id = generate_short_id()
        
        # Create URL for the QR code
        qr_url = f"{request.host_url.rstrip('/')}/#/qr/{qr_id}"
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4
        )
        qr.add_data(qr_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # Store the links data
        qr_storage[qr_id] = {
            'links': links,
            'created_at': datetime.now().isoformat(),
            'qr_image': img_base64
        }
        
        return jsonify({
            'success': True,
            'qr_id': qr_id,
            'qr_image': f'data:image/png;base64,{img_base64}',
            'qr_url': qr_url,
            'links': links
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/qr/<qr_id>')
def get_qr_data(qr_id):
    """Get the links and HTML for a specific QR code"""
    if qr_id not in qr_storage:
        return jsonify({'error': 'QR code not found'}), 404
    
    data = qr_storage[qr_id]
    links = data['links']
    html_content = generate_html_with_links(links)
    
    return jsonify({
        'links': links,
        'html': html_content
    })

@app.route('/qr/<qr_id>')
def view_qr_links(qr_id):
    """Display the HTML page with all links"""
    if qr_id not in qr_storage:
        return "QR code not found", 404
    
    data = qr_storage[qr_id]
    links = data['links']
    html_content = generate_html_with_links(links)
    
    return html_content

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 8000)))



