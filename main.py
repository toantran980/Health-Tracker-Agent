"""Main application entry point"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.routes import app

def main():
    """Run the application"""
    print("AI Health & Wellness Tracker")
    print("\nStarting Flask API server...")
    print("Server running at: http://localhost:5001")
    print("\nAvailable endpoints:")
    print("  POST   /api/user/create")
    print("  GET    /api/user/<user_id>")
    print("  GET    /api/health")
    print("  GET    /api/insights/<user_id>")
    print("  GET    /api/nutrition/analysis/<user_id>")
    print("  GET    /api/nutrition/recommendations/<user_id>")
    print("  GET    /api/schedule/available-slots/<user_id>")
    print("  POST   /api/schedule/optimize/<user_id>")
    print("  POST   /api/productivity/predict/<user_id>")
    print("  GET    /api/productivity/optimal-time/<user_id>")
    print("  POST   /api/recommendations/<user_id>")
    
    app.run(debug=True, host='0.0.0.0', port=5001)

if __name__ == '__main__':
    main()
