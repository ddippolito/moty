#!/usr/bin/env python3
"""
Script to populate verified users from a CSV file.

Usage:
    python populate_users.py <csv_file>

CSV Format:
    username,tier
    viewer1,follower
    viewer2,sub
    viewer3,vip

Valid tiers: follower, sub, vip
"""

import csv
import sqlite3
import sys

DATABASE = 'votes.db'
VALID_TIERS = ['follower', 'sub', 'vip']

def init_db():
    """Initialize database if it doesn't exist"""
    db = sqlite3.connect(DATABASE)

    db.execute('''
        CREATE TABLE IF NOT EXISTS verified_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL COLLATE NOCASE,
            tier TEXT NOT NULL,
            added_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(username COLLATE NOCASE)
        )
    ''')

    db.commit()
    return db

def populate_users(csv_file):
    """Read CSV and populate verified users table"""
    db = init_db()
    cursor = db.cursor()

    added_count = 0
    duplicate_count = 0
    error_count = 0

    try:
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)

            # Check for required columns
            if 'username' not in reader.fieldnames or 'tier' not in reader.fieldnames:
                print("Error: CSV must have 'username' and 'tier' columns")
                return

            for row_num, row in enumerate(reader, start=2):  # Start at 2 (after header)
                username = row['username'].strip()
                tier = row['tier'].strip().lower()

                # Validate tier
                if tier not in VALID_TIERS:
                    print(f"Row {row_num}: Invalid tier '{tier}' for user '{username}'. Skipping.")
                    error_count += 1
                    continue

                # Validate username
                if not username:
                    print(f"Row {row_num}: Empty username. Skipping.")
                    error_count += 1
                    continue

                # Try to insert
                try:
                    cursor.execute(
                        'INSERT INTO verified_users (username, tier) VALUES (?, ?)',
                        (username, tier)
                    )
                    added_count += 1
                    print(f"Added: {username} ({tier})")
                except sqlite3.IntegrityError:
                    # Duplicate username
                    duplicate_count += 1
                    print(f"Duplicate: {username} already exists. Skipping.")

        db.commit()

        print(f"\n--- Summary ---")
        print(f"Successfully added: {added_count}")
        print(f"Duplicates skipped: {duplicate_count}")
        print(f"Errors: {error_count}")
        print(f"Total in database: {cursor.execute('SELECT COUNT(*) FROM verified_users').fetchone()[0]}")

    except FileNotFoundError:
        print(f"Error: File '{csv_file}' not found")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python populate_users.py <csv_file>")
        print("\nExample CSV format:")
        print("username,tier")
        print("viewer1,follower")
        print("viewer2,sub")
        print("viewer3,vip")
        sys.exit(1)

    csv_file = sys.argv[1]
    populate_users(csv_file)
