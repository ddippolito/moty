import os
import sqlite3
import csv
import io
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response
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

@app.route('/prizes')
def prizes():
    """Display prize information page"""
    return render_template('prizes.html')

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

    # Pagination, filtering, and search parameters
    page = request.args.get('page', 1, type=int)
    tier_filter = request.args.get('tier', 'all')
    search = request.args.get('search', '').strip()
    per_page = 50

    db = get_db()

    # Build query for verified users with optional tier filter and search
    query = 'SELECT id, username, tier, added_timestamp FROM verified_users'
    params = []
    where_clauses = []

    if tier_filter != 'all':
        where_clauses.append('tier = ?')
        params.append(tier_filter)

    if search:
        where_clauses.append('username LIKE ?')
        params.append(f'%{search}%')

    if where_clauses:
        query += ' WHERE ' + ' AND '.join(where_clauses)

    # Get total count for pagination
    count_query = query.replace('SELECT id, username, tier, added_timestamp', 'SELECT COUNT(*)')
    total_users = db.execute(count_query, params).fetchone()[0]
    total_pages = (total_users + per_page - 1) // per_page  # Ceiling division

    # Ensure page is within valid range
    page = max(1, min(page, total_pages)) if total_pages > 0 else 1

    # Add sorting and pagination
    query += ' ORDER BY tier, username LIMIT ? OFFSET ?'
    params.extend([per_page, (page - 1) * per_page])

    verified_users = db.execute(query, params).fetchall()

    # Get tier counts for filter badges
    tier_counts = {}
    for tier in ['follower', 'sub', 'vip']:
        count = db.execute('SELECT COUNT(*) FROM verified_users WHERE tier = ?', (tier,)).fetchone()[0]
        tier_counts[tier] = count

    # Get all votes
    votes = db.execute(
        'SELECT id, username, voted_for, vote_weight, timestamp FROM votes ORDER BY timestamp DESC'
    ).fetchall()

    db.close()

    return render_template('admin.html',
                         verified_users=verified_users,
                         votes=votes,
                         vote_counts=get_vote_counts(),
                         page=page,
                         total_pages=total_pages,
                         total_users=total_users,
                         tier_filter=tier_filter,
                         tier_counts=tier_counts,
                         search=search)

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

@app.route('/admin/export')
def admin_export():
    """Export all votes to CSV"""
    if not session.get('admin_authenticated'):
        flash('Unauthorized', 'error')
        return redirect(url_for('admin'))

    db = get_db()
    votes = db.execute(
        'SELECT username, voted_for, vote_weight, timestamp FROM votes ORDER BY timestamp DESC'
    ).fetchall()
    db.close()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Username', 'Voted For', 'Vote Weight', 'Timestamp'])

    for vote in votes:
        writer.writerow([vote['username'], vote['voted_for'], vote['vote_weight'], vote['timestamp']])

    # Create response with CSV file
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=votes_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'

    return response

@app.route('/admin/upload-users', methods=['POST'])
def admin_upload_users():
    """Upload CSV file to update verified users"""
    if not session.get('admin_authenticated'):
        flash('Unauthorized', 'error')
        return redirect(url_for('admin'))

    if 'file' not in request.files:
        flash('No file uploaded', 'error')
        return redirect(url_for('admin'))

    file = request.files['file']

    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('admin'))

    if not file.filename.endswith('.csv'):
        flash('Please upload a CSV file', 'error')
        return redirect(url_for('admin'))

    try:
        # Read CSV file
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_reader = csv.reader(stream)

        # Skip header row if it exists
        header = next(csv_reader)
        if header[0].lower() not in ['username', 'user']:
            # No header, reset reader
            stream.seek(0)
            csv_reader = csv.reader(stream)

        db = get_db()
        added_count = 0
        updated_count = 0

        for row in csv_reader:
            if len(row) < 2:
                continue

            username = row[0].strip()
            tier = row[1].strip().lower()

            if not username or tier not in ['follower', 'sub', 'vip']:
                continue

            # Check if user already exists
            existing = db.execute(
                'SELECT id FROM verified_users WHERE LOWER(username) = LOWER(?)',
                (username,)
            ).fetchone()

            if existing:
                # Update existing user
                db.execute(
                    'UPDATE verified_users SET tier = ? WHERE LOWER(username) = LOWER(?)',
                    (tier, username)
                )
                updated_count += 1
            else:
                # Insert new user
                db.execute(
                    'INSERT INTO verified_users (username, tier) VALUES (?, ?)',
                    (username, tier)
                )
                added_count += 1

        db.commit()
        db.close()

        flash(f'Successfully processed! Added {added_count} new users, updated {updated_count} existing users.', 'success')

    except Exception as e:
        flash(f'Error processing file: {str(e)}', 'error')
        print(f"Error: {e}")

    return redirect(url_for('admin'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
