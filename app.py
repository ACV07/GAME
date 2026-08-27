import os
from flask import Flask, render_template
from config import Config
from database import init_db
from seed import seed_database

# Import blueprints
from routes.auth import auth_bp
from routes.challenges import challenges_bp
from routes.leaderboard import leaderboard_bp
from routes.admin import admin_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize Database Schema & Seed Data
    init_db()
    seed_database()

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(challenges_bp)
    app.register_blueprint(leaderboard_bp)
    app.register_blueprint(admin_bp)

    @app.context_processor
    def inject_global_vars():
        from models import EventConfigModel
        return {
            'round_status': EventConfigModel.get_round_status(),
            'global_announcement': EventConfigModel.get_announcement()
        }

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('base.html'), 404

    return app

app = create_app()

if __name__ == '__main__':
    print("⚡ Round 2 Challenge Arena starting on http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
