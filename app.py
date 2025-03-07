from flask import Flask, request, jsonify
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
from selenium import webdriver
from selenium_stealth import stealth


app = Flask(__name__)

# Test endpoint that doesn't require any external dependencies
@app.route('/test', methods=['GET'])
def test_endpoint():
    return jsonify({
        'message': 'API is working correctly'
    })



@app.route('/track', methods=['GET'])
def track_package():
    # Get the tracking number from the query parameters
    tracking_number = request.args.get('tracking_number')
    if not tracking_number:
        return jsonify({'error': 'Tracking number is required'}), 400

    # Initialize the undetected Chrome driver
    options = uc.ChromeOptions()
  
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.140 Safari/537.36"

   
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

             # Wait until the page is fully loaded
        driver.implicitly_wait(10)  # Adjust the wait time as needed

     

        # status = driver.find_element(By.CSS_SELECTOR, '.status-description h2 strong').text

        try:
            # Wait for status element to be present
            wait = WebDriverWait(driver, 10)
            status_element = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.status-description h2 strong'))
            )
            status = status_element.text
            if not status:
                raise ValueError("Status text is empty")
        except Exception as status_error:
            return jsonify({
                'error': 'Status Extraction Failed',
                'tracking_number': tracking_number,
                'details': 'Could not find or extract tracking status. It could be due to hCaptcha',
                'message': str(status_error)

            }), 404


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





@app.route('/track_only_number', methods=['GET'])
def track_package_only_number():
    # Get the tracking number from the query parameters
    tracking_number = request.args.get('tracking_number')
    if not tracking_number:
        return jsonify({'error': 'Tracking number is required'}), 400

    # Initialize the undetected Chrome driver
    options = uc.ChromeOptions()

    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.140 Safari/537.36"



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

        # Find all elements with the class 'summary-line'
        summary_elements = driver.find_elements(By.CLASS_NAME, 'summary-line')

        # Regular expression pattern to match dates in the format 'dd-mm-yyyy'
        date_pattern = re.compile(r'\b\d{2}-\d{2}-\d{4}\b')

        # Iterate over each element and extract the date
        for element in summary_elements:
            text = element.text
            match = date_pattern.search(text)
            if match:
                return jsonify({'delivery_date': match.group()})

        # Capture a screenshot
        driver.save_screenshot('screenshot.png')

        # # Retrieve and print the page source
        # page_source = driver.page_source
        # print(page_source)
        
        # If no date is found, return an appropriate message
        return jsonify({'message': 'Delivery date not found'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        # Close the browser
        driver.quit()



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=500)


