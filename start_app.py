import os

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    dotenv_path = os.getenv('EARSOFFORTUNE_DOTENV', '.env')
    load_dotenv(dotenv_path)

from app import app

if __name__ == '__main__':
    # Set default host and port
    host = os.getenv('HOST', '127.0.0.1')
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    print(f"Starting HorizonScanner on {host}:{port}")
    print("API Status Check:")
    
    # Load environment variables and check API keys (without hardcoded sample comparisons)
    from app import DEEPSEEK_API_KEY
    deepseek_configured = bool(DEEPSEEK_API_KEY) and 'YOUR_' not in str(DEEPSEEK_API_KEY)
    
    print(f"  DeepSeek configured: {deepseek_configured}")
    
    if not deepseek_configured:
        print("\n[WARN] DeepSeek key missing; downstream analysis features will use fallbacks.")
    
    print(f"\nAccess URL: http://{host}:{port}")
    print("Frontend will show 'Loading news data' and connection status")
    
    app.run(host=host, port=port, debug=debug, threaded=True)
