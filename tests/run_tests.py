import argparse
import os
import subprocess
import sys

def main():
    parser = argparse.ArgumentParser(description="E2E Test Runner")
    parser.add_argument("--mock", action="store_true", help="Launch tests against local mock servers")
    parser.add_argument("--backend-url", default="http://localhost:8000", help="FastAPI backend URL")
    parser.add_argument("--frontend-url", default="http://localhost:3000", help="React frontend URL")
    args, unknown = parser.parse_known_args()

    env = os.environ.copy()
    if args.mock:
        env["USE_MOCK_SERVERS"] = "true"
        env["BACKEND_URL"] = "http://127.0.0.1:8001"
        env["FRONTEND_URL"] = "http://127.0.0.1:8001"
    else:
        env["USE_MOCK_SERVERS"] = "false"
        env["BACKEND_URL"] = args.backend_url
        env["FRONTEND_URL"] = args.frontend_url

    print("================== E2E Test Execution ==================")
    print(f"Target Mode: {'Mocked' if args.mock else 'Real Services'}")
    print(f"Backend URL: {env['BACKEND_URL']}")
    print(f"Frontend URL: {env['FRONTEND_URL']}")
    print("========================================================")

    # Automatically install Playwright browser driver (chromium only to save time)
    try:
        print("Installing Playwright Chromium browser...")
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
    except subprocess.SubprocessError as e:
        print(f"Playwright browser installation failed or skipped: {e}")

    # Invoke pytest
    cmd = [sys.executable, "-m", "pytest", "-v"] + unknown
    result = subprocess.run(cmd, env=env)
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
