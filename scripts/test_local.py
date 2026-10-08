"""Run the full suite against the explicitly local disposable Supabase stack."""
import json
import os
import subprocess
import sys

status = json.loads(subprocess.check_output(
    ['npx', '--no-install', 'supabase', 'status', '-o', 'json'], stderr=subprocess.DEVNULL))
env = os.environ.copy()
for variable, key in [('TLM_TEST_ADMIN_DSN', 'DB_URL'), ('TLM_TEST_AUTH_URL', 'API_URL'),
                      ('TLM_TEST_AUTH_KEY', 'PUBLISHABLE_KEY')]:
    value = status.get(key)
    if not value:
        raise RuntimeError(f'Missing disposable Supabase configuration: {key}')
    env[variable] = value
raise SystemExit(subprocess.call(
    [sys.executable, '-m', 'pytest', *sys.argv[1:]], env=env))
