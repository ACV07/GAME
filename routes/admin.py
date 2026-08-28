from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
from models import TeamModel, SessionModel, SubmissionModel, LeaderboardModel, EventConfigModel
from database import get_db_connection

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    """Decorator to enforce admin authentication."""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            flash('Organizer admin authentication required.', 'danger')
            return redirect(url_for('auth.admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/admin')
@admin_required
def dashboard():
    """Renders organizer control room and live team monitor."""
    SessionModel.clean_expired_sessions()
    teams = LeaderboardModel.get_rankings()
    rankings = teams
    round_status = EventConfigModel.get_round_status()
    announcement = EventConfigModel.get_announcement()
    timer_info = EventConfigModel.get_timer_info()
    return render_template('admin.html', teams=teams, rankings=rankings, round_status=round_status, announcement=announcement, timer_info=timer_info)

@admin_bp.route('/admin/control-center')
@admin_required
def control_center():
    """Dedicated Master Event Control Center web page for Round 2 Organizers."""
    SessionModel.clean_expired_sessions()
    teams = LeaderboardModel.get_rankings()
    rankings = teams
    round_status = EventConfigModel.get_round_status()
    announcement = EventConfigModel.get_announcement()
    recent_activity = EventConfigModel.get_recent_activity(limit=15)
    timer_info = EventConfigModel.get_timer_info()
    return render_template('admin_control.html', teams=teams, rankings=rankings, round_status=round_status, announcement=announcement, recent_activity=recent_activity, timer_info=timer_info)

@admin_bp.route('/api/admin/set-timer-duration', methods=['POST'])
@admin_required
def set_timer_duration():
    """Admin endpoint to set round duration in minutes and start countdown."""
    data = request.get_json() or {}
    try:
        minutes = int(data.get('minutes', 30))
        if minutes <= 0:
            return jsonify({'success': False, 'message': 'Duration must be greater than 0 minutes.'}), 400
        
        end_epoch = EventConfigModel.start_timer_with_duration(minutes)
        # Also ensure round is set to ACTIVE when timer starts
        EventConfigModel.set_round_status('ACTIVE')
        timer_info = EventConfigModel.get_timer_info()
        return jsonify({'success': True, 'message': f'Master timer set to {minutes} minutes.', 'timer_info': timer_info, 'round_status': 'ACTIVE'})
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Invalid minutes value.'}), 400

@admin_bp.route('/api/admin/set-round-status', methods=['POST'])
@admin_required
def set_round_status():
    """Controls the global round state: ACTIVE, PAUSED, STOPPED, NOT_STARTED, ENDED."""
    data = request.get_json() or {}
    status = data.get('status', '').upper()
    if status not in ['ACTIVE', 'PAUSED', 'STOPPED', 'NOT_STARTED', 'ENDED']:
        return jsonify({'success': False, 'message': 'Invalid status value.'}), 400

    EventConfigModel.set_round_status(status)
    return jsonify({'success': True, 'message': f'Round status set to {status}.', 'round_status': status})

@admin_bp.route('/api/admin/broadcast-announcement', methods=['POST'])
@admin_required
def broadcast_announcement():
    """Posts a global live announcement message to all contestant screens."""
    data = request.get_json() or {}
    msg = data.get('announcement', '').strip()
    EventConfigModel.set_announcement(msg)
    return jsonify({'success': True, 'message': 'Announcement updated.', 'announcement': msg})

@admin_bp.route('/api/admin/unlock-all-teams', methods=['POST'])
@admin_required
def unlock_all_teams():
    """Force unlocks all active device locks across all teams."""
    conn = get_db_connection()
    conn.execute("UPDATE sessions SET is_active = 0")
    conn.execute("UPDATE teams SET status = 'WAITING' WHERE status = 'ACTIVE'")
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'All team sessions unlocked successfully.'})

@admin_bp.route('/api/admin/unlock-team', methods=['POST'])
@admin_required
def unlock_team():
    """Force unlocks an active session lock for a specific team."""
    data = request.get_json() or {}
    team_id = data.get('team_id')
    if not team_id:
        return jsonify({'success': False, 'message': 'Missing team ID.'}), 400

    SessionModel.force_unlock_team(team_id)
    return jsonify({'success': True, 'message': 'Team session unlocked successfully.'})

@admin_bp.route('/api/admin/reset-team', methods=['POST'])
@admin_required
def reset_team():
    """Resets a team progress, score, and timer back to initial state."""
    data = request.get_json() or {}
    team_id = data.get('team_id')
    if not team_id:
        return jsonify({'success': False, 'message': 'Missing team ID.'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE teams 
        SET current_challenge = 1,
            total_score = 0,
            start_time = NULL,
            completion_time = NULL,
            total_time_seconds = 0,
            status = 'WAITING',
            draft_json = ''
        WHERE id = ?
    """, (team_id,))
    cursor.execute("DELETE FROM submissions WHERE team_id = ?", (team_id,))
    cursor.execute("UPDATE sessions SET is_active = 0 WHERE team_id = ?", (team_id,))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': 'Team progress reset to Challenge 1.'})

@admin_bp.route('/api/admin/reset-entire-game', methods=['POST'])
@admin_required
def reset_entire_game():
    """Resets ALL teams back to Challenge 1, clears all submissions and timer state."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE teams 
        SET current_challenge = 1,
            total_score = 0,
            start_time = NULL,
            completion_time = NULL,
            total_time_seconds = 0,
            status = 'WAITING',
            draft_json = ''
    """)
    cursor.execute("DELETE FROM submissions")
    cursor.execute("UPDATE sessions SET is_active = 0")
    conn.commit()
    conn.close()

    # Reset round status and master timer
    EventConfigModel.set_round_status('NOT_STARTED')
    EventConfigModel.set_config('master_timer_end', '')
    EventConfigModel.set_config('master_timer_remaining', '')
    EventConfigModel.set_config('pause_started_at', '')
    EventConfigModel.set_config('total_paused_seconds', '0')

    return jsonify({'success': True, 'message': '🚨 Entire Game Reset! All teams are back to Challenge 1.'})

@admin_bp.route('/api/admin/add-team', methods=['POST'])
@admin_required
def add_team():
    """Dynamically adds a new team."""
    team_name = request.form.get('team_name', '').strip()
    team_code = request.form.get('team_code', '').strip()

    if not team_name:
        flash('Team Name is required.', 'warning')
        return redirect(url_for('admin.dashboard'))

    try:
        if not team_code:
            TeamModel.get_or_create_by_name(team_name)
        else:
            TeamModel.create_team(team_code, team_name)
        flash(f'Team "{team_name}" registered successfully.', 'success')
    except Exception as e:
        flash(f'Error registering team: {str(e)}', 'danger')

    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/api/admin/team-submissions/<int:team_id>')
@admin_required
def team_submissions(team_id):
    """Returns submission audit history for a team."""
    submissions = SubmissionModel.get_team_submissions(team_id)
    return jsonify({'submissions': submissions})

@admin_bp.route('/api/admin/live-activity')
@admin_required
def live_activity():
    """Returns recent submission activity feed."""
    activity = EventConfigModel.get_recent_activity(limit=20)
    return jsonify({'activity': activity})

@admin_bp.route('/api/admin/delete-team/<int:team_id>', methods=['POST'])
@admin_required
def delete_team_api(team_id):
    """Deletes a team permanently from DB (Admin only)."""
    team = TeamModel.get_by_id(team_id)
    if not team:
        return jsonify({'success': False, 'message': 'Team not found.'}), 404
        
    team_name = team['team_name']
    TeamModel.delete_team(team_id)
    return jsonify({'success': True, 'message': f'Team "{team_name}" deleted from database successfully.'})

@admin_bp.route('/api/event-status')
def public_event_status():
    """Public endpoint polled by contestant pages to check round status, announcements, and master countdown timer."""
    status = EventConfigModel.get_round_status()
    announcement = EventConfigModel.get_announcement()
    timer_info = EventConfigModel.get_timer_info()
    
    # Auto-end round if master timer has expired
    if timer_info.get('is_expired') and status == 'ACTIVE':
        EventConfigModel.set_round_status('ENDED')
        status = 'ENDED'

    return jsonify({
        'round_status': status,
        'announcement': announcement,
        'timer_info': timer_info
    })
