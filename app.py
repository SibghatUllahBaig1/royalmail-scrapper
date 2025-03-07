from flask import Flask, request, jsonify
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
from selenium import webdriver
from selenium_stealth import stealth


app = Flask(__name__)

@app.route('/track', methods=['GET'])
def track_package():
    # Get the tracking number from the query parameters
    tracking_number = request.args.get('tracking_number')
    if not tracking_number:
        return jsonify({'error': 'Tracking number is required'}), 400

    # Initialize the undetected Chrome driver
    options = uc.ChromeOptions()
    # options.add_argument('--headless')  # Run in headless mode
    # options.add_argument('--headless=new')  # Enable the new headless mode
    # options.add_argument('--window-size=1920,1080')  # Set a standard window size
    # options.add_argument('--disable-gpu')  # Disabl9e GPU acceleration
    # options.add_argument('--no-sandbox')  # Bypass OS security model
    # options.add_argument('--disable-dev-shm-usage')  # Overcome limited resource problems
    # options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.140 Safari/537.36"

    # options.add_argument('--headless=new')
    # options.add_argument("--start-maximized")
    # options.add_argument("user-agent={}".format(user_agent))
    # options.add_experimental_option("excludeSwitches", ["enable-automation"])
    # options.add_experimental_option('useAutomationExtension', False)

    driver = uc.Chrome(options=options)

    # driver = uc.Chrome(headless=True,use_subprocess=False,)


    stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
        )
    
    # stealth(driver,
    #     user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.53 Safari/537.36',
    #     languages=["en-US", "en"],
    #     vendor="Google Inc.",
    #     platform="Win32",
    #     webgl_vendor="Intel Inc.",
    #     renderer="Intel Iris OpenGL Engine",
    #     fix_hairline=False,
    #     run_on_insecure_origins=False
    #     )

    


    try:
        # Navigate to the Royal Mail tracking page with the provided tracking number

        
        url = f'https://www.royalmail.com/track-your-item#/tracking-results/{tracking_number}'
        driver.get(url)

        # # Wait until the element with class 'summary-line' is present

        # WebDriverWait(driver, 10).until(
        #     EC.presence_of_all_elements_located((By.CLASS_NAME, 'estimated-delivery-message'))
        # )

                # Wait until the page is fully loaded
        driver.implicitly_wait(10)  # Adjust the wait time as needed

        # # Find all elements with the class 'summary-line'
        # summary_elements = driver.find_elements(By.CLASS_NAME, 'summary-line')

        # # Regular expression pattern to match dates in the format 'dd-mm-yyyy'
        # date_pattern = re.compile(r'\b\d{2}-\d{2}-\d{4}\b')

        # # Iterate over each element and extract the date
        # for element in summary_elements:
        #     text = element.text
        #     match = date_pattern.search(text)
        #     if match:
        #         return jsonify({'delivery_date': match.group()})

        status = driver.find_element(By.CSS_SELECTOR, '.status-description h2 strong').text


        # Extract delivery message
        delivery_message = driver.find_element(By.CSS_SELECTOR, '.estimated-delivery-message .summary-line div').text

        # Extract tracking details
        tracking_details = {}
        detail_sections = driver.find_elements(By.CSS_SELECTOR, '.tracking-detail')
        
        if not detail_sections:
            return jsonify({
                'error': 'Not Found',
                'message': 'No tracking details available',
                'tracking_number': tracking_number
            }), 404

        for section in detail_sections:
            try:
                label = section.find_element(By.CSS_SELECTOR, '[class$="-label"]').text.strip(':')
                value = section.find_element(By.CSS_SELECTOR, 'span:last-child').text
                tracking_details[label] = value
            except:
                continue

        # Construct response JSON
        response_data = {
            'status': status,
            'delivery_message': delivery_message,
            'tracking_details': tracking_details
        }


        # Capture a screenshot
        driver.save_screenshot('screenshot.png')

        # # Retrieve and print the page source
        # page_source = driver.page_source
        # print(page_source)
        
        return jsonify(response_data)


    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        # Close the browser
        driver.quit()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)
