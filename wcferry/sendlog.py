import requests

def run(log_message):
    # url = 'http://localhost:5000/add_log'
    # data = {
    #     'log_message': log_message
    # }
    # try:
    #     response = requests.post(url, data=data)
    #     response.raise_for_status()
    #     result = response.json()
    #     if result['status'] == 'success':
    #         print(f"Log added successfully: {result['log']}")
    #     else:
    #         print(f"Failed to add log: {result['error']}")
    # except requests.exceptions.RequestException as e:
    #     print(f"Failed to communicate with Flask service: {e}")
    print(log_message)