from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
from models import TeamModel, SessionModel
from config import Config

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def login():
    """Renders the login page for teams and organizers."""
    # If already logged in with active session, redirect to lobby
    token = session.get('session_token')
    if token:
        sess_data = SessionModel.validate_session(token)
        if sess_data:
            return redirect(url_for('auth.lobby'))
            
    return render_template('login.html')

@auth_bp.route('/login', methods=['POST'])
def team_login():
    """Handles team registration by name or re-login with Team Code/Name."""
    identifier = request.form.get('team_identifier', '').strip() or request.form.get('team_code', '').strip()
    if not identifier:
        flash('Please enter a Team Name or Unique Team Code.', 'danger')
        return redirect(url_for('auth.login'))

    # 1. First check if identifier is an existing Team Code
    team = TeamModel.get_by_code(identifier)
    is_new = False
    
    # 2. If not a code, get or create team by Team Name automatically
    if not team:
        team, is_new = TeamModel.get_or_create_by_name(identifier)

    user_agent = request.headers.get('User-Agent', 'Browser Client')
    session_token, err = SessionModel.create_session(team['id'], device_info=user_agent)
    
    if err:
        flash(err, 'warning')
        return redirect(url_for('auth.login'))

    # Store session token in browser cookie session
    session['session_token'] = session_token
    session['team_id'] = team['id']
    session['team_name'] = team['team_name']

    if is_new:
        flash(f"🎉 Team registered successfully! Your Unique Passcode is: {team['team_code']}. Save this code to log back in if needed!", "success")

    return redirect(url_for('auth.lobby'))

@auth_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Handles dedicated organizer admin login."""
    if session.get('is_admin'):
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        admin_id = request.form.get('admin_id', '').strip()
        password = request.form.get('password', '').strip()
        
        if admin_id == Config.ADMIN_USERNAME and password == Config.ADMIN_PASSWORD:
            session['is_admin'] = True
            flash('Admin authentication successful.', 'success')
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Invalid Admin ID or Password.', 'danger')
            return redirect(url_for('auth.admin_login'))

    return render_template('admin_login.html')

from models import TeamModel, SessionModel, EventConfigModel

@auth_bp.route('/lobby')
def lobby():
    """Renders team briefing lobby."""
    token = session.get('session_token')
    sess_data = SessionModel.validate_session(token)
    if not sess_data:
        flash('Session expired or inactive on another device.', 'warning')
        session.clear()
        return redirect(url_for('auth.login'))

    team = TeamModel.get_by_id(sess_data['team_id'])
    round_status = EventConfigModel.get_round_status()
    timer_info = EventConfigModel.get_timer_info()
    return render_template('lobby.html', team=team, session_data=sess_data, round_status=round_status, timer_info=timer_info)

@auth_bp.route('/api/heartbeat', methods=['POST'])
def heartbeat():
    """API endpoint pinged by client JS to maintain active session lock."""
    token = session.get('session_token')
    if not token:
        return jsonify({'status': 'error', 'active': False, 'message': 'No session token found.'}), 401
        
    updated = SessionModel.update_heartbeat(token)
    if updated:
        return jsonify({'status': 'ok', 'active': True})
    else:
        session.clear()
        return jsonify({'status': 'expired', 'active': False, 'message': 'Session expired or overridden.'}), 403

@auth_bp.route('/logout', methods=['POST', 'GET'])
def logout():
    """Logs out the team and frees the active session lock."""
    token = session.get('session_token')
    if token:
        SessionModel.terminate_session(token)
    session.clear()
    flash('Logged out successfully. Session unlocked.', 'info')
    return redirect(url_for('auth.login'))
