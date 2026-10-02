import os
import sys
import socket
import threading
import subprocess
import time
import traceback

def pipe(s, d):
    try:
        while True:
            data = s.recv(4096)
            if not data:
                break
            d.sendall(data)
    except Exception:
        pass
    finally:
        try:
            d.shutdown(socket.SHUT_WR)
        except Exception:
            pass

def start_tcp_bridge(listen_port, target_port):
    """Bridges traffic from listen_port to target_port"""
    try:
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("0.0.0.0", listen_port))
        srv.listen(128)
        print(f"[Bridge] Listening on 0.0.0.0:{listen_port} -> forwarding to 127.0.0.1:{target_port}", flush=True)
        while True:
            client, _ = srv.accept()
            try:
                target = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                target.connect(("127.0.0.1", target_port))
                threading.Thread(target=pipe, args=(client, target), daemon=True).start()
                threading.Thread(target=pipe, args=(target, client), daemon=True).start()
            except Exception as conn_err:
                print(f"[Bridge] Error connecting to target port {target_port}: {conn_err}", flush=True)
                try:
                    client.close()
                except Exception:
                    pass
    except Exception as bridge_err:
        print(f"[Bridge] Could not start bridge on port {listen_port}: {bridge_err}", flush=True)

def main():
    port_str = os.environ.get("PORT", "5000")
    try:
        main_port = int(port_str)
    except Exception:
        main_port = 5000

    print(f"=== KIMQ ATTENDANCE STARTUP ===", flush=True)
    print(f"Python executable: {sys.executable}", flush=True)
    print(f"PORT environment variable: {main_port}", flush=True)
    print(f"DATABASE_URL set: {bool(os.environ.get('DATABASE_URL'))}", flush=True)

    # 1. Start TCP bridge so BOTH port 5000 and port 8080 always accept HTTP traffic
    if main_port != 5000:
        # Railway domain routes to targetPort: 5000, Gunicorn listens on main_port (e.g. 8080)
        # Bridge 5000 -> main_port
        threading.Thread(target=start_tcp_bridge, args=(5000, main_port), daemon=True).start()
    else:
        # Gunicorn listens on 5000, bridge 8080 -> 5000
        threading.Thread(target=start_tcp_bridge, args=(8080, 5000), daemon=True).start()

    # 2. Test importing app to verify database connection and schema
    try:
        print("Testing app import...", flush=True)
        from app import app
        print("App imported successfully without fatal errors!", flush=True)
    except Exception as e:
        err_msg = traceback.format_exc()
        print(f"FATAL ERROR DURING APP IMPORT:\n{err_msg}", flush=True)
        from flask import Flask
        fallback = Flask(__name__)
        @fallback.route('/')
        @fallback.route('/health')
        def show_err():
            return f"<h2>KimQ Attendance Startup Error</h2><pre>{err_msg}</pre>", 500
        fallback.run(host="0.0.0.0", port=main_port)
        sys.exit(1)

    # 3. Launch Gunicorn on main_port
    cmd = [
        "gunicorn",
        "-w", "2",
        "-b", f"0.0.0.0:{main_port}",
        "--timeout", "120",
        "app:app"
    ]
    print(f"Running Gunicorn command: {' '.join(cmd)}", flush=True)
    
    try:
        res = subprocess.run(cmd)
        if res.returncode != 0:
            print(f"Gunicorn exited with code {res.returncode}. Running direct app.run fallback...", flush=True)
            app.run(host="0.0.0.0", port=main_port)
    except Exception as run_err:
        print(f"Error running gunicorn: {run_err}", flush=True)
        app.run(host="0.0.0.0", port=main_port)

if __name__ == "__main__":
    main()
