# Azure App Service startup script for production deployment
import os
import logging
from web_app import app

# Configure logging for production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # Get port from environment variable (Azure App Service sets this)
    port = int(os.environ.get('PORT', 8000))
    
    logger.info(f"Starting Azure Monitor Logs Agent on port {port}")
    
    # Production settings
    app.config['ENV'] = 'production'
    app.config['DEBUG'] = False
    app.config['TESTING'] = False
    
    # Run the Flask app
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        use_reloader=False
    )