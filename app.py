import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Configuration
DATABASE = 'votes.db'
ADMIN_PASSWORD = 'moty2025'
MODS = ['Nonno', 'Felon', 'Pez', 'Jensi', 'Marco']
OUTPUT_DIR = 'output'

def get_db():
    """Get database connection"""
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    """Initialize database tables"""
    db = get_db()

    # Create verified_users table
    db.execute('''
        CREATE TABLE IF NOT EXISTS verified_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL COLLATE NOCASE,
            tier TEXT NOT NULL,
            added_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(username COLLATE NOCASE)
        )
    ''')

    # Create votes table
    db.execute('''
        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL COLLATE NOCASE,
            voted_for TEXT NOT NULL,
            vote_weight INTEGER NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(username COLLATE NOCASE)
        )
    ''')

    db.commit()
    db.close()

def get_vote_counts():
    """Get vote counts for all mods"""
    db = get_db()
    results = {}

    for mod in MODS:
        count = db.execute(
            'SELECT COALESCE(SUM(vote_weight), 0) as total FROM votes WHERE voted_for = ?',
            (mod,)
        ).fetchone()
        results[mod] = count['total']

    db.close()
    return results

def update_obs_files():
    """Update OBS text files with current vote counts"""
    # Create output directory if it doesn't exist
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # Get current vote counts
    counts = get_vote_counts()

    # Write each mod's count to a separate file
    for mod in MODS:
        filename = os.path.join(OUTPUT_DIR, f'{mod.lower()}_votes.txt')
        with open(filename, 'w') as f:
            f.write(str(counts[mod]))

# Initialize database on startup
init_db()

@app.route('/')
def index():
    """Main voting page"""
    return render_template('index.html', mods=MODS)

@app.route('/vote', methods=['POST'])
def vote():
    """Process vote submission"""
    username = request.form.get('username', '').strip()
    voted_for = request.form.get('mod')

    # Validation
    if not username:
        flash('Please enter your Twitch username.', 'error')
        return redirect(url_for('index'))

    if voted_for not in MODS:
        flash('Invalid mod selection.', 'error')
        return redirect(url_for('index'))

    db = get_db()

    # Check if username is verified
    verified_user = db.execute(
        'SELECT tier FROM verified_users WHERE LOWER(username) = LOWER(?)',
        (username,)
    ).fetchone()

    if not verified_user:
        flash(f'Username "{username}" not recognized. Please enter your exact Twitch username.', 'error')
        db.close()
        return redirect(url_for('index'))

    # Check if user already voted
    existing_vote = db.execute(
        'SELECT id FROM votes WHERE LOWER(username) = LOWER(?)',
        (username,)
    ).fetchone()

    if existing_vote:
        flash(f'You have already voted!', 'error')
        db.close()
        return redirect(url_for('index'))

    # Calculate vote weight based on tier
    tier = verified_user['tier'].lower()
    vote_weight = 2 if tier in ['sub', 'vip'] else 1

    # Record vote
    try:
        db.execute(
            'INSERT INTO votes (username, voted_for, vote_weight) VALUES (?, ?, ?)',
            (username, voted_for, vote_weight)
        )
        db.commit()

        # Update OBS text files
        update_obs_files()

        flash(f'Thank you for voting, {username}! Your vote for {voted_for} has been recorded.', 'success')
    except sqlite3.Error as e:
        flash('An error occurred. Please try again.', 'error')
        print(f"Database error: {e}")
    finally:
        db.close()

    return redirect(url_for('index'))

@app.route('/results')
def results():
    """Display live voting results"""
    vote_counts = get_vote_counts()

    # Calculate total votes and find the leader
    total_votes = sum(vote_counts.values())
    max_votes = max(vote_counts.values()) if vote_counts else 0

    # Get number of voters
    db = get_db()
    voter_count = db.execute('SELECT COUNT(*) as count FROM votes').fetchone()['count']
    db.close()

    return render_template('results.html',
                         vote_counts=vote_counts,
                         total_votes=total_votes,
                         voter_count=voter_count,
                         max_votes=max_votes,
                         mods=MODS)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    """Admin panel - login and dashboard"""
    if request.method == 'POST':
        # Handle login
        password = request.form.get('password', '')
        if password == ADMIN_PASSWORD:
            session['admin_authenticated'] = True
            return redirect(url_for('admin'))
        else:
            flash('Invalid password', 'error')
            return redirect(url_for('admin'))

    # Check if authenticated
    if not session.get('admin_authenticated'):
        return render_template('admin_login.html')

    # Get all verified users
    db = get_db()
    verified_users = db.execute(
        'SELECT id, username, tier, added_timestamp FROM verified_users ORDER BY username'
    ).fetchall()

    # Get all votes
    votes = db.execute(
        'SELECT id, username, voted_for, vote_weight, timestamp FROM votes ORDER BY timestamp DESC'
    ).fetchall()

    db.close()

    return render_template('admin.html',
                         verified_users=verified_users,
                         votes=votes,
                         vote_counts=get_vote_counts())

@app.route('/admin/reset', methods=['POST'])
def admin_reset():
    """Reset all votes"""
    if not session.get('admin_authenticated'):
        flash('Unauthorized', 'error')
        return redirect(url_for('admin'))

    db = get_db()
    db.execute('DELETE FROM votes')
    db.commit()
    db.close()

    # Update OBS files to show 0 votes
    update_obs_files()

    flash('All votes have been reset!', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/logout')
def admin_logout():
    """Logout from admin panel"""
    session.pop('admin_authenticated', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('admin'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
