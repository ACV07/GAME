import json
import uuid
from datetime import datetime, timezone
from database import get_db_connection
from config import Config

class EventConfigModel:
    @staticmethod
    def get_config(key, default_value=''):
        conn = get_db_connection()
        row = conn.execute("SELECT value FROM event_config WHERE key = ?", (key,)).fetchone()
        conn.close()
        return row['value'] if row else default_value

    @staticmethod
    def set_config(key, value):
        conn = get_db_connection()
        conn.execute("INSERT OR REPLACE INTO event_config (key, value) VALUES (?, ?)", (key, str(value)))
        conn.commit()
        conn.close()

    @staticmethod
    def get_round_status():
        return EventConfigModel.get_config('round_status', 'NOT_STARTED')

    FROZEN_STATUSES = ('PAUSED', 'STOPPED')

    @staticmethod
    def get_pause_seconds():
        """Wall-clock seconds the round has been paused or stopped (excluded from play time)."""
        import time
        total_raw = EventConfigModel.get_config('total_paused_seconds', '0')
        total_sec = int(total_raw) if str(total_raw).isdigit() else 0
        started = EventConfigModel.get_config('pause_started_at', '')
        status = EventConfigModel.get_round_status()
        if status in EventConfigModel.FROZEN_STATUSES and str(started).isdigit():
            total_sec += max(0, int(time.time()) - int(started))
        return total_sec

    @staticmethod
    def set_round_status(status):
        import time
        old_status = EventConfigModel.get_round_status()
        now = int(time.time())
        frozen = EventConfigModel.FROZEN_STATUSES

        if status == 'ACTIVE' and old_status != 'ACTIVE':
            if old_status in frozen:
                started = EventConfigModel.get_config('pause_started_at', '')
                if str(started).isdigit():
                    extra = max(0, now - int(started))
                    prev = EventConfigModel.get_config('total_paused_seconds', '0')
                    prev_i = int(prev) if str(prev).isdigit() else 0
                    EventConfigModel.set_config('total_paused_seconds', str(prev_i + extra))
                EventConfigModel.set_config('pause_started_at', '')

            rem_str = EventConfigModel.get_config('master_timer_remaining', '')
            if rem_str and rem_str.isdigit() and int(rem_str) > 0:
                rem_sec = int(rem_str)
                end_epoch = now + rem_sec
                EventConfigModel.set_config('master_timer_end', str(end_epoch))
                EventConfigModel.set_config('master_timer_remaining', '')
            else:
                end_str = EventConfigModel.get_config('master_timer_end', '')
                if not end_str or not end_str.isdigit() or int(end_str) <= now:
                    dur = EventConfigModel.get_config('master_timer_duration', '30')
                    dur_min = int(dur) if dur.isdigit() else 30
                    end_epoch = now + dur_min * 60
                    EventConfigModel.set_config('master_timer_end', str(end_epoch))
                    EventConfigModel.set_config('master_timer_remaining', '')

        elif status in frozen:
            if old_status == 'ACTIVE':
                end_str = EventConfigModel.get_config('master_timer_end', '')
                if end_str and end_str.isdigit():
                    rem_sec = max(0, int(end_str) - now)
                    EventConfigModel.set_config('master_timer_remaining', str(rem_sec))
                EventConfigModel.set_config('pause_started_at', str(now))
            elif old_status not in frozen:
                EventConfigModel.set_config('pause_started_at', str(now))

        elif status == 'NOT_STARTED':
            EventConfigModel.set_config('master_timer_end', '')
            EventConfigModel.set_config('master_timer_remaining', '')
            EventConfigModel.set_config('pause_started_at', '')
            EventConfigModel.set_config('total_paused_seconds', '0')

        EventConfigModel.set_config('round_status', status)

    @staticmethod
    def get_announcement():
        return EventConfigModel.get_config('global_announcement', '')

    @staticmethod
    def set_announcement(msg):
        EventConfigModel.set_config('global_announcement', msg)

    @staticmethod
    def start_timer_with_duration(minutes):
        """Sets round end timestamp based on specified minutes duration and starts round."""
        import time
        now = int(time.time())
        end_epoch = now + int(minutes) * 60
        EventConfigModel.set_config('master_timer_end', str(end_epoch))
        EventConfigModel.set_config('master_timer_duration', str(minutes))
        EventConfigModel.set_config('master_timer_remaining', '')
        EventConfigModel.set_config('round_status', 'ACTIVE')
        return end_epoch

    @staticmethod
    def get_timer_info():
        """Returns comprehensive timer info for client clocks."""
        import time
        status = EventConfigModel.get_round_status()
        end_str = EventConfigModel.get_config('master_timer_end', '')
        rem_str = EventConfigModel.get_config('master_timer_remaining', '')
        duration_str = EventConfigModel.get_config('master_timer_duration', '30')
        dur_min = int(duration_str) if duration_str.isdigit() else 30
        now = int(time.time())

        remaining = 0
        has_timer = False
        is_expired = False
        end_epoch = 0

        if status in EventConfigModel.FROZEN_STATUSES and rem_str and rem_str.isdigit():
            remaining = int(rem_str)
            has_timer = True
        elif end_str and end_str.isdigit():
            end_epoch = int(end_str)
            remaining = max(0, end_epoch - now)
            has_timer = True
            is_expired = (remaining <= 0 and status == 'ACTIVE')
        elif status == 'NOT_STARTED':
            remaining = dur_min * 60
            has_timer = True

        return {
            'has_timer': has_timer,
            'round_status': status,
            'end_epoch': end_epoch,
            'remaining_seconds': remaining,
            'duration_minutes': dur_min,
            'is_expired': is_expired
        }

    @staticmethod
    def get_recent_activity(limit=15):
        conn = get_db_connection()
        rows = conn.execute("""
            SELECT s.*, t.team_name, c.title AS challenge_title
            FROM submissions s
            JOIN teams t ON s.team_id = t.id
            JOIN challenges c ON s.challenge_id = c.id
            ORDER BY s.submission_time DESC
            LIMIT ?
        """, (limit,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]
class TeamModel:
    @staticmethod
    def get_by_code(team_code):
        conn = get_db_connection()
        team = conn.execute("SELECT * FROM teams WHERE LOWER(team_code) = LOWER(?)", (team_code.strip(),)).fetchone()
        conn.close()
        return dict(team) if team else None

    @staticmethod
    def get_by_name(team_name):
        conn = get_db_connection()
        team = conn.execute("SELECT * FROM teams WHERE LOWER(team_name) = LOWER(?)", (team_name.strip(),)).fetchone()
        conn.close()
        return dict(team) if team else None

    @staticmethod
    def get_by_id(team_id):
        conn = get_db_connection()
        team = conn.execute("SELECT * FROM teams WHERE id = ?", (team_id,)).fetchone()
        conn.close()
        return dict(team) if team else None

    @staticmethod
    def get_all():
        conn = get_db_connection()
        teams = conn.execute("SELECT * FROM teams ORDER BY id ASC").fetchall()
        conn.close()
        return [dict(t) for t in teams]

    @staticmethod
    def create_team(team_code, team_name):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO teams (team_code, team_name) VALUES (?, ?)",
            (team_code.strip().upper(), team_name.strip())
        )
        team_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return team_id

    @staticmethod
    def generate_random_team_code(team_name):
        """Generates a random unique team code e.g. CW-8492."""
        import random
        import string
        
        # Build prefix from initials or name
        words = team_name.strip().split()
        if len(words) >= 2:
            prefix = (words[0][0] + words[1][0]).upper()
        elif len(words[0]) >= 2:
            prefix = words[0][:2].upper()
        else:
            prefix = "TEAM"
            
        conn = get_db_connection()
        while True:
            suffix = ''.join(random.choices(string.digits + string.ascii_uppercase, k=4))
            code = f"{prefix}-{suffix}"
            existing = conn.execute("SELECT id FROM teams WHERE team_code = ?", (code,)).fetchone()
            if not existing:
                conn.close()
                return code

    @staticmethod
    def get_or_create_by_name(team_name):
        """Finds existing team by name, or automatically creates it with a random unique code."""
        clean_name = team_name.strip()
        conn = get_db_connection()
        existing = conn.execute("SELECT * FROM teams WHERE LOWER(team_name) = LOWER(?)", (clean_name,)).fetchone()
        conn.close()
        
        if existing:
            return dict(existing), False # existing team, not newly created
            
        # Create new team with random unique code
        code = TeamModel.generate_random_team_code(clean_name)
        team_id = TeamModel.create_team(code, clean_name)
        new_team = TeamModel.get_by_id(team_id)
        return new_team, True # newly created

    @staticmethod
    def save_draft(team_id, challenge_id, draft):
        payload = json.dumps({'challenge_id': int(challenge_id), 'draft': draft})
        conn = get_db_connection()
        conn.execute("UPDATE teams SET draft_json = ? WHERE id = ?", (payload, team_id))
        conn.commit()
        conn.close()

    @staticmethod
    def get_draft(team_id):
        conn = get_db_connection()
        row = conn.execute("SELECT draft_json FROM teams WHERE id = ?", (team_id,)).fetchone()
        conn.close()
        raw = (row['draft_json'] if row else '') or ''
        if not raw:
            return None
        try:
            return json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return None

    @staticmethod
    def clear_draft(team_id):
        conn = get_db_connection()
        conn.execute("UPDATE teams SET draft_json = '' WHERE id = ?", (team_id,))
        conn.commit()
        conn.close()


class SessionModel:
    @staticmethod
    def clean_expired_sessions():
        """Marks sessions inactive if last_seen is older than Config.HEARTBEAT_TIMEOUT seconds."""
        conn = get_db_connection()
        cursor = conn.cursor()
        # Find sessions silent for longer than HEARTBEAT_TIMEOUT seconds
        cursor.execute("""
            UPDATE sessions 
            SET is_active = 0 
            WHERE is_active = 1 
            AND (strftime('%s', 'now') - strftime('%s', last_seen)) > ?
        """, (Config.HEARTBEAT_TIMEOUT,))
        
        # Also sync team status if all sessions inactive and team was active
        cursor.execute("""
            UPDATE teams 
            SET status = 'WAITING' 
            WHERE status = 'ACTIVE' 
            AND id NOT IN (SELECT team_id FROM sessions WHERE is_active = 1)
        """)
        
        conn.commit()
        conn.close()

    @staticmethod
    def get_active_session_for_team(team_id):
        SessionModel.clean_expired_sessions()
        conn = get_db_connection()
        session = conn.execute(
            "SELECT * FROM sessions WHERE team_id = ? AND is_active = 1 ORDER BY last_seen DESC LIMIT 1",
            (team_id,)
        ).fetchone()
        conn.close()
        return dict(session) if session else None

    @staticmethod
    def create_session(team_id, device_info="Web Browser"):
        SessionModel.clean_expired_sessions()
        
        # Check if an active session already exists for this team
        existing = SessionModel.get_active_session_for_team(team_id)
        if existing:
            return None, "This team is currently active on another device."

        session_token = str(uuid.uuid4())
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Deactivate any previous sessions for this team
        cursor.execute("UPDATE sessions SET is_active = 0 WHERE team_id = ?", (team_id,))
        
        # Insert new active session
        cursor.execute("""
            INSERT INTO sessions (team_id, session_token, device_info, is_active, last_seen, created_at)
            VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (team_id, session_token, device_info))
        
        # Update team start time if not started yet
        cursor.execute("""
            UPDATE teams 
            SET status = CASE WHEN current_challenge > 5 THEN 'COMPLETED' ELSE 'ACTIVE' END,
                start_time = COALESCE(start_time, CURRENT_TIMESTAMP)
            WHERE id = ?
        """, (team_id,))
        
        conn.commit()
        conn.close()
        return session_token, None

    @staticmethod
    def update_heartbeat(session_token):
        if not session_token:
            return False
            
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE sessions 
            SET last_seen = CURRENT_TIMESTAMP, is_active = 1 
            WHERE session_token = ? AND is_active = 1
        """, (session_token,))
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated

    @staticmethod
    def validate_session(session_token):
        if not session_token:
            return None
        SessionModel.clean_expired_sessions()
        conn = get_db_connection()
        session = conn.execute("""
            SELECT s.*, t.team_name, t.team_code, t.current_challenge, t.total_score, t.status AS team_status
            FROM sessions s
            JOIN teams t ON s.team_id = t.id
            WHERE s.session_token = ? AND s.is_active = 1
        """, (session_token,)).fetchone()
        conn.close()
        return dict(session) if session else None

    @staticmethod
    def terminate_session(session_token):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE sessions SET is_active = 0 WHERE session_token = ?", (session_token,))
        conn.commit()
        conn.close()

    @staticmethod
    def force_unlock_team(team_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE sessions SET is_active = 0 WHERE team_id = ?", (team_id,))
        cursor.execute("UPDATE teams SET status = 'WAITING' WHERE id = ? AND status = 'ACTIVE'", (team_id,))
        conn.commit()
        conn.close()


class ChallengeModel:
    @staticmethod
    def get_by_id(challenge_id):
        conn = get_db_connection()
        ch = conn.execute("SELECT * FROM challenges WHERE id = ?", (challenge_id,)).fetchone()
        conn.close()
        if not ch:
            return None
        res = dict(ch)
        res['data'] = json.loads(res['data_json'])
        return res

    @staticmethod
    def get_all():
        conn = get_db_connection()
        rows = conn.execute("SELECT * FROM challenges ORDER BY id ASC").fetchall()
        conn.close()
        result = []
        for r in rows:
            item = dict(r)
            item['data'] = json.loads(item['data_json'])
            result.append(item)
        return result

    @staticmethod
    def evaluate_answer(challenge_id, submitted_answer):
        ch = ChallengeModel.get_by_id(challenge_id)
        if not ch:
            return False, 0, "Invalid challenge ID."

        ch_type = ch['type']
        ch_data = ch['data']
        is_correct = False

        if ch_type == 'drag_drop':
            # submitted_answer expected to be list or JSON string of answers for blanks
            if isinstance(submitted_answer, str):
                try:
                    submitted = json.loads(submitted_answer)
                except Exception:
                    submitted = [submitted_answer]
            else:
                submitted = submitted_answer
            
            target_blanks = ch_data.get('blanks', [])
            is_correct = (submitted == target_blanks)

        elif ch_type == 'error_line':
            # submitted_answer is integer line number (1-based)
            try:
                selected_line = int(submitted_answer)
                correct_line = int(ch_data.get('correct_line', -1))
                is_correct = (selected_line == correct_line)
            except (ValueError, TypeError):
                is_correct = False

        elif ch_type == 'problem_solving':
            # submitted_answer is text/number string
            clean_sub = str(submitted_answer).strip()
            target_ans = str(ch_data.get('correct_answer', '')).strip()
            acceptable = [str(a).strip() for a in ch_data.get('acceptable_answers', [target_ans])]
            is_correct = (clean_sub in acceptable)

        points = ch['points'] if is_correct else 0
        return is_correct, points, ch_data.get('explanation', '')


class SubmissionModel:
    @staticmethod
    def record_submission(team_id, challenge_id, submitted_answer, is_correct, points):
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Format answer string for storage
        ans_str = json.dumps(submitted_answer) if not isinstance(submitted_answer, str) else submitted_answer
        
        cursor.execute("""
            INSERT INTO submissions (team_id, challenge_id, submitted_answer, is_correct, points_earned, submission_time)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (team_id, challenge_id, ans_str, 1 if is_correct else 0, points))
        
        if is_correct:
            # Advance team to next challenge and add points
            cursor.execute("SELECT current_challenge, total_score, start_time FROM teams WHERE id = ?", (team_id,))
            team = cursor.fetchone()
            
            new_challenge = max(team['current_challenge'], challenge_id + 1)
            new_score = team['total_score'] + points
            
            if new_challenge > 5:
                pause_sec = EventConfigModel.get_pause_seconds()
                cursor.execute("""
                    UPDATE teams 
                    SET current_challenge = 6,
                        total_score = ?,
                        completion_time = CURRENT_TIMESTAMP,
                        status = 'COMPLETED',
                        total_time_seconds = MAX(0, CAST((strftime('%s', 'now') - strftime('%s', start_time)) AS INTEGER) - ?),
                        draft_json = ''
                    WHERE id = ?
                """, (new_score, pause_sec, team_id))
            else:
                cursor.execute("""
                    UPDATE teams 
                    SET current_challenge = ?,
                        total_score = ?,
                        draft_json = ''
                    WHERE id = ?
                """, (new_challenge, new_score, team_id))

        conn.commit()
        conn.close()

    @staticmethod
    def get_team_submissions(team_id):
        conn = get_db_connection()
        rows = conn.execute("""
            SELECT s.*, c.title AS challenge_title, c.points AS max_points
            FROM submissions s
            JOIN challenges c ON s.challenge_id = c.id
            WHERE s.team_id = ?
            ORDER BY s.submission_time ASC
        """, (team_id,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]


class LeaderboardModel:
    @staticmethod
    def get_rankings():
        conn = get_db_connection()
        # Ranking rules (No Points system):
        # Primary: Higher current_challenge = Higher Rank
        # Secondary: Lower completion time / elapsed_seconds = Higher Rank
        query = """
            SELECT 
                id, team_code, team_name, current_challenge, status, start_time, completion_time,
                CASE 
                    WHEN status = 'COMPLETED' THEN total_time_seconds
                    WHEN start_time IS NOT NULL THEN CAST((strftime('%s', 'now') - strftime('%s', start_time)) AS INTEGER)
                    ELSE 999999
                END AS elapsed_seconds
            FROM teams
            ORDER BY 
                current_challenge DESC,
                elapsed_seconds ASC,
                id ASC
        """
        rows = conn.execute(query).fetchall()
        conn.close()
        pause_sec = EventConfigModel.get_pause_seconds()
        
        result = []
        for rank, row in enumerate(rows, start=1):
            r = dict(row)
            r['rank'] = rank
            
            total_sec = r['elapsed_seconds']
            if total_sec == 999999:
                r['formatted_time'] = "--:--"
            else:
                if r.get('status') != 'COMPLETED':
                    total_sec = max(0, int(total_sec) - pause_sec)
                    r['elapsed_seconds'] = total_sec
                minutes = total_sec // 60
                seconds = total_sec % 60
                r['formatted_time'] = f"{minutes:02d}:{seconds:02d}"
            result.append(r)
            
        return result
