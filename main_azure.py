import os
from web_app import app

if __name__ == "__main__":
    # Get port from environment variable or default to 8000 for Azure App Service
    port = int(os.environ.get('PORT', 8000))
    
    # Run the Flask app
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False  # Disable debug mode in production
    )