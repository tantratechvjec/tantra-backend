#!/usr/bin/env python3
"""Startup helper for Render.

Writes FIREBASE_SERVICE_ACCOUNT_JSON (if present) to a temporary file and sets
FIREBASE_CREDENTIALS_FILE to that path, then execs gunicorn to run the app.
"""
import os
import sys
import json
import tempfile


def write_service_account(json_str: str):
    # Write JSON to a temp file and return the path
    tf = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
    # If json_str came via env var it may contain literal \n sequences or be compact
    try:
        # Try to parse then pretty-write to ensure valid JSON
        obj = json.loads(json_str)
        tf.write(json.dumps(obj, indent=2).encode('utf-8'))
    except Exception:
        # Fallback: write raw string
        tf.write(json_str.encode('utf-8'))
    tf.flush()
    tf.close()
    return tf.name


def main():
    port = os.environ.get('PORT', '5000')
    sa_json = os.environ.get('FIREBASE_SERVICE_ACCOUNT_JSON')
    if sa_json:
        path = write_service_account(sa_json)
        # Expose the file path to the app
        os.environ['FIREBASE_CREDENTIALS_FILE'] = path

    # Default to running gunicorn for the app callable
    bind = f'0.0.0.0:{port}'
    cmd = ['gunicorn', 'app:app', '--bind', bind]

    # Replace current process with gunicorn
    os.execvp(cmd[0], cmd)


if __name__ == '__main__':
    main()
