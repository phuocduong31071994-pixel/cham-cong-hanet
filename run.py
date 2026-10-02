import os
import sys

def main():
    port = os.environ.get("PORT", "5000")
    bind_args = ["-b", f"0.0.0.0:{port}"]
    if str(port) != "5000":
        bind_args.extend(["-b", "0.0.0.0:5000"])

    cmd = [
        sys.executable, "-m", "gunicorn",
        "-w", "2",
        *bind_args,
        "--timeout", "120",
        "--access-logfile", "-",
        "--error-logfile", "-",
        "app:app"
    ]
    print(f"Starting Gunicorn with bindings: {bind_args}...", flush=True)
    os.execv(sys.executable, cmd)

if __name__ == "__main__":
    main()
