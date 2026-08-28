from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
from models import TeamModel, SessionModel, ChallengeModel, SubmissionModel, EventConfigModel

challenges_bp = Blueprint('challenges', __name__)

def get_current_active_team():
    """Helper middleware checking active session validity."""
    token = session.get('session_token')
    if not token:
        return None, None
    sess_data = SessionModel.validate_session(token)
    if not sess_data:
        return None, None
    team = TeamModel.get_by_id(sess_data['team_id'])
    return sess_data, team

@challenges_bp.route('/challenge/<int:challenge_id>')
def view_challenge(challenge_id):
    """Renders the appropriate challenge page with strict server-side sequence enforcement."""
    sess_data, team = get_current_active_team()
    if not team:
        flash('Active session required. Please log in.', 'warning')
        return redirect(url_for('auth.login'))

    session['team_name'] = team['team_name']

    # If team has completed all challenges (current_challenge > 5), redirect to completion page
    if team['current_challenge'] > 5:
        return redirect(url_for('challenges.completed'))

    # Route Guard: Prevent teams from skipping ahead beyond unlocked challenges
    if challenge_id > team['current_challenge']:
        flash(f"Challenge {challenge_id} is locked. Complete Challenge {team['current_challenge']} first.", "warning")
        return redirect(url_for('challenges.view_challenge', challenge_id=team['current_challenge']))

    ch = ChallengeModel.get_by_id(challenge_id)
    if not ch:
        flash("Challenge not found.", "danger")
        return redirect(url_for('auth.lobby'))

    template_map = {
        'drag_drop': 'challenge_drag_drop.html',
        'error_line': 'challenge_error_line.html',
        'problem_solving': 'challenge_problem.html'
    }
    
    template_name = template_map.get(ch['type'], 'challenge_problem.html')
    draft = TeamModel.get_draft(team['id'])
    draft_payload = draft['draft'] if draft and draft.get('challenge_id') == challenge_id else None
    
    if not draft_payload:
        sub = SubmissionModel.get_team_submission(team['id'], challenge_id)
        if sub and sub.get('submitted_answer'):
            try:
                draft_payload = json.loads(sub['submitted_answer'])
            except Exception:
                draft_payload = sub['submitted_answer']

    is_read_only = False

    return render_template(template_name, challenge=ch, team=team, saved_draft=draft_payload, is_read_only=is_read_only)


@challenges_bp.route('/api/save-draft', methods=['POST'])
def save_draft():
    """Stores in-progress answers so pause/stop can restore the same board on resume."""
    sess_data, team = get_current_active_team()
    if not team:
        return jsonify({'success': False, 'message': 'Unauthorized or session expired.'}), 401

    data = request.get_json() or {}
    challenge_id = data.get('challenge_id')
    draft = data.get('draft')
    if not challenge_id:
        return jsonify({'success': False, 'message': 'Missing challenge id.'}), 400
    if int(challenge_id) > team['current_challenge']:
        return jsonify({'success': False, 'message': 'Draft does not match an unlocked challenge.'}), 403

    TeamModel.save_draft(team['id'], challenge_id, draft)
    return jsonify({'success': True})

@challenges_bp.route('/api/submit-challenge', methods=['POST'])
def submit_challenge():
    """Server-side endpoint to evaluate challenge answers and calculate scores."""
    sess_data, team = get_current_active_team()
    if not team:
        return jsonify({'success': False, 'message': 'Unauthorized or session expired.'}), 401

    # Round Status Check
    status = EventConfigModel.get_round_status()
    if status != 'ACTIVE':
        return jsonify({'success': False, 'stopped': True, 'message': 'GAME_STOPPED'}), 403

    data = request.get_json() or {}
    challenge_id = data.get('challenge_id')
    submitted_answer = data.get('answer')

    if not challenge_id or submitted_answer is None:
        return jsonify({'success': False, 'message': 'Missing submission data.'}), 400

    # Ensure team is submitting for an unlocked challenge
    if int(challenge_id) > team['current_challenge']:
        return jsonify({
            'success': False, 
            'message': f"Submission rejected. Challenge {challenge_id} is not unlocked."
        }), 403

    is_correct, points, explanation = ChallengeModel.evaluate_answer(challenge_id, submitted_answer)
    
    # Store/update submission record and update score/progress server-side
    SubmissionModel.record_submission(
        team_id=team['id'],
        challenge_id=int(challenge_id),
        submitted_answer=submitted_answer,
        is_correct=is_correct,
        points=points
    )

    # Re-fetch updated team info to check current_challenge
    _, updated_team = get_current_active_team()
    curr_active = updated_team['current_challenge'] if updated_team else team['current_challenge']

    if int(challenge_id) < curr_active:
        next_challenge = min(curr_active, int(challenge_id) + 1)
    else:
        next_challenge = int(challenge_id) + 1

    completed_all = (next_challenge > 5 or curr_active > 5)
    redirect_url = url_for('challenges.completed') if completed_all else url_for('challenges.view_challenge', challenge_id=next_challenge)

    return jsonify({
        'success': True,
        'is_correct': is_correct,
        'points_earned': points,
        'explanation': explanation,
        'next_challenge': next_challenge,
        'completed_all': completed_all,
        'redirect_url': redirect_url,
        'message': "Submitted. Advancing to next challenge..."
    })

@challenges_bp.route('/api/skip-challenge', methods=['POST'])
def skip_challenge():
    """Endpoint allowing contestants to skip an unlocked challenge (0 points)."""
    sess_data, team = get_current_active_team()
    if not team:
        return jsonify({'success': False, 'message': 'Unauthorized or session expired.'}), 401

    status = EventConfigModel.get_round_status()
    if status != 'ACTIVE':
        return jsonify({'success': False, 'stopped': True, 'message': 'GAME_STOPPED'}), 403

    data = request.get_json() or {}
    challenge_id = data.get('challenge_id')

    if not challenge_id:
        return jsonify({'success': False, 'message': 'Missing challenge id.'}), 400

    if int(challenge_id) > team['current_challenge']:
        return jsonify({
            'success': False,
            'message': f"Skip rejected. Challenge {challenge_id} is not unlocked."
        }), 403

    # Record submission log for audit
    SubmissionModel.record_submission(
        team_id=team['id'],
        challenge_id=int(challenge_id),
        submitted_answer='[SKIPPED]',
        is_correct=False,
        points=0
    )

    _, updated_team = get_current_active_team()
    curr_active = updated_team['current_challenge'] if updated_team else team['current_challenge']

    if int(challenge_id) < curr_active:
        next_challenge = min(curr_active, int(challenge_id) + 1)
    else:
        next_challenge = int(challenge_id) + 1

    completed_all = (next_challenge > 5 or curr_active > 5)
    redirect_url = url_for('challenges.completed') if completed_all else url_for('challenges.view_challenge', challenge_id=next_challenge)

    return jsonify({
        'success': True,
        'message': f"Challenge {challenge_id} skipped.",
        'next_challenge': next_challenge,
        'completed_all': completed_all,
        'redirect_url': redirect_url
    })

@challenges_bp.route('/completed')
def completed():
    """Renders final result and victory screen."""
    sess_data, team = get_current_active_team()
    if not team:
        flash('Session expired.', 'warning')
        return redirect(url_for('auth.login'))

    if team['current_challenge'] <= 5:
        return redirect(url_for('challenges.view_challenge', challenge_id=team['current_challenge']))

    submissions = SubmissionModel.get_team_submissions(team['id'])
    
    # Calculate formatted time
    sec = team.get('total_time_seconds', 0)
    minutes = sec // 60
    seconds = sec % 60
    formatted_time = f"{minutes:02d}:{seconds:02d}"

    return render_template('completed.html', team=team, submissions=submissions, formatted_time=formatted_time)
