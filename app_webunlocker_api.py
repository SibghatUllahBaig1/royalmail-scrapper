from flask import Flask, request, jsonify
import requests
import json
import re
from bs4 import BeautifulSoup

app = Flask(__name__)

# Bright Data Web Unlocker API configuration
API_TOKEN = '70aa6e1fafe58f8fc91d6d7c4dfb52ddce80a473b00e6e495ce205a0b9e97246'
ZONE_NAME = 'web_unlocker1'
API_URL = 'https://api.brightdata.com/request'

def make_unlocker_request(url):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {API_TOKEN}',
        'x-unblock-expect': json.dumps({
            'element': 
                '.status-description h2 strong'  # Status element
                                        
        })
    }
    
    payload = {
        'zone': ZONE_NAME,
        'url': url,
        'format': 'raw'
    }
    
    response = requests.post(API_URL, headers=headers, json=payload)
    return response

def make_unlocker_request_date_only(url):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {API_TOKEN}',
        'x-unblock-expect': json.dumps({
            'element': '.summary-line'  # Element containing the date
        })
    }
    
    payload = {
        'zone': ZONE_NAME,
        'url': url,
        'format': 'raw'
    }
    
    response = requests.post(API_URL, headers=headers, json=payload)
    return response

def check_for_hcaptcha(soup):
    try:
        # Check for data-site element
        data_site_elements = soup.select('[data-site]')
        if data_site_elements:
            return True
            
        # Additional checks for hCaptcha
        hcaptcha_indicators = [
            'iframe[src*="hcaptcha"]',  # hCaptcha iframe
            '.h-captcha',               # hCaptcha widget
            '#hcaptcha-challenge',      # Challenge window
            '[name="h-captcha-response"]' # Response field
        ]
        
        for selector in hcaptcha_indicators:
            if soup.select(selector):
                return True
        
        return False
    except Exception as e:
        print(f"Error checking for hCaptcha: {str(e)}")
        return False

@app.route('/test', methods=['GET'])
def test_endpoint():
    return jsonify({
        'message': 'API is working correctly'
    })

@app.route('/track', methods=['GET'])
def track_package():
    tracking_number = request.args.get('tracking_number')
    if not tracking_number:
        return jsonify({'error': 'Tracking number is required'}), 400

    try:
        url = f'https://www.royalmail.com/track-your-item#/tracking-results/{tracking_number}'
        response = make_unlocker_request(url)
        
        if response.status_code != 200:
            return jsonify({
                'error': 'Web Unlocker API Error',
                'details': response.text,
                'status_code': response.status_code
            }), response.status_code

        # Parse the HTML response
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check for hCaptcha
        if check_for_hcaptcha(soup):
            return jsonify({
                'error': 'CAPTCHA Detected',
                'tracking_number': tracking_number,
                'details': 'hCaptcha verification required'
            }), 429
        
        # Extract status
        status_element = soup.select_one('.status-description h2 strong')
        if not status_element:
            return jsonify({
                'error': 'Status Extraction Failed',
                'tracking_number': tracking_number,
                'details': 'Could not find tracking status'
            }), 404
        
        status = status_element.text.strip()
        
        # Extract delivery message
        delivery_message_element = soup.select_one('.estimated-delivery-message .summary-line div')
        delivery_message = delivery_message_element.text.strip() if delivery_message_element else ''
        
        # Extract tracking details
        tracking_details = {}
        detail_sections = soup.select('.tracking-detail')
        
        if not detail_sections:
            return jsonify({
                'error': 'Not Found',
                'message': 'No tracking details available',
                'tracking_number': tracking_number
            }), 404

        for section in detail_sections:
            try:
                label = section.select_one('[class$="-label"]').text.strip(':')
                value = section.select_one('span:last-child').text.strip()
                tracking_details[label] = value
            except:
                continue

        response_data = {
            'status': status,
            'delivery_message': delivery_message,
            'tracking_details': tracking_details
        }

        return jsonify(response_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/track_only_number', methods=['GET'])
def track_package_only_number():
    tracking_number = request.args.get('tracking_number')
    if not tracking_number:
        return jsonify({'error': 'Tracking number is required'}), 400

    try:
        url = f'https://www.royalmail.com/track-your-item#/tracking-results/{tracking_number}'
        response = make_unlocker_request_date_only(url)
        
        if response.status_code != 200:
            return jsonify({
                'error': 'Web Unlocker API Error',
                'details': response.text,
                'status_code': response.status_code
            }), response.status_code

        # Parse the HTML response
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check for hCaptcha
        if check_for_hcaptcha(soup):
            return jsonify({
                'error': 'CAPTCHA Detected',
                'tracking_number': tracking_number,
                'details': 'hCaptcha verification required'
            }), 429
        
        # Find delivery date
        summary_elements = soup.select('.summary-line')
        date_pattern = re.compile(r'\b\d{2}-\d{2}-\d{4}\b')
        
        for element in summary_elements:
            text = element.text
            match = date_pattern.search(text)
            if match:
                return jsonify({'delivery_date': match.group()})

        return jsonify({'message': 'Delivery date not found'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003)
