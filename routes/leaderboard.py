from flask import Blueprint, render_template, jsonify, session, redirect, url_for, flash, request
from models import LeaderboardModel
from routes.admin import admin_required

leaderboard_bp = Blueprint('leaderboard', __name__)

@leaderboard_bp.route('/leaderboard')
@admin_required
def view_leaderboard():
    """Renders the live leaderboard page (Admin Access Only)."""
    sort_by = request.args.get('sort', 'points')
    if sort_by not in ['points', 'time']:
        sort_by = 'points'
    rankings = LeaderboardModel.get_rankings(sort_by=sort_by)
    return render_template('leaderboard.html', rankings=rankings, active_sort=sort_by)

@leaderboard_bp.route('/api/leaderboard')
@admin_required
def api_leaderboard():
    """JSON endpoint for live leaderboard auto-polling (Admin Access Only)."""
    sort_by = request.args.get('sort', 'points')
    if sort_by not in ['points', 'time']:
        sort_by = 'points'
    rankings = LeaderboardModel.get_rankings(sort_by=sort_by)
    return jsonify({'rankings': rankings, 'active_sort': sort_by})
