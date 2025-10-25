# Mod of the Year 2025 - Voting Application

A Flask-based voting application for Twitch community "Mod of the Year" contests. Features verified user system with weighted voting for subscribers and VIPs.

## Features

- ✅ Verified user whitelist system (only approved users can vote)
- ✅ Weighted voting: Followers (1 vote), Subs/VIPs (2 votes)
- ✅ Duplicate vote prevention
- ✅ Case-insensitive username matching
- ✅ OBS integration with individual vote count text files
- ✅ Admin panel for monitoring votes
- ✅ Mobile-responsive design with gaming theme

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Prepare Verified Users

Create a CSV file with your Twitch community members:

```csv
username,tier
viewer1,follower
viewer2,sub
viewer3,vip
```

Valid tiers: `follower`, `sub`, `vip`

### 3. Populate Database

```bash
python populate_users.py your_users.csv
```

This creates `votes.db` with your verified users.

### 4. Run the Application

```bash
python app.py
```

The app will run at `http://localhost:5000`

## Testing Locally

Test users are included in `test_users.csv`:

```bash
python populate_users.py test_users.csv
python app.py
```

Test usernames:
- `testfollower1`, `testfollower2` (1 vote each)
- `testsub1`, `testsub2` (2 votes each)
- `testvip1` (2 votes)

Visit `http://localhost:5000` and try voting!

## Routes

- `/` - Main voting page
- `/results` - Live results (Phase 2)
- `/admin` - Admin dashboard (Phase 3, password: moty2025)

## Deployment

### Railway.app

1. Push to GitHub:
   ```bash
   git add .
   git commit -m "Initial commit"
   git push origin main
   ```

2. Connect repository to Railway
3. Railway will automatically detect Flask and deploy
4. Set `PORT` environment variable if needed (Railway does this automatically)

## Project Structure

```
moty/
├── app.py                 # Main Flask application
├── populate_users.py      # Script to import verified users
├── requirements.txt       # Python dependencies
├── votes.db              # SQLite database (created after population)
├── templates/
│   └── index.html        # Voting page template
├── test_users.csv        # Sample test data
└── README.md            # This file
```

## Database Schema

**verified_users table:**
- `id`: Primary key
- `username`: Twitch username (case-insensitive unique)
- `tier`: follower, sub, or vip
- `added_timestamp`: When user was added

**votes table:**
- `id`: Primary key
- `username`: Twitch username (case-insensitive unique)
- `voted_for`: Mod name
- `vote_weight`: 1 or 2 based on tier
- `timestamp`: When vote was cast

## Admin Password

Default admin password: `moty2025`

To change it, edit the `ADMIN_PASSWORD` variable in `app.py`.

## Mods in Contest

1. Nonno
2. Felon
3. Pez
4. Jensi
5. Marco

To change the mod list, edit the `MODS` list in `app.py`.

## Development Status

**Phase 1: ✅ Complete**
- Core voting infrastructure
- Database setup
- Basic voting form
- User verification

**Phase 2: 🚧 Coming Soon**
- Results page
- OBS integration

**Phase 3: 🚧 Coming Soon**
- Admin panel
- Vote monitoring

**Phase 4: 🚧 Coming Soon**
- UI polish
- Responsive design

## License

MIT
