import os

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    dotenv_path = os.getenv('EARSOFFORTUNE_DOTENV', '.env')
    load_dotenv(dotenv_path)

from ears_of_fortune_v2 import app

if __name__ == '__main__':
    # Set default host and port
    host = os.getenv('HOST', '127.0.0.1')
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    print(f"Starting HorizonScanner on {host}:{port}")
    print("API Status Check:")
    
    # Load environment variables and check API keys (without hardcoded sample comparisons)
    from ears_of_fortune_v2 import DEEPSEEK_API_KEY, get_no_api_health_snapshot, news_manager
    deepseek_configured = bool(DEEPSEEK_API_KEY) and 'YOUR_' not in str(DEEPSEEK_API_KEY)
    scraper_health = news_manager.get_health_snapshot()
    doctor_health = get_no_api_health_snapshot(force_refresh=True)
    
    print(f"  DeepSeek configured: {deepseek_configured}")
    print(f"  RSS sources: {scraper_health.get('rss', {})}")
    print(f"  Truth Social: {scraper_health.get('truth_social', {})}")
    twitter_state = scraper_health.get('twitter', {})
    print(f"  Twitter scraper handles: {twitter_state}")
    if doctor_health:
        print("  No-API Doctor Snapshot:")
        print(f"    RSS sources: {doctor_health.get('rss')}")
        print(f"    Truth Social: {doctor_health.get('truth')}")
        print(f"    Twitter scraper ready: {doctor_health.get('twitter_ready')}")
    
    if not deepseek_configured:
        print("\n[WARN] DeepSeek key missing; downstream analysis features will use fallbacks.")
    
    print(f"\nAccess URL: http://{host}:{port}")
    print("Frontend will show 'Loading news data' and connection status")
    
    app.run(host=host, port=port, debug=debug, threaded=True)
