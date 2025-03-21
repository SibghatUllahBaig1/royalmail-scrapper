from flask import Flask, request, jsonify, Response
import requests
import json
import re
from bs4 import BeautifulSoup
import urllib3
import base64
from pathlib import Path

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# Bright Data Web Unlocker proxy configuration
PROXY_HOST = "brd.superproxy.io"
PROXY_PORT = "33335"
PROXY_USER = "brd-customer-hl_24675aba-zone-web_unlocker1-debug-full"
PROXY_PASS = "g3z9kygx2w7k"

def make_unlocker_request(url):
    proxies = {
        'https': f'https://{PROXY_HOST}:{PROXY_PORT}',
        'http': f'http://{PROXY_HOST}:{PROXY_PORT}'
    }
    
    headers = {
        'x-unblock-expect': json.dumps({
            'element': '.status-description h2 strong',
            'timeout': 120000  # 2 minutes in milliseconds
        })
    }
    
    try:
        response = requests.get(
            url,
            proxies=proxies,
            headers=headers,
            verify=False,
            timeout=(30, 120)  # (connect timeout, read timeout) in seconds
        )
        
        # Print debug information
        debug_info = response.headers.get('x-brd-debug')
        if debug_info:
            print(f"Debug Info: {debug_info}")
        
        if response.status_code == 502:
            error_code = response.headers.get('x-luminati-error-code', 'unknown')
            error_message = response.headers.get('x-luminati-error', 'No specific error message')
            print(f"Luminati Error Code: {error_code}")
            print(f"Luminati Error Message: {error_message}")
            
            # Create a new Response object for the error
            error_response = requests.Response()
            error_response.status_code = 502
            error_response._content = f"Luminati Error: {error_code} - {error_message}".encode()
            return error_response
            
        return response
        
    except requests.exceptions.RequestException as e:
        print(f"Request Exception: {str(e)}")
        # Create a Response-like object for the error case
        error_response = requests.Response()
        error_response.status_code = 502
        error_response.text = str(e)
        return error_response

def make_unlocker_request_date_only(url):
    proxy_url = f'http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}'
    proxies = {
        'http': proxy_url,
        'https': proxy_url
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'x-unblock-expect': json.dumps({
            'element': '.summary-line'
        })
    }
    
    try:
        response = requests.get(
            url,
            proxies=proxies,
            headers=headers,
            verify=False,
            timeout=(30, 120)
        )
        
        # Add detailed error logging
        if response.status_code != 200:
            print(f"Error Response Status: {response.status_code}")
            print(f"Error Response Headers: {dict(response.headers)}")
            print(f"Error Response Content: {response.text}")
            
        return response
        
    except requests.exceptions.RequestException as e:
        print(f"Request Exception: {str(e)}")
        raise

def make_unlocker_screenshot_request(url, save_path=None, viewport_size=None, full_page=False):
    proxies = {
        'https': f'http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}',
        'http': f'http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}'
    }
    
    # Prepare screenshot configuration
    expect_config = {
        'element': 'body',
        'timeout': 30000  # 30 seconds timeout
    }
    
    if viewport_size:
        expect_config['viewport'] = viewport_size
    if full_page:
        expect_config['fullPage'] = True
    
    headers = {
        'x-unblock-data-format': 'screenshot',
        'Accept': 'image/png',
        'x-unblock-expect': json.dumps(expect_config)
    }
    
    try:
        response = requests.get(
            url,
            proxies=proxies,
            headers=headers,
            verify=False,
            timeout=60
        )
        
        if response.status_code == 502:
            error_code = response.headers.get('x-luminati-error-code', 'unknown')
            error_message = response.headers.get('x-luminati-error', 'No specific error message')
            print(f"Luminati Error Code: {error_code}")
            print(f"Luminati Error Message: {error_message}")
            return None
            
        if response.status_code == 200:
            if not response.content:
                print("Response content is empty")
                return None
                
            # Check content type more strictly
            content_type = response.headers.get('content-type', '')
            if 'image/png' not in content_type:
                print(f"Unexpected content type: {content_type}")
                return None
                
            if save_path:
                # Save the screenshot to a file
                Path(save_path).write_bytes(response.content)
                return True
            return response.content
        
        print(f"Unexpected status code: {response.status_code}")
        return None
        
    except requests.exceptions.RequestException as e:
        print(f"Screenshot Request Exception: {str(e)}")
        return None

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
                'status_code': response.status_code
            }), response.status_code


        # Save HTML to a file
        with open('debug_response.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        # Continue with the rest of your function...
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
        
        # Print debug information about summary elements
        print("\nFound Summary Elements:")
        for element in summary_elements:
            print(f"Summary Element Text: {element.text}")
        
        for element in summary_elements:
            text = element.text
            match = date_pattern.search(text)
            if match:
                return jsonify({'delivery_date': match.group()})

        # If no date found, return the complete HTML for debugging
        return jsonify({
            'message': 'Delivery date not found'
            # 'html_response': response.text,
            # 'summary_elements_found': [elem.text for elem in summary_elements]
        }), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/track_screenshot', methods=['GET'])
def track_package_screenshot():
    tracking_number = request.args.get('tracking_number')
    if not tracking_number:
        return jsonify({'error': 'Tracking number is required'}), 400

    try:
        url = f'https://www.royalmail.com/track-your-item#/tracking-results/{tracking_number}'
        
        screenshot_data = make_unlocker_screenshot_request(url)
        if screenshot_data:
            return Response(
                screenshot_data,
                mimetype='image/png',
                headers={
                    'Content-Disposition': f'attachment; filename=tracking_{tracking_number}.png'
                }
            )
        
        return jsonify({
            'error': 'Screenshot Failed',
            'tracking_number': tracking_number,
            'details': 'Failed to capture screenshot'
        }), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003)
