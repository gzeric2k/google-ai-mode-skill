#!/usr/bin/env python3
"""
Universal runner for NotebookLM skill scripts
Ensures all scripts run with the correct virtual environment
"""

import os
import sys
import subprocess
from pathlib import Path


def get_venv_python():
    """Get the virtual environment Python executable"""
    skill_dir = Path(__file__).parent.parent
    venv_dir = skill_dir / ".venv"

    if os.name == 'nt':  # Windows
        # Some tools (uv, Git Bash, Cygwin) create bin/ on Windows instead of Scripts/
        scripts_python = venv_dir / "Scripts" / "python.exe"
        if scripts_python.exists():
            return scripts_python
        bin_python = venv_dir / "bin" / "python"
        if bin_python.exists():
            return bin_python
        return scripts_python  # Return canonical path even if missing (triggers setup)

    return venv_dir / "bin" / "python"


def ensure_venv():
    """Ensure virtual environment exists and Python binary is present"""
    skill_dir = Path(__file__).parent.parent
    venv_dir = skill_dir / ".venv"
    setup_script = skill_dir / "scripts" / "setup_environment.py"

    venv_python = get_venv_python()
    needs_setup = not venv_dir.exists() or not venv_python.exists()

    if needs_setup:
        print("First-time setup: Creating virtual environment...")
        print("   This may take a minute...")

        # Run setup with system Python
        result = subprocess.run([sys.executable, str(setup_script)])
        if result.returncode != 0:
            print("Failed to set up environment")
            sys.exit(1)

        print("Environment ready!")

    return get_venv_python()


def main():
    """Main runner"""
    if len(sys.argv) < 2:
        print("Usage: python run.py <script_name> [args...]")
        print("\nAvailable scripts:")
        print("  search.py  - Query Google AI Mode for web research")
        print("  analyze.py - Extract and analyze documents from URL or local file")
        print("\nExamples:")
        print('  python run.py search.py --query "React hooks 2026" --save --debug')
        print('  python run.py analyze.py --url "https://example.com/doc.pdf" --save')
        print('  python run.py analyze.py --file report.pdf --question "Key financials?"')
        sys.exit(1)

    script_name = sys.argv[1]
    script_args = sys.argv[2:]

    # Handle both "scripts/script.py" and "script.py" formats
    if script_name.startswith('scripts/'):
        # Remove the scripts/ prefix if provided
        script_name = script_name[8:]  # len('scripts/') = 8

    # Ensure .py extension
    if not script_name.endswith('.py'):
        script_name += '.py'

    # Get script path
    skill_dir = Path(__file__).parent.parent
    script_path = skill_dir / "scripts" / script_name

    if not script_path.exists():
        print(f"Script not found: {script_name}")
        print(f"   Working directory: {Path.cwd()}")
        print(f"   Skill directory: {skill_dir}")
        print(f"   Looked for: {script_path}")
        sys.exit(1)

    # Ensure venv exists and get Python executable
    venv_python = ensure_venv()

    # Build command
    cmd = [str(venv_python), str(script_path)] + script_args

    # Run the script
    try:
        result = subprocess.run(cmd)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(130)
    except OSError as e:
        if e.errno in (2, 8, 193):  # Not found, Exec format, Not valid Win32 app
            # venv python is a non-Windows binary (e.g. created in WSL/Cygwin)
            # Fall back to system Python
            print(f"  Note: venv Python not usable on this platform, using system Python")
            scripts_dir = script_path.parent
            fallback_cmd = [sys.executable, str(script_path)] + script_args
            env = dict(os.environ, PYTHONPATH=str(scripts_dir))
            result = subprocess.run(fallback_cmd, env=env)
            sys.exit(result.returncode)
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()