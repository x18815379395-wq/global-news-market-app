import os
from dotenv import load_dotenv
load_dotenv()

from ears_of_fortune_v2 import app, DEEPSEEK_API_KEY, news_manager
import json

print('=== DEBUG INFO ===')
print(f'DEEPSEEK_API_KEY: {repr(DEEPSEEK_API_KEY)}')
example_deepseek_key = "sk-b72945444d894596bc8b881d553279b7"
print(f'DEEPSEEK_API_KEY is example value: {DEEPSEEK_API_KEY == example_deepseek_key}')

print('\n=== SCRAPER HEALTH ===')
health = news_manager.get_health_snapshot()
print(json.dumps(health, indent=2, ensure_ascii=False))

print('\n=== CONNECTIVITY TEST ===')
try:
    with app.app_context():
        from ears_of_fortune_v2 import api_connectivity_test
        result = api_connectivity_test()
        print(f'Result type: {type(result)}')
        
        # If it's a Flask Response object
        if hasattr(result, 'get_json'):
            json_data = result.get_json()
            print(f'JSON response: {json.dumps(json_data, indent=2)}')
        # If it returns a tuple (response, status)
        elif isinstance(result, tuple):
            response, status = result
            if hasattr(response, 'get_json'):
                json_data = response.get_json()
                print(f'Tuple response JSON: {json.dumps(json_data, indent=2)}, status: {status}')
            elif isinstance(response, dict):
                print(f'Tuple response: {json.dumps(response, indent=2)}, status: {status}')
            else:
                print(f'Tuple response: {response}, status: {status}')
        else:
            print(f'Other response type: {result}')
except Exception as e:
    print(f'Error calling api_connectivity_test: {e}')
    import traceback
    traceback.print_exc()
