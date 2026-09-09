import subprocess
import sys
import os

def ensure_environment():
    # Ensure pip is available
    try:
        import pip
    except ImportError:
        print("[run_server] pip not found. Installing pip...")
        try:
            get_pip_url = "https://bootstrap.pypa.io/get-pip.py"
            subprocess.run(f"curl -sS {get_pip_url} -o /tmp/get-pip.py && {sys.executable} /tmp/get-pip.py", shell=True, check=True)
        except Exception as e:
            print(f"[run_server] Warning installing pip: {e}")

    # Check required core dependencies
    required_pkgs = ["streamlit", "pandas", "numpy", "sklearn", "lightgbm", "plotly", "reportlab"]
    missing = False
    for pkg in required_pkgs:
        try:
            __import__(pkg)
        except ImportError:
            missing = True
            break

    if missing:
        print("[run_server] Missing dependencies detected. Installing from requirements.txt...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "--no-cache-dir", "-r", "requirements.txt"], check=True)
        except Exception as e:
            print(f"[run_server] Error during pip install: {e}")

def main():
    ensure_environment()
    print("[run_server] Starting Streamlit server on 0.0.0.0:3000...")
    cmd = [
        sys.executable, "-m", "streamlit", "run", "app.py",
        "--server.port", "3000",
        "--server.address", "0.0.0.0",
        "--server.headless", "true",
        "--server.enableCORS", "false",
        "--server.enableXsrfProtection", "false"
    ]
    os.execvp(sys.executable, cmd)

if __name__ == "__main__":
    main()
