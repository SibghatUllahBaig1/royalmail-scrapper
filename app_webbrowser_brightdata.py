from flask import Flask, request, jsonify
from selenium.webdriver import Remote, ChromeOptions
from selenium.webdriver.chromium.remote_connection import ChromiumRemoteConnection
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException
import re
import time

app = Flask(__name__)


#*******Bright Data WebScapping Browser******

# Bright Data credentials
AUTH = 'brd-customer-hl_24675aba-zone-scraping_browser1:4b6f1lnz6xuh'
SBR_WEBDRIVER = f'https://{AUTH}@brd.superproxy.io:9515'

def create_driver():
    print('Connecting to Scraping Browser...')
    sbr_connection = ChromiumRemoteConnection(SBR_WEBDRIVER, 'goog', 'chrome')
    options = ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    return Remote(sbr_connection, options=options)

def safe_quit(driver):
    try:
        if driver:
            driver.quit()
    except WebDriverException:
        pass  # Ignore session not found errors during quit

@app.route('/test', methods=['GET'])
def test_endpoint():
    return jsonify({'message': 'API is working correctly'})

@app.route('/track', methods=['GET'])
def track_package():
    tracking_number = request.args.get('tracking_number')
    if not tracking_number:
        return jsonify({'error': 'Tracking number is required'}), 400

    driver = None
    try:
        driver = create_driver()
        print('Connected! Navigating...')
        url = f'https://www.royalmail.com/track-your-item#/tracking-results/{tracking_number}'
        driver.get(url)
        
        # Increased wait time for initial page load
        driver.implicitly_wait(45)

        # Take initial screenshot
        print('Taking initial screenshot')
        try:
            driver.save_screenshot('initial_page.png')
        except Exception as screenshot_error:
            print(f'Initial screenshot error: {screenshot_error}')

        # Wait for any dynamic content to load
        wait = WebDriverWait(driver, 45)
        
        try:
            # Wait for page to be fully loaded
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Print page title and URL for debugging
            print(f"Current URL: {driver.current_url}")
            print(f"Page Title: {driver.title}")

            # Get page source for debugging
            page_source = driver.page_source
            print("Page source length:", len(page_source))
            
            # # First, check if we're on an error page or if captcha is present
            # if "captcha" in page_source.lower():
            #     return jsonify({
            #         'error': 'CAPTCHA detected',
            #         'tracking_number': tracking_number
            #     }), 429

            # Try to find any tracking-related content first
            tracking_content_selectors = [
                '.tracking-results',
                '#tracking-results',
                '.tracking-container',
                '.tracking-details'
            ]
            
            tracking_content_found = False
            for selector in tracking_content_selectors:
                try:
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    tracking_content_found = True
                    print(f"Found tracking content with selector: {selector}")
                    break
                except:
                    continue

            if not tracking_content_found:
                print("No tracking content found on page")
                driver.save_screenshot('no_tracking_content.png')
                return jsonify({
                    'error': 'No tracking content found',
                    'tracking_number': tracking_number
                }), 404

            # Try multiple possible selectors for status
            status = None
            status_selectors = [
                '.status-description h2 strong',
                '.tracking-status strong',
                '.status-message',
                '[data-test-id="tracking-status"]',
                '.tracking-results h2',
                '.delivery-status',
                '.status'
            ]
            
            print("Searching for status...")
            for selector in status_selectors:
                try:
                    status_element = wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    status = status_element.text.strip()
                    print(f"Found status with selector {selector}: {status}")
                    if status:
                        break
                except:
                    print(f"Selector {selector} not found")
                    continue

            if not status:
                # Try to get any visible text that might contain status
                try:
                    main_content = driver.find_element(By.TAG_NAME, 'main')
                    print("Main content text:", main_content.text)
                except:
                    print("Could not find main content")

                raise ValueError("Status text not found")

            # Try multiple possible selectors for delivery message
            delivery_message = ""
            message_selectors = [
                '.estimated-delivery-message .summary-line div',
                '.delivery-message',
                '.estimated-delivery',
                '[data-test-id="delivery-message"]'
            ]
            
            for selector in message_selectors:
                try:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                    delivery_message = element.text.strip()
                    if delivery_message:
                        break
                except:
                    continue

            # Get tracking details
            tracking_details = {}
            detail_selectors = [
                '.tracking-detail',
                '.tracking-info',
                '.tracking-history-item'
            ]
            
            for selector in detail_selectors:
                detail_sections = driver.find_elements(By.CSS_SELECTOR, selector)
                if detail_sections:
                    for section in detail_sections:
                        try:
                            label = section.find_element(By.CSS_SELECTOR, '[class$="-label"]').text.strip(':')
                            value = section.find_element(By.CSS_SELECTOR, 'span:last-child').text.strip()
                            tracking_details[label] = value
                        except:
                            continue
                    break

            response_data = {
                'status': status,
                'delivery_message': delivery_message,
                'tracking_details': tracking_details
            }

            # Take final screenshot
            print('Taking final screenshot')
            try:
                driver.save_screenshot('final_page.png')
            except Exception as screenshot_error:
                print(f'Final screenshot error: {screenshot_error}')

            return jsonify(response_data)

        except Exception as status_error:
            # Take error screenshot
            try:
                driver.save_screenshot('error_page.png')
            except:
                pass
                
            print(f'Status extraction error: {str(status_error)}')
            return jsonify({
                'error': 'Status Extraction Failed',
                'tracking_number': tracking_number,
                'details': 'Could not find or extract tracking status',
                'message': str(status_error)
            }), 404

    except Exception as e:
        print(f'Error occurred: {str(e)}')
        return jsonify({'error': str(e)}), 500

    finally:
        safe_quit(driver)

@app.route('/track_only_number', methods=['GET'])
def track_package_only_number():
    tracking_number = request.args.get('tracking_number')
    if not tracking_number:
        return jsonify({'error': 'Tracking number is required'}), 400

    max_retries = 3
    for retry_count in range(max_retries):
        driver = None
        try:
            if retry_count > 0:
                print(f'Retry attempt {retry_count} of {max_retries - 1}')
                time.sleep(5)  # Wait 5 seconds between retries

            driver = create_driver()
            print('Connected! Navigating...')
            url = f'https://www.royalmail.com/track-your-item#/tracking-results/{tracking_number}'
            driver.get(url)

            # Wait for page load
            driver.implicitly_wait(100)

            # Take screenshot before searching for elements
            print('Taking page screenshot')
            try:
                driver.save_screenshot(f'screenshot_attempt_{retry_count + 1}.png')
            except Exception as screenshot_error:
                print(f'Screenshot error: {screenshot_error}')

            summary_elements = driver.find_elements(By.CLASS_NAME, 'summary-line')
            date_pattern = re.compile(r'\b\d{2}-\d{2}-\d{4}\b')

            for element in summary_elements:
                text = element.text
                match = date_pattern.search(text)
                if match:
                    driver.save_screenshot(f'track_only_number_found_attempt_{retry_count + 1}.png')
                    return jsonify({
                        'delivery_date': match.group(),
                        'summary_elements': [elem.text for elem in summary_elements],
                        'attempt': retry_count + 1
                    })

        except Exception as e:
            print(f'Error occurred in attempt {retry_count + 1}: {str(e)}')
            if retry_count == max_retries - 1:  # Only return error on last attempt
                return jsonify({'error': str(e)}), 500

        finally:
            safe_quit(driver)

    # If we get here, we've exhausted all retries
    return jsonify({
        'message': f'Delivery date not found after {max_retries} attempts'
    }), 404

@app.route('/track_new', methods=['GET'])
def track_package_new():
    tracking_number = request.args.get('tracking_number')
    if not tracking_number:
        return jsonify({'error': 'Tracking number is required'}), 400

    max_retries = 3
    for retry_count in range(max_retries):
        driver = None
        try:
            if retry_count > 0:
                print(f'Retry attempt {retry_count} of {max_retries - 1}')
                time.sleep(5)  # Wait 5 seconds between retries

            driver = create_driver()
            print('Connected! Navigating...')
            url = f'https://www.royalmail.com/track-your-item#/tracking-results/{tracking_number}'
            driver.get(url)

            # Wait for page load
            driver.implicitly_wait(100)

            # Take screenshot before searching for elements
            print('Taking page screenshot')
            try:
                driver.save_screenshot(f'track_new_attempt_{retry_count + 1}.png')
            except Exception as screenshot_error:
                print(f'Screenshot error: {screenshot_error}')

            # Extract status
            status = driver.find_element(By.CSS_SELECTOR, '.status-description h2 strong').text
            print(f"Found status: {status}")

            # Extract delivery message
            delivery_message = driver.find_element(By.CSS_SELECTOR, '.estimated-delivery-message .summary-line div').text
            print(f"Found delivery message: {delivery_message}")

            # Extract tracking details
            tracking_details = {}
            detail_sections = driver.find_elements(By.CSS_SELECTOR, '.tracking-detail')
            
            if detail_sections:
                for section in detail_sections:
                    try:
                        label = section.find_element(By.CSS_SELECTOR, '[class$="-label"]').text.strip(':')
                        value = section.find_element(By.CSS_SELECTOR, 'span:last-child').text.strip()
                        tracking_details[label] = value
                    except:
                        continue

            print(f"Found tracking details: {tracking_details}")

            # Take success screenshot
            driver.save_screenshot(f'track_new_success_attempt_{retry_count + 1}.png')
            
            return jsonify({
                'status': status,
                'delivery_message': delivery_message,
                'tracking_details': tracking_details,
                'attempt': retry_count + 1
            })

        except Exception as e:
            print(f'Error occurred in attempt {retry_count + 1}: {str(e)}')
            try:
                driver.save_screenshot(f'track_new_error_attempt_{retry_count + 1}.png')
            except:
                pass
                
            if retry_count == max_retries - 1:  # Only return error on last attempt
                return jsonify({
                    'error': str(e),
                    'tracking_number': tracking_number
                }), 500

        finally:
            safe_quit(driver)

    # If we get here, we've exhausted all retries
    return jsonify({
        'message': f'Tracking information not found after {max_retries} attempts',
        'tracking_number': tracking_number
    }), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003)
