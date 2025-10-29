#!/usr/bin/env python3
"""
Convert Twitch export CSV to the format needed by populate_users.py

Usage:
    python convert_twitch_export.py <input.csv> <tier> [output.csv]

Example:
    python convert_twitch_export.py followers_current_20251025_190107.csv follower followers.csv
    python convert_twitch_export.py subscribers.csv sub subs.csv
    python convert_twitch_export.py vips.csv vip vips.csv
"""

import csv
import sys

def convert_csv(input_file, tier, output_file=None):
    """Convert Twitch export CSV to populate_users format"""

    if output_file is None:
        output_file = f'converted_{tier}s.csv'

    valid_tiers = ['follower', 'sub', 'vip']
    if tier not in valid_tiers:
        print(f"Error: tier must be one of {valid_tiers}")
        sys.exit(1)

    usernames = []

    try:
        with open(input_file, 'r') as f:
            reader = csv.DictReader(f)

            # Check if 'username' or 'Username' column exists
            username_col = None
            if 'username' in reader.fieldnames:
                username_col = 'username'
            elif 'Username' in reader.fieldnames:
                username_col = 'Username'
            else:
                print(f"Error: CSV must have a 'username' or 'Username' column")
                print(f"Found columns: {reader.fieldnames}")
                sys.exit(1)

            for row in reader:
                username = row[username_col].strip()
                if username:
                    usernames.append(username)

        # Write output CSV
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['username', 'tier'])
            for username in usernames:
                writer.writerow([username, tier])

        print(f"✅ Converted {len(usernames)} users")
        print(f"📝 Output saved to: {output_file}")
        print(f"\nNext step:")
        print(f"  python populate_users.py {output_file}")

    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python convert_twitch_export.py <input.csv> <tier> [output.csv]")
        print("\nTier must be one of: follower, sub, vip")
        print("\nExamples:")
        print("  python convert_twitch_export.py followers_current_20251025_190107.csv follower")
        print("  python convert_twitch_export.py subs.csv sub")
        print("  python convert_twitch_export.py vips.csv vip")
        sys.exit(1)

    input_file = sys.argv[1]
    tier = sys.argv[2]
    output_file = sys.argv[3] if len(sys.argv) > 3 else None

    convert_csv(input_file, tier, output_file)
