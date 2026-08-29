import unittest
import json
import os
from app import create_app
from database import get_db_connection
from models import TeamModel, SessionModel, LeaderboardModel, ChallengeModel, SubmissionModel, EventConfigModel

class Round2ArenaTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        # Reset database tables for isolated test runs
        conn = get_db_connection()
        conn.execute("UPDATE teams SET current_challenge = 1, total_score = 0, start_time = NULL, completion_time = NULL, total_time_seconds = 0, status = 'WAITING'")
        conn.execute("DELETE FROM submissions")
        conn.execute("DELETE FROM sessions")
        conn.commit()
        conn.close()

    def test_01_seed_and_challenges(self):
        """Verify that 5 challenges and demo teams are present in DB."""
        challenges = ChallengeModel.get_all()
        self.assertEqual(len(challenges), 5)
        self.assertEqual(challenges[0]['points'], 10)
        self.assertEqual(challenges[1]['points'], 10)
        self.assertEqual(challenges[2]['points'], 10)
        self.assertEqual(challenges[3]['points'], 10)
        self.assertEqual(challenges[4]['points'], 10)

        team = TeamModel.get_by_code('CW2026')
        self.assertIsNotNone(team)
        self.assertEqual(team['team_name'], 'CYBER WOLVES')

    def test_02_single_device_session_locking(self):
        """Verify that only 1 device can hold an active session per team code."""
        team = TeamModel.get_by_code('CW2026')
        
        # Reset any previous sessions
        SessionModel.force_unlock_team(team['id'])

        # Device 1 logs in
        token1, err1 = SessionModel.create_session(team['id'], "Device 1 - Laptop A")
        self.assertIsNotNone(token1)
        self.assertIsNone(err1)

        # Device 2 tries to log in while Device 1 is active
        token2, err2 = SessionModel.create_session(team['id'], "Device 2 - Laptop B")
        self.assertIsNone(token2)
        self.assertEqual(err2, "This team is currently active on another device.")

    def test_03_heartbeat_and_expiration(self):
        """Test heartbeat ping and validation."""
        team = TeamModel.get_by_code('HT2026')
        SessionModel.force_unlock_team(team['id'])
        token, _ = SessionModel.create_session(team['id'])
        
        # Valid heartbeat update
        updated = SessionModel.update_heartbeat(token)
        self.assertTrue(updated)
        
        # Valid session query
        sess_data = SessionModel.validate_session(token)
        self.assertIsNotNone(sess_data)
        self.assertEqual(sess_data['team_code'], 'HT2026')

    def test_04_full_challenge_progression(self):
        """Simulate a complete 100-point challenge run for Team BM2026."""
        EventConfigModel.set_round_status('ACTIVE')
        team = TeamModel.get_by_code('BM2026')
        SessionModel.force_unlock_team(team['id'])

        # Login via HTTP test client
        response = self.client.post('/login', data={'team_code': 'BM2026'}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        # 1. Challenge 1 (Drag & Drop: ["main", "print"])
        res1 = self.client.post('/api/submit-challenge', json={
            'challenge_id': 1,
            'answer': ['main', 'print']
        })
        d1 = json.loads(res1.data)
        self.assertIn('is_correct', d1, msg=f"Unexpected response: {d1}")
        self.assertTrue(d1['is_correct'])

        # 2. Challenge 2 (Drag & Drop: ["<", "print", "return"])
        res2 = self.client.post('/api/submit-challenge', json={
            'challenge_id': 2,
            'answer': ['<', 'print', 'return']
        })
        d2 = json.loads(res2.data)
        self.assertTrue(d2['is_correct'])

        # 3. Challenge 3 (Line Error: Line 6)
        res3 = self.client.post('/api/submit-challenge', json={
            'challenge_id': 3,
            'answer': 6
        })
        d3 = json.loads(res3.data)
        self.assertTrue(d3['is_correct'])

        # 4. Challenge 4 (Line Error: Line 6)
        res4 = self.client.post('/api/submit-challenge', json={
            'challenge_id': 4,
            'answer': 6
        })
        d4 = json.loads(res4.data)
        self.assertTrue(d4['is_correct'])

        # 5. Challenge 5 (Problem Solving: "933")
        res5 = self.client.post('/api/submit-challenge', json={
            'challenge_id': 5,
            'answer': '933'
        })
        d5 = json.loads(res5.data)
        self.assertTrue(d5['is_correct'])
        self.assertTrue(d5['completed_all'])

        # Verify team status in DB
        updated_team = TeamModel.get_by_id(team['id'])
        self.assertEqual(updated_team['status'], 'COMPLETED')
        self.assertEqual(updated_team['current_challenge'], 6)

    def test_05_leaderboard_rankings(self):
        """Verify leaderboard produces sorted ranks based on total_score points."""
        rankings = LeaderboardModel.get_rankings()
        self.assertTrue(len(rankings) >= 5)
        # Ensure total_score sorted descending
        for i in range(len(rankings) - 1):
            self.assertGreaterEqual(rankings[i]['total_score'], rankings[i+1]['total_score'])

    def test_06_admin_only_leaderboard_protection(self):
        """Verify that non-admins are blocked from viewing leaderboard, and admin login grants access."""
        # Unauthenticated request to /leaderboard should redirect to /admin/login
        res1 = self.client.get('/leaderboard')
        self.assertEqual(res1.status_code, 302)
        self.assertIn('/admin/login', res1.location)

        # Login as Admin
        admin_res = self.client.post('/admin/login', data={
            'admin_id': 'admin',
            'password': 'admin2026'
        }, follow_redirects=True)
        self.assertEqual(admin_res.status_code, 200)

        # Authenticated Admin access to /leaderboard should succeed (200 OK)
        res2 = self.client.get('/leaderboard')
        self.assertEqual(res2.status_code, 200)
    def test_07_auto_team_registration_and_unique_code(self):
        """Verify entering a new team name auto-creates database entry and generates random unique passcode."""
        new_team_name = "Shadow Hackers"
        res = self.client.post('/login', data={'team_identifier': new_team_name}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Shadow Hackers', res.data)

        # Retrieve created team from DB
        team = TeamModel.get_by_name(new_team_name)
        self.assertIsNotNone(team)
        self.assertIsNotNone(team['team_code'])
        self.assertTrue(team['team_code'].startswith('SH-') or team['team_code'].startswith('TEAM-'))

        # Logout and test re-logging in using the generated unique passcode
        SessionModel.force_unlock_team(team['id'])
        self.client.get('/logout')
        res_relogin = self.client.post('/login', data={'team_identifier': team['team_code']}, follow_redirects=True)
        self.assertEqual(res_relogin.status_code, 200)
        self.assertIn(b'Shadow Hackers', res_relogin.data)

        # Logout and verify that trying to log in with the team name again is BLOCKED
        SessionModel.force_unlock_team(team['id'])
        self.client.get('/logout')
        res_blocked = self.client.post('/login', data={'team_identifier': new_team_name}, follow_redirects=True)
        self.assertIn(b'already registered', res_blocked.data)

    def test_08_admin_permission_guard(self):
        """Verify contestants cannot enter or submit challenges until Admin starts the round."""
        EventConfigModel.set_round_status('NOT_STARTED')
        team = TeamModel.get_by_code('CW2026')
        SessionModel.force_unlock_team(team['id'])
        
        # Log in contestant
        self.client.post('/login', data={'team_code': 'CW2026'}, follow_redirects=True)
        
        # Attempting to view challenge 1 when NOT_STARTED should redirect to lobby with notice
        res_view = self.client.get('/challenge/1', follow_redirects=True)
        self.assertIn(b'Standby', res_view.data)

        # Attempting to submit answer when NOT_STARTED should be rejected with 403
        res_sub = self.client.post('/api/submit-challenge', json={'challenge_id': 1, 'answer': ['main', 'print']})
        self.assertEqual(res_sub.status_code, 403)
        self.assertIn(b'GAME_STOPPED', res_sub.data)

        # Admin starts round -> submissions now succeed
        EventConfigModel.set_round_status('ACTIVE')
        res_sub2 = self.client.post('/api/submit-challenge', json={'challenge_id': 1, 'answer': ['main', 'print']})
        self.assertEqual(res_sub2.status_code, 200)

    def test_09_reset_entire_game(self):
        """Verify Admin can reset entire game for all teams back to Challenge 1."""
        # 1. Log in admin and execute reset entire game API
        self.client.post('/admin/login', data={'admin_id': 'admin', 'password': 'admin2026'})
        res = self.client.post('/api/admin/reset-entire-game')
        self.assertEqual(res.status_code, 200)
        d = json.loads(res.data)
        self.assertTrue(d['success'])

        # 2. Verify all teams are back at current_challenge 1
        teams = TeamModel.get_all()
        for t in teams:
            self.assertEqual(t['current_challenge'], 1)
            self.assertEqual(t['status'], 'WAITING')

    def test_10_pause_and_stop_preserve_progress(self):
        """Pause and stop block play, keep challenge progress, and resume on the same challenge."""
        EventConfigModel.set_round_status('ACTIVE')
        team = TeamModel.get_by_code('CW2026')
        SessionModel.force_unlock_team(team['id'])
        self.client.post('/login', data={'team_code': 'CW2026'}, follow_redirects=True)

        first = self.client.post('/api/submit-challenge', json={'challenge_id': 1, 'answer': ['main', 'print']})
        self.assertTrue(json.loads(first.data)['is_correct'])
        self.assertEqual(TeamModel.get_by_id(team['id'])['current_challenge'], 2)

        draft_res = self.client.post('/api/save-draft', json={'challenge_id': 2, 'draft': ['<', 'print', '']})
        self.assertEqual(draft_res.status_code, 200)

        EventConfigModel.set_round_status('PAUSED')
        paused = self.client.post('/api/submit-challenge', json={'challenge_id': 2, 'answer': ['<', 'print', 'return']})
        self.assertEqual(paused.status_code, 403)
        self.assertEqual(TeamModel.get_by_id(team['id'])['current_challenge'], 2)
        self.assertEqual(TeamModel.get_draft(team['id'])['draft'], ['<', 'print', ''])

        status = json.loads(self.client.get('/api/event-status').data)
        self.assertEqual(status['round_status'], 'PAUSED')

        EventConfigModel.set_round_status('STOPPED')
        stopped = self.client.post('/api/submit-challenge', json={'challenge_id': 2, 'answer': ['<', 'print', 'return']})
        self.assertEqual(stopped.status_code, 403)
        status2 = json.loads(self.client.get('/api/event-status').data)
        self.assertEqual(status2['round_status'], 'STOPPED')
        self.assertEqual(TeamModel.get_by_id(team['id'])['current_challenge'], 2)

        EventConfigModel.set_round_status('ACTIVE')
        resumed = self.client.post('/api/submit-challenge', json={'challenge_id': 2, 'answer': ['<', 'print', 'return']})
        self.assertEqual(resumed.status_code, 200)
        self.assertTrue(json.loads(resumed.data)['is_correct'])
        self.assertEqual(TeamModel.get_by_id(team['id'])['current_challenge'], 3)

    def test_11_admin_delete_team(self):
        """Verify Admin can permanently delete a team from DB."""
        # 1. Create temporary team
        team_id = TeamModel.create_team('DEL2026', 'Temp Delete Team')
        self.assertIsNotNone(TeamModel.get_by_id(team_id))

        # 2. Non-admin request should redirect to admin login
        res1 = self.client.post(f'/api/admin/delete-team/{team_id}')
        self.assertEqual(res1.status_code, 302)

        # 3. Log in as admin and delete team
        self.client.post('/admin/login', data={'admin_id': 'admin', 'password': 'admin2026'})
        res2 = self.client.post(f'/api/admin/delete-team/{team_id}')
        self.assertEqual(res2.status_code, 200)
        self.assertTrue(json.loads(res2.data)['success'])

        # 4. Verify team is gone from DB
        self.assertIsNone(TeamModel.get_by_id(team_id))

    def test_12_skip_challenge(self):
        """Verify contestants can skip a challenge and advance to the next one (0 points)."""
        EventConfigModel.set_round_status('ACTIVE')
        team = TeamModel.get_by_code('CW2026')
        SessionModel.force_unlock_team(team['id'])
        self.client.get('/logout')
        self.client.post('/login', data={'team_code': 'CW2026'}, follow_redirects=True)

        # Skip Challenge 1
        res = self.client.post('/api/skip-challenge', json={'challenge_id': 1})
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['next_challenge'], 2)

        # Verify DB updated
        updated_team = TeamModel.get_by_id(team['id'])
        self.assertEqual(updated_team['current_challenge'], 2)

    def test_13_resubmit_previous_challenge(self):
        """Verify contestants can edit and resubmit answers for previous unlocked challenges, updating points."""
        EventConfigModel.set_round_status('ACTIVE')
        team = TeamModel.get_by_code('CW2026')
        SessionModel.force_unlock_team(team['id'])
        self.client.get('/logout')
        self.client.post('/login', data={'team_code': 'CW2026'}, follow_redirects=True)

        # 1. Submit partial answer for Challenge 1 (1 out of 2 correct = 5.0 pts)
        self.client.post('/api/submit-challenge', json={'challenge_id': 1, 'answer': ['main', 'wrong_word']})
        t1 = TeamModel.get_by_id(team['id'])
        self.assertEqual(t1['current_challenge'], 2)
        self.assertEqual(t1['total_score'], 5.0)

        # 2. Advance to Challenge 3 by submitting Challenge 2 (10.0 pts)
        self.client.post('/api/submit-challenge', json={'challenge_id': 2, 'answer': ['<', 'print', 'return']})
        t2 = TeamModel.get_by_id(team['id'])
        self.assertEqual(t2['current_challenge'], 3)
        self.assertEqual(t2['total_score'], 15.0)

        # 3. Go back to Challenge 1, edit answer to 100% correct (10.0 pts), and resubmit
        res_resub = self.client.post('/api/submit-challenge', json={'challenge_id': 1, 'answer': ['main', 'print']})
        self.assertEqual(res_resub.status_code, 200)

        # 4. Verify points updated from 15.0 to 20.0 (5.0 -> 10.0 for Ch 1, + 10.0 for Ch 2)
        t3 = TeamModel.get_by_id(team['id'])
        self.assertEqual(t3['current_challenge'], 3) # Active challenge remains 3
        self.assertEqual(t3['total_score'], 20.0) # Score updated from 15.0 to 20.0!

    def test_14_delete_team_api(self):
        """Verify admin can delete a team permanently from the leaderboard and database."""
        self.client.post('/admin/login', data={'admin_id': 'admin', 'password': 'admin2026'})
        team = TeamModel.get_by_code('CW2026')
        self.assertIsNotNone(team)
        
        res = self.client.post(f'/api/admin/delete-team/{team["id"]}')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        
        deleted_team = TeamModel.get_by_id(team['id'])
        self.assertIsNone(deleted_team)

if __name__ == '__main__':
    unittest.main()
