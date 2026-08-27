from flask import Blueprint, render_template, jsonify, session, redirect, url_for, flash
from models import LeaderboardModel
from routes.admin import admin_required

leaderboard_bp = Blueprint('leaderboard', __name__)

@leaderboard_bp.route('/leaderboard')
@admin_required
def view_leaderboard():
    """Renders the live leaderboard page (Admin Access Only)."""
    rankings = LeaderboardModel.get_rankings()
    return render_template('leaderboard.html', rankings=rankings)

@leaderboard_bp.route('/api/leaderboard')
@admin_required
def api_leaderboard():
    """JSON endpoint for live leaderboard auto-polling (Admin Access Only)."""
    rankings = LeaderboardModel.get_rankings()
    return jsonify({'rankings': rankings})
