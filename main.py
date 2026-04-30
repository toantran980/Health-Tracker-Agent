"""Main application entry point"""
import sys
import os
import logging
from flask import Flask

from api.routes import app

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Run the application"""
    logger.info("Starting AI Health & Wellness Tracker")
    logger.info("Initializing Flask API server...")

    port = int(os.environ.get('PORT', 5001))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = os.environ.get('DEBUG', 'True').lower() == 'true'

    logger.info(f"Server will run at: http://{host}:{port}")
    logger.info("Available endpoints:")
    logger.info("  POST   /api/user/create")
    logger.info("  GET    /api/user/<user_id>")
    logger.info("  GET    /api/health")
    logger.info("  GET    /api/insights/<user_id>")
    logger.info("  GET    /api/nutrition/analysis/<user_id>")
    logger.info("  GET    /api/nutrition/recommendations/<user_id>")
    logger.info("  GET    /api/schedule/available-slots/<user_id>")
    logger.info("  POST   /api/schedule/optimize/<user_id>")
    logger.info("  POST   /api/productivity/predict/<user_id>")
    logger.info("  GET    /api/productivity/optimal-time/<user_id>")
    logger.info("  POST   /api/recommendations/<user_id>")

    try:
        app.run(debug=debug, host=host, port=port)
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
