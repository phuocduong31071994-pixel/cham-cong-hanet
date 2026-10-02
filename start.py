import os
import sys
import subprocess
import traceback

def main():
    port = os.environ.get("PORT", "5000")
    print(f"=== KIMQ ATTENDANCE STARTUP ===", flush=True)
    print(f"Python executable: {sys.executable}", flush=True)
    print(f"PORT environment variable: {port}", flush=True)
    print(f"DATABASE_URL set: {bool(os.environ.get('DATABASE_URL'))}", flush=True)

    # 1. Test importing app to verify database connection and schema
    try:
        print("Testing app import...", flush=True)
        from app import app
        print("App imported successfully without fatal errors!", flush=True)
    except Exception as e:
        err_msg = traceback.format_exc()
        print(f"FATAL ERROR DURING APP IMPORT:\n{err_msg}", flush=True)
        # Start a lightweight HTTP server so the container does not crash and we can see the error
        try:
            from flask import Flask
            fallback = Flask(__name__)
            @fallback.route('/')
            @fallback.route('/health')
            def show_err():
                return f"<h2>KimQ Attendance Startup Error</h2><pre>{err_msg}</pre>", 500
            print(f"Starting fallback error diagnostic server on port {port}...", flush=True)
            fallback.run(host="0.0.0.0", port=int(port))
        except Exception as fb_err:
            print(f"Could not start fallback: {fb_err}", flush=True)
        sys.exit(1)

    # 2. Determine port bindings
    bind_args = ["-b", f"0.0.0.0:{port}"]
    if str(port) != "5000":
        bind_args.extend(["-b", "0.0.0.0:5000"])

    cmd = [
        "gunicorn",
        "-w", "2",
        *bind_args,
        "--timeout", "120",
        "app:app"
    ]
    print(f"Running Gunicorn command: {' '.join(cmd)}", flush=True)
    
    try:
        res = subprocess.run(cmd)
        if res.returncode != 0:
            print(f"Gunicorn exited with code {res.returncode}. Retrying on single port 0.0.0.0:{port}...", flush=True)
            single_cmd = ["gunicorn", "-w", "2", "-b", f"0.0.0.0:{port}", "--timeout", "120", "app:app"]
            subprocess.run(single_cmd)
    except Exception as run_err:
        print(f"Error running gunicorn subprocess: {run_err}", flush=True)
        # Fallback to direct flask app run
        print(f"Falling back to app.run(host='0.0.0.0', port={port})...", flush=True)
        app.run(host="0.0.0.0", port=int(port))

if __name__ == "__main__":
    main()
