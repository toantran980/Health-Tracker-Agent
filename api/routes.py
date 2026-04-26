"""
routes.py

App factory — creates the Flask app and registers all domain blueprints.
Route logic lives in api/blueprints/<domain>.py.
"""

import os
from flask import Flask, render_template


from api.blueprints.user import user_bp
from api.blueprints.nutrition import nutrition_bp
from api.blueprints.schedule import schedule_bp
from api.blueprints.chat import chat_bp
from api.blueprints.external import external_bp
from api.blueprints.health import health_bp
from api.blueprints.metrics import metrics_bp

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static'),
    static_url_path='/static',
)

for bp in (user_bp, nutrition_bp, schedule_bp, chat_bp, external_bp, health_bp, metrics_bp):
    app.register_blueprint(bp)


@app.route('/', methods=['GET'])
def index():
    """Serve the single-page frontend application."""
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
