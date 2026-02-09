import subprocess

# 実行を許可するコマンド一覧
COMMANDS = {
    'echo': ['echo', 'hoge']
}


def execute_command(code: str):
    if code not in COMMANDS:
        return {
            'ok': False,
            'error': 'invalid_command'
        }

    cmd = COMMANDS[code]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
        )

        return {
            'ok': True,
            'code': code,
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
        }

    except subprocess.TimeoutExpired:
        return {
            'ok': False,
            'error': 'timeout'
        }

    except Exception as e:
        return {
            'ok': False,
            'error': str(e)
        }
