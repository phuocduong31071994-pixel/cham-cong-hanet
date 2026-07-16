import os
import threading
import time
from datetime import datetime, date, timezone, timedelta
import logging
from flask import Flask, render_template, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'kimq-secret-key-1289471928')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'Admin@KimQ')
HANET_TOKEN = os.getenv('HANET_TOKEN', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjMyNDA3MzYyODk0Njg3MTEwMDAiLCJlbWFpbCI6ImhyQGtpbXEudGVjaCIsImNsaWVudF9pZCI6ImZiOWJlMjE3ZDZjNTlmZjQ3MGM5NWYxMDdhYzRhYWI0IiwidHlwZSI6ImF1dGhvcml6YXRpb25fY29kZSIsImlhdCI6MTc4NDAxNDAxMiwiZXhwIjoxODE1NTUwMDEyfQ.7A0TP0g_LbmJhalHoZFASZG9FSsKLyo4PrBl90Rupsg')
HANET_PLACE_ID = os.getenv('HANET_PLACE_ID', '997723')

# Configure Database: Use PostgreSQL on Railway if available, otherwise fallback to SQLite locally
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    # SQL Alchemy requires postgresql:// instead of postgres:// from older configurations
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///attendance.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
class Setting(db.Model):
    __tablename__ = 'settings'
    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.Text, nullable=False)

def get_admin_password():
    try:
        setting = Setting.query.filter_by(key='admin_password').first()
        if setting:
            return setting.value
    except Exception as e:
        logging.error(f"Error querying admin_password setting: {e}")
    return os.getenv('ADMIN_PASSWORD', 'Admin@KimQ')

def get_ceo_password():
    try:
        setting = Setting.query.filter_by(key='ceo_password').first()
        if setting:
            return setting.value
    except Exception as e:
        logging.error(f"Error querying ceo_password setting: {e}")
    return os.getenv('CEO_PASSWORD', 'CEO@KimQ')

def get_dates_from_range(date_str):
    # Expects "DD/MM/YYYY" or "DD/MM/YYYY to DD/MM/YYYY"
    date_str = date_str.strip()
    if not date_str:
        return []
    if " to " in date_str:
        parts = date_str.split(" to ")
        if len(parts) == 2:
            try:
                start_dt = datetime.strptime(parts[0].strip(), "%d/%m/%Y")
                end_dt = datetime.strptime(parts[1].strip(), "%d/%m/%Y")
                dates = []
                curr = start_dt
                while curr <= end_dt:
                    dates.append(curr)
                    curr += timedelta(days=1)
                return dates
            except Exception as e:
                logging.error(f"Error parsing date range {date_str}: {e}")
                return []
    # Single date
    try:
        dt = datetime.strptime(date_str, "%d/%m/%Y")
        return [dt]
    except Exception as e:
        logging.error(f"Error parsing single date {date_str}: {e}")
        return []

class CheckIn(db.Model):
    __tablename__ = 'checkins'
    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.String(100), nullable=True)
    alias_id = db.Column(db.String(100), nullable=True)
    person_name = db.Column(db.String(200), nullable=False)
    time = db.Column(db.DateTime, default=lambda: datetime.now(timezone(timedelta(hours=7))).replace(tzinfo=None), nullable=False)
    place_id = db.Column(db.String(100), nullable=True)
    place_name = db.Column(db.String(200), nullable=True)
    device_id = db.Column(db.String(100), nullable=True)
    device_name = db.Column(db.String(200), nullable=True)
    avatar_url = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "person_id": self.person_id,
            "alias_id": self.alias_id,
            "person_name": self.person_name,
            # Format time in local/friendly ISO format (dd/MM/yyyy HH:mm:ss)
            "time": self.time.strftime('%d/%m/%Y %H:%M:%S'),
            "place_id": self.place_id,
            "place_name": self.place_name,
            "device_id": self.device_id,
            "device_name": self.device_name,
            "avatar_url": self.avatar_url
        }

class Employee(db.Model):
    __tablename__ = 'employee'
    person_id = db.Column(db.String(100), primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    alias_id = db.Column(db.String(100), nullable=True)
    pin = db.Column(db.String(50), nullable=True)
    avatar_url = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            "person_id": self.person_id,
            "name": self.name,
            "alias_id": self.alias_id,
            "pin": self.pin,
            "avatar_url": self.avatar_url
        }

class AttendanceRequest(db.Model):
    __tablename__ = 'attendance_requests'
    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.String(100), nullable=False)
    person_name = db.Column(db.String(200), nullable=False)
    date = db.Column(db.String(50), nullable=False) # Format DD/MM/YYYY
    request_type = db.Column(db.String(50), nullable=False) # 'checkin', 'checkout', 'both'
    reason = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default='pending', nullable=False) # 'pending', 'approved', 'rejected'
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone(timedelta(hours=7))).replace(tzinfo=None), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "person_id": self.person_id,
            "person_name": self.person_name,
            "date": self.date,
            "request_type": self.request_type,
            "reason": self.reason,
            "status": self.status,
            "created_at": self.created_at.strftime('%d/%m/%Y %H:%M:%S')
        }

# Seed dummy data if empty
def seed_data():
    # Mock seeding disabled
    pass

# Create DB Tables
with app.app_context():
    db.create_all()
    # Auto-drop unique pin constraint in PostgreSQL and ensure avatar_url column exists
    if "postgresql" in app.config.get('SQLALCHEMY_DATABASE_URI', ''):
        try:
            from sqlalchemy import text
            db.session.execute(text("ALTER TABLE employees DROP CONSTRAINT IF EXISTS employees_pin_key CASCADE;"))
            db.session.execute(text("ALTER TABLE checkins ADD COLUMN IF NOT EXISTS avatar_url TEXT;"))
            db.session.execute(text("ALTER TABLE employee ADD COLUMN IF NOT EXISTS avatar_url TEXT;"))
            db.session.commit()
            logging.info("PostgreSQL Schema Check: Dropped unique pin key and ensured checkins & employee avatar_url columns exist.")
        except Exception as db_err:
            db.session.rollback()
            logging.error(f"Error executing schema migrations in PostgreSQL: {db_err}")
    seed_data()
    
    # One-off clean up: Delete all Leave and WFH requests and checkin records
    try:
        deleted_reqs = AttendanceRequest.query.filter(AttendanceRequest.request_type.in_(['leave', 'wfh'])).delete(synchronize_session=False)
        deleted_checkins = CheckIn.query.filter(
            (CheckIn.place_name.in_(['Nghỉ phép (P)', 'Work From Home (H)', 'Work From Home', 'Nghỉ phép'])) |
            (CheckIn.device_name.like('%Nghỉ phép%')) |
            (CheckIn.device_name.like('%Work From Home%')) |
            (CheckIn.device_name.like('%Work from home%'))
        ).delete(synchronize_session=False)
        db.session.commit()
        if deleted_reqs > 0 or deleted_checkins > 0:
            logging.info(f"Database clean: deleted {deleted_reqs} leave/wfh requests and {deleted_checkins} simulated checkins.")
    except Exception as clean_err:
        db.session.rollback()
        logging.error(f"Error cleaning up database: {clean_err}")

# Webpage Route
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/clear-db', methods=['GET'])
def clear_db():
    try:
        db.session.query(CheckIn).delete()
        db.session.commit()
        return "Da lam sach database thanh cong! Hay load lai trang chu de kiem tra.", 200
    except Exception as e:
        return f"Loi: {str(e)}", 500

# Webhook Endpoint (Receives Post Requests from Hanet AI Camera)
@app.route('/webhook/hanet', methods=['POST'])
def hanet_webhook():
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "Request body is empty"}), 400

        logging.info(f"Incoming Webhook Payload: {data}")

        # Normalize fields
        event_data = data.get("data") if isinstance(data.get("data"), dict) else data
        
        person_id = event_data.get("personID") or event_data.get("person_id")
        alias_id = event_data.get("aliasID") or event_data.get("alias_id") or event_data.get("alias")
        person_name = event_data.get("personName") or event_data.get("person_name")
        place_id = event_data.get("placeID") or event_data.get("place_id") or "997723"
        place_name = event_data.get("placeName") or event_data.get("place_name") or "Văn phòng Hanet"
        device_id = event_data.get("deviceID") or event_data.get("device_id")
        device_name = event_data.get("deviceName") or event_data.get("device_name") or "Camera AI"
        avatar_url = event_data.get("faceImageURL") or event_data.get("face_image_url") or event_data.get("avatar") or event_data.get("faceImage")

        raw_time = event_data.get("time") or data.get("timestamp")
        
        # Determine datetime
        if raw_time:
            try:
                timestamp_sec = int(raw_time)
                if timestamp_sec > 9999999999: # in ms
                    timestamp_sec = timestamp_sec // 1000
                # Convert UTC timestamp to Vietnam Time (UTC+7)
                utc_time = datetime.fromtimestamp(timestamp_sec, tz=timezone.utc)
                checkin_time = utc_time.astimezone(timezone(timedelta(hours=7))).replace(tzinfo=None)
            except (ValueError, TypeError):
                checkin_time = datetime.now(timezone(timedelta(hours=7))).replace(tzinfo=None)
        else:
            checkin_time = datetime.now(timezone(timedelta(hours=7))).replace(tzinfo=None)

        if not person_name:
            return jsonify({"status": "ignored", "message": "Missing personName"}), 200

        # Save check-in record to database
        new_record = CheckIn(
            person_id=str(person_id) if person_id else None,
            alias_id=str(alias_id) if alias_id else None,
            person_name=str(person_name),
            time=checkin_time,
            place_id=str(place_id),
            place_name=str(place_name),
            device_id=str(device_id) if device_id else None,
            device_name=str(device_name),
            avatar_url=str(avatar_url) if avatar_url else None
        )

        # If this person has been renamed on Hanet, update all their existing records in DB
        if person_id:
            db.session.query(CheckIn).filter(
                CheckIn.person_id == str(person_id),
                CheckIn.person_name != str(person_name)
            ).update({CheckIn.person_name: str(person_name)}, synchronize_session=False)

        db.session.add(new_record)
        db.session.commit()

        logging.info(f"Successfully recorded check-in for {person_name} at {checkin_time}")
        return jsonify({"status": "success", "message": f"Recorded check-in for {person_name}"}), 200

    except Exception as e:
        logging.error(f"Error processing webhook: {str(e)}")
        return jsonify({"status": "error", "message": "Internal Server Error"}), 500

LAST_EMPLOYEE_SYNC = 0
LAST_RANGE_SYNC = {}

def sync_employee_names():
    """
    Fetches the current employee list from Hanet and updates their names
    in our database if they have been renamed. Runs in a background thread.
    """
    global LAST_EMPLOYEE_SYNC
    now = time.time()
    if now - LAST_EMPLOYEE_SYNC < 300: # 5 minutes cooldown
        return
    LAST_EMPLOYEE_SYNC = now

    def run_sync():
        with app.app_context():
            try:
                url = "https://partner.hanet.ai/person/getListByPlace"
                payload = {
                    "token": HANET_TOKEN,
                    "placeID": HANET_PLACE_ID,
                    "size": 200
                }
                res = requests.post(url, data=payload, timeout=10)
                if res.status_code == 200:
                    res_json = res.json()
                    if res_json.get("returnCode") == 1:
                        employees = res_json.get("data", [])
                        db_modified = False
                        for emp in employees:
                            p_id = emp.get("personID")
                            p_name = emp.get("name", "").strip()
                            p_alias = emp.get("aliasID", "").strip() if emp.get("aliasID") else None
                            if p_id and p_name:
                                # 1. Update all check-in records for this person if their name changed
                                updated_rows = db.session.query(CheckIn).filter(
                                    CheckIn.person_id == str(p_id),
                                    CheckIn.person_name != p_name
                                ).update({CheckIn.person_name: p_name}, synchronize_session=False)
                                if updated_rows > 0:
                                    db_modified = True
                                # 2. Sync to Employee table
                                db_emp = Employee.query.filter_by(person_id=str(p_id)).first()
                                avatar_val = emp.get("avatar")
                                if not db_emp:
                                    db_emp = Employee(person_id=str(p_id), name=p_name, alias_id=p_alias, avatar_url=avatar_val)
                                    db.session.add(db_emp)
                                    db_modified = True
                                else:
                                    if db_emp.name != p_name or db_emp.alias_id != p_alias or db_emp.avatar_url != avatar_val:
                                        db_emp.name = p_name
                                        db_emp.alias_id = p_alias
                                        db_emp.avatar_url = avatar_val
                                        db_modified = True
                        
                        if db_modified:
                            db.session.commit()
                            logging.info("Successfully synchronized renamed employees from Hanet place list in background.")
                    else:
                        logging.error(f"Hanet getListByPlace Error: {res_json.get('returnMessage')}")
                else:
                    logging.error(f"Failed to fetch user list from Hanet. Status: {res.status_code}")
            except Exception as e:
                logging.error(f"Error in sync_employee_names background thread: {str(e)}")

    threading.Thread(target=run_sync).start()

def sync_hanet_history_for_range(start_date_str, end_date_str):
    """
    Syncs checkin history from Hanet for a specific date range (YYYY-MM-DD)
    in a background thread. Saves new records to the local database.
    """
    global LAST_RANGE_SYNC
    key = (start_date_str, end_date_str)
    now = time.time()
    if key in LAST_RANGE_SYNC and now - LAST_RANGE_SYNC[key] < 60: # 1 minute cooldown per range
        return
    LAST_RANGE_SYNC[key] = now

    def run_sync():
        with app.app_context():
            try:
                # Define Vietnam local timezone (+07:00) to ensure exact local timestamps across environments
                vn_tz = timezone(timedelta(hours=7))
                start_dt = datetime.strptime(f"{start_date_str} 00:00:00", "%Y-%m-%d %H:%M:%S").replace(tzinfo=vn_tz)
                end_dt = datetime.strptime(f"{end_date_str} 23:59:59", "%Y-%m-%d %H:%M:%S").replace(tzinfo=vn_tz)
                
                from_ms = int(start_dt.timestamp() * 1000)
                to_ms = int(end_dt.timestamp() * 1000)

                url = "https://partner.hanet.ai/person/getCheckinByPlaceIdInTimestamp"
                payload = {
                    "token": HANET_TOKEN,
                    "placeID": HANET_PLACE_ID,
                    "from": from_ms,
                    "to": to_ms,
                    "size": 1000
                }
                res = requests.post(url, data=payload, timeout=15)
                if res.status_code == 200:
                    res_json = res.json()
                    if res_json.get("returnCode") == 1:
                        checkins = res_json.get("data", [])
                        
                        # 1. Map person_id to their latest/newest name (list is newest to oldest)
                        latest_names = {}
                        for c in checkins:
                            p_id = c.get("personID")
                            p_name = c.get("personName", c.get("name", "")).strip()
                            if p_id and p_name and c.get("type") != 2:
                                p_id_str = str(p_id)
                                if p_id_str not in latest_names:
                                    latest_names[p_id_str] = p_name
                                    
                        db_modified = False
                        for c in checkins:
                            person_id = c.get("personID")
                            raw_person_name = c.get("personName", c.get("name", "")).strip()
                            
                            # Get latest name or fallback to raw name
                            person_name = latest_names.get(str(person_id)) if person_id else raw_person_name
                            
                            # Only sync registered employees (type == 0 and has personName)
                            if not person_name or c.get("type") == 2:
                                continue
                                
                            checkin_time_ms = c.get("checkinTime")
                            if not checkin_time_ms:
                                continue
                                
                            # Convert milliseconds timestamp to Vietnam Naive Datetime
                            timestamp_sec = checkin_time_ms // 1000
                            utc_time = datetime.fromtimestamp(timestamp_sec, tz=timezone.utc)
                            vn_time = utc_time.astimezone(timezone(timedelta(hours=7))).replace(tzinfo=None)
                            
                            # If this person has been renamed on Hanet, update all their existing records in DB
                            if person_id:
                                updated_rows = db.session.query(CheckIn).filter(
                                    CheckIn.person_id == str(person_id),
                                    CheckIn.person_name != person_name
                                ).update({CheckIn.person_name: person_name}, synchronize_session=False)
                                if updated_rows > 0:
                                    db_modified = True
                            
                            # Check if already exists in DB (match by person_id if available, otherwise by name)
                            if person_id:
                                exists = CheckIn.query.filter_by(
                                    person_id=str(person_id),
                                    time=vn_time
                                ).first()
                            else:
                                exists = CheckIn.query.filter_by(
                                    person_name=person_name,
                                    time=vn_time
                                ).first()
                            if not exists:
                                alias_id = c.get("aliasID")
                                place_name = c.get("place", "Văn phòng KimQ")
                                device_id = c.get("deviceID")
                                device_name = c.get("deviceName", "Camera AI")
                                avatar_url = c.get("avatar")
                                
                                new_rec = CheckIn(
                                    person_id=str(person_id) if person_id else None,
                                    alias_id=str(alias_id) if alias_id else None,
                                    person_name=person_name,
                                    time=vn_time,
                                    place_id=str(HANET_PLACE_ID),
                                    place_name=place_name,
                                    device_id=str(device_id) if device_id else None,
                                    device_name=device_name,
                                    avatar_url=avatar_url
                                )
                                db.session.add(new_rec)
                                db_modified = True
                            else:
                                # Backfill avatar_url if it exists but is currently empty/None
                                if not exists.avatar_url and c.get("avatar"):
                                    exists.avatar_url = c.get("avatar")
                                    db_modified = True
                        
                        if db_modified:
                            db.session.commit()
                            logging.info(f"Synced checkins from Hanet in background for range {start_date_str} to {end_date_str}.")
                    else:
                        logging.error(f"Hanet API Error: {res_json.get('returnMessage')}")
                else:
                    logging.error(f"Failed to sync with Hanet API. Status: {res.status_code}")
            except Exception as e:
                logging.error(f"Error in sync_hanet_history_for_range background thread: {str(e)}")

    # Enforce range check before launching thread
    try:
        start_dt = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date_str, '%Y-%m-%d')
        if (end_dt - start_dt).days > 30:
            logging.warning("Sync range skipped: range > 30 days.")
            return
    except ValueError:
        return

    threading.Thread(target=run_sync).start()

# Debug CSDL Endpoint
@app.route('/api/debug-db')
def debug_db():
    try:
        import sqlalchemy as sa
        inspect = sa.inspect(db.engine)
        tables = inspect.get_table_names()
        info = {}
        for t in tables:
            info[t] = [c['name'] for c in inspect.get_columns(t)]
        
        checkins_count = db.session.query(CheckIn).count()
        employees_count = db.session.query(Employee).count()
        
        return jsonify({
            "status": "success",
            "tables": info,
            "checkins_count": checkins_count,
            "employees_count": employees_count
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        })

# JSON API for fetching history & stats
@app.route('/api/checkins', methods=['GET'])
def get_checkins():
    try:
        # Sync employee name changes from Hanet
        sync_employee_names()
        
        is_admin = session.get('is_admin', False)
        search_query = request.args.get('search', '').strip()
        
        date_str = request.args.get('date', '').strip()
        start_date = request.args.get('start_date', '').strip()
        end_date = request.args.get('end_date', '').strip()

        # Parse date range from inputs
        if date_str:
            if " to " in date_str:
                parts = date_str.split(" to ")
                start_date = parts[0].strip()
                end_date = parts[1].strip()
            else:
                start_date = date_str
                end_date = date_str

        today_str = datetime.now(timezone(timedelta(hours=7))).strftime('%Y-%m-%d')
        if not start_date:
            start_date = today_str
        if not end_date:
            end_date = today_str

        # Enforce maximum 30 days range check in the backend
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            if (end_dt - start_dt).days > 30:
                return jsonify({"status": "error", "message": "Khoảng thời gian chọn không được vượt quá 30 ngày (1 tháng)"}), 400
        except ValueError:
            return jsonify({"status": "error", "message": "Định dạng ngày tháng không hợp lệ!"}), 400

        # Perform automatic sync for this range
        sync_hanet_history_for_range(start_date, end_date)

        # Anyone can view all check-ins (public access)
        query = CheckIn.query
        valid_pin = False

        # Filter by search query if provided
        if search_query:
            # Find matching employee person_ids from Employee table (to also match by alias_id)
            matching_emp_ids = [e.person_id for e in Employee.query.filter(
                (Employee.name.ilike(f"%{search_query}%")) |
                (Employee.alias_id.ilike(f"%{search_query}%"))
            ).all()]

            query = query.filter(
                (CheckIn.person_name.ilike(f"%{search_query}%")) | 
                (CheckIn.alias_id.ilike(f"%{search_query}%")) |
                (CheckIn.person_id.ilike(f"%{search_query}%")) |
                (CheckIn.person_id.in_(matching_emp_ids))
            )

        # Filter by date range (Vietnam local time)
        end_dt_end = datetime.combine(end_dt.date(), datetime.max.time())
        query = query.filter(CheckIn.time >= start_dt, CheckIn.time <= end_dt_end)

        # Get latest records first
        records = query.order_by(CheckIn.time.desc()).all()

        # Calculate Statistics for the selected date range/search records
        total_today = len(records)
        unique_today = len(set(c.person_name for c in records))
        
        latest_time = "Chưa có"
        if records:
            latest_time = max(c.time for c in records).strftime('%H:%M:%S')

        # Checkin Distribution by hour for the selected records
        hour_counts = [0] * 24
        for c in records:
            hour_counts[c.time.hour] += 1

        stats = {
            "total_today": total_today,
            "unique_today": unique_today,
            "latest_time": latest_time,
            "hour_chart": hour_counts
        }

        # Backfill alias_id and avatar_url from synced Employee records if missing on the CheckIn record itself
        emp_data = {emp.person_id: {"alias_id": emp.alias_id, "avatar_url": emp.avatar_url} for emp in Employee.query.all()}
        
        serialized_data = []
        for r in records:
            d = r.to_dict()
            # Clean string values like "None" or "null"
            if d.get("alias_id") in ["None", "null", "None", None, ""]:
                d["alias_id"] = None
            
            # Backfill from Employee table if present
            if r.person_id in emp_data:
                if not d.get("alias_id"):
                    d["alias_id"] = emp_data[r.person_id]["alias_id"]
                if not d.get("avatar_url") or d.get("avatar_url").strip() == "":
                    d["avatar_url"] = emp_data[r.person_id]["avatar_url"]
                    
            serialized_data.append(d)

        return jsonify({
            "status": "success",
            "data": serialized_data,
            "stats": stats,
            "is_admin": is_admin,
            "valid_pin": valid_pin
        })

    except Exception as e:
        logging.error(f"Error fetching check-ins api: {str(e)}")
        return jsonify({"status": "error", "message": "Failed to fetch records"}), 500

# Unified Login Endpoint (Admin and Employee)
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    if not username or not password:
        return jsonify({"status": "error", "message": "Vui lòng nhập tài khoản và mật khẩu!"}), 400
        
    # 1. Admin & CEO login
    if username.lower() == 'admin':
        if password == get_admin_password():
            session['is_admin'] = True
            session['admin_role'] = 'admin'
            session['employee_id'] = None
            session['employee_name'] = 'Admin'
            return jsonify({
                "status": "success",
                "message": "Đăng nhập Admin thành công",
                "is_admin": True,
                "admin_role": "admin"
            }), 200
        else:
            return jsonify({"status": "error", "message": "Mật khẩu Admin không chính xác!"}), 401
            
    elif username.lower() == 'ceo':
        if password == get_ceo_password():
            session['is_admin'] = True
            session['admin_role'] = 'ceo'
            session['employee_id'] = None
            session['employee_name'] = 'CEO'
            return jsonify({
                "status": "success",
                "message": "Đăng nhập CEO thành công",
                "is_admin": True,
                "admin_role": "ceo"
            }), 200
        else:
            return jsonify({"status": "error", "message": "Mật khẩu CEO không chính xác!"}), 401
            
    # 2. Employee login - Disabled as requested
    return jsonify({"status": "error", "message": "Chỉ chấp nhận tài khoản quản trị (Admin/CEO) đăng nhập!"}), 401

# --- Attendance Requests API ---

# 1. Create a request (Employee only)
@app.route('/api/requests', methods=['POST'])
def create_request():
    employee_id = session.get('employee_id')
    employee_name = session.get('employee_name')
    if not employee_id:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
    data = request.json or {}
    req_date = data.get('date', '').strip() # expected DD/MM/YYYY
    req_type = data.get('request_type', '').strip() # 'checkin', 'checkout', 'both'
    reason = data.get('reason', '').strip()
    
    if not req_date or not req_type:
        return jsonify({"status": "error", "message": "Vui lòng nhập ngày và loại yêu cầu!"}), 400
        
    if req_type not in ['checkin', 'checkout', 'both', 'leave', 'wfh']:
        return jsonify({"status": "error", "message": "Loại yêu cầu không hợp lệ!"}), 400
        
    # Check if a pending request for this employee on this date already exists
    exists = AttendanceRequest.query.filter_by(
        person_id=employee_id,
        date=req_date,
        status='pending'
    ).first()
    if exists:
        return jsonify({"status": "error", "message": "Bạn đã gửi yêu cầu cho ngày này và đang chờ duyệt!"}), 400
        
    req = AttendanceRequest(
        person_id=employee_id,
        person_name=employee_name,
        date=req_date,
        request_type=req_type,
        reason=reason
    )
    db.session.add(req)
    db.session.commit()
    
    return jsonify({"status": "success", "message": "Gửi yêu cầu bổ sung công thành công!"}), 201

# 2. Get requests list (Admin gets all, Employee gets their own)
@app.route('/api/requests', methods=['GET'])
def get_requests():
    is_admin = session.get('is_admin', False)
    employee_id = session.get('employee_id')
    
    if not is_admin and not employee_id:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
    if is_admin:
        reqs = AttendanceRequest.query.order_by(AttendanceRequest.created_at.desc()).all()
    else:
        reqs = AttendanceRequest.query.filter_by(person_id=employee_id).order_by(AttendanceRequest.created_at.desc()).all()
        
    return jsonify({
        "status": "success",
        "data": [r.to_dict() for r in reqs]
    }), 200

# 3. Action on request (Admin only: Approve or Reject)
@app.route('/api/requests/<int:request_id>/action', methods=['POST'])
def action_request(request_id):
    if not session.get('is_admin', False):
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
    data = request.json or {}
    action = data.get('action', '').strip() # 'approve', 'reject'
    
    if action not in ['approve', 'reject']:
        return jsonify({"status": "error", "message": "Hành động không hợp lệ!"}), 400
        
    req = AttendanceRequest.query.get(request_id)
    if not req:
        return jsonify({"status": "error", "message": "Yêu cầu không tồn tại!"}), 404
        
    if req.status != 'pending':
        return jsonify({"status": "error", "message": "Yêu cầu này đã được xử lý trước đó!"}), 400
        
    role = session.get('admin_role', 'admin') # 'admin' or 'ceo'
    
    if action == 'reject':
        req.status = 'rejected_' + role
        db.session.commit()
        return jsonify({"status": "success", "message": "Từ chối yêu cầu thành công!"}), 200
        
    # Action is approve
    req.status = 'approved_' + role
    
    # Parse date range or single date
    dates = get_dates_from_range(req.date)
    if not dates:
        return jsonify({"status": "error", "message": "Định dạng ngày trong yêu cầu không hợp lệ!"}), 400
        
    # Find employee's alias_id
    emp = Employee.query.filter_by(person_id=req.person_id).first()
    alias_id = emp.alias_id if emp else None
    
    role_label = "CEO" if role == 'ceo' else "Admin"
    
    for dt in dates:
        day = dt.day
        month = dt.month
        year = dt.year
        
        # Add check-in records:
        # Vào (09:00:00)
        if req.request_type in ['checkin', 'both', 'leave', 'wfh']:
            place_name = "Bổ sung công (Hệ thống)"
            device_name = f"Yêu cầu: Bổ sung giờ vào [{role_label}]"
            if req.request_type == 'both':
                place_name = "Bổ sung công (Hệ thống)"
                device_name = f"Yêu cầu: Bổ sung cả hai [{role_label}]"
            elif req.request_type == 'leave':
                place_name = "Nghỉ phép (P)"
                device_name = f"Yêu cầu: Nghỉ phép [{role_label}]"
            elif req.request_type == 'wfh':
                place_name = "Work From Home (H)"
                device_name = f"Yêu cầu: Work From Home [{role_label}]"

            time_vào = datetime(year, month, day, 9, 0, 0)
            c_in = CheckIn(
                person_id=req.person_id,
                alias_id=alias_id,
                person_name=req.person_name,
                time=time_vào,
                place_id="997723",
                place_name=place_name,
                device_id="system",
                device_name=device_name,
                avatar_url=""
            )
            db.session.add(c_in)
            
        # Ra (18:00:00)
        if req.request_type in ['checkout', 'both', 'leave', 'wfh']:
            place_name = "Bổ sung công (Hệ thống)"
            device_name = f"Yêu cầu: Bổ sung giờ ra [{role_label}]"
            if req.request_type == 'both':
                place_name = "Bổ sung công (Hệ thống)"
                device_name = f"Yêu cầu: Bổ sung cả hai [{role_label}]"
            elif req.request_type == 'leave':
                place_name = "Nghỉ phép (P)"
                device_name = f"Yêu cầu: Nghỉ phép [{role_label}]"
            elif req.request_type == 'wfh':
                place_name = "Work From Home (H)"
                device_name = f"Yêu cầu: Work From Home [{role_label}]"

            time_ra = datetime(year, month, day, 18, 0, 0)
            c_out = CheckIn(
                person_id=req.person_id,
                alias_id=alias_id,
                person_name=req.person_name,
                time=time_ra,
                place_id="997723",
                place_name=place_name,
                device_id="system",
                device_name=device_name,
                avatar_url=""
            )
            db.session.add(c_out)
        
    db.session.commit()
    return jsonify({"status": "success", "message": "Duyệt yêu cầu thành công!"}), 200

# Admin Change Password Endpoint
@app.route('/api/admin/change-password', methods=['POST'])
def admin_change_password():
    if not session.get('is_admin', False):
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
    role = session.get('admin_role', 'admin') # 'admin' or 'ceo'
    data = request.json or {}
    current_pw = data.get('current_password')
    new_pw = data.get('new_password')
    
    if not current_pw or not new_pw:
        return jsonify({"status": "error", "message": "Thiếu thông tin yêu cầu!"}), 400
        
    correct_current = get_admin_password() if role == 'admin' else get_ceo_password()
    if current_pw != correct_current:
        return jsonify({"status": "error", "message": f"Mật khẩu hiện tại của {role.upper()} không chính xác!"}), 400
        
    if len(new_pw) < 6:
        return jsonify({"status": "error", "message": "Mật khẩu mới phải có tối thiểu 6 ký tự!"}), 400
        
    try:
        setting_key = 'admin_password' if role == 'admin' else 'ceo_password'
        setting = Setting.query.filter_by(key=setting_key).first()
        if not setting:
            setting = Setting(key=setting_key, value=new_pw)
            db.session.add(setting)
        else:
            setting.value = new_pw
        db.session.commit()
        return jsonify({"status": "success", "message": f"Đổi mật khẩu {role.upper()} thành công!"}), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error saving {role} password: {e}")
        return jsonify({"status": "error", "message": "Lỗi cơ sở dữ liệu khi lưu mật khẩu mới."}), 500

# Logout Endpoint
@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('is_admin', None)
    session.pop('admin_role', None)
    session.pop('employee_id', None)
    session.pop('employee_name', None)
    return jsonify({"status": "success", "message": "Đã đăng xuất"}), 200

# Session Status Endpoint
@app.route('/api/status', methods=['GET'])
def session_status():
    return jsonify({
        "is_admin": session.get('is_admin', False),
        "admin_role": session.get('admin_role'),
        "employee_id": session.get('employee_id'),
        "employee_name": session.get('employee_name')
    })

# Temporary Debug DB Endpoint
@app.route('/api/admin/debug-db', methods=['GET'])
def admin_debug_db():
    uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if "@" in uri:
        parts = uri.split("@")
        uri = parts[0].split(":")[0] + "://***:***@" + parts[1]
    
    # Return env keys to verify if DATABASE_URL is injected
    env_keys = list(os.environ.keys())
    return jsonify({
        "uri": uri,
        "env_keys": env_keys,
        "has_db_url": "DATABASE_URL" in os.environ,
        "db_url_val_len": len(os.environ.get("DATABASE_URL", ""))
    })

# Admin Manual Check-In Endpoint
@app.route('/api/admin/checkin/manual', methods=['POST'])
def admin_manual_checkin():
    try:
        if not session.get('is_admin', False):
            return jsonify({"status": "error", "message": "Từ chối truy cập: Chỉ admin mới có quyền thực hiện"}), 403
            
        data = request.json or {}
        person_name = data.get('person_name', '').strip()
        alias_id = data.get('alias_id', '').strip()
        date_str = data.get('date', '').strip()  # YYYY-MM-DD
        time_str = data.get('time', '').strip()  # HH:MM:SS
        
        if not person_name or not date_str or not time_str:
            return jsonify({"status": "error", "message": "Vui lòng nhập đầy đủ Tên, Ngày và Giờ!"}), 400
            
        # Parse datetime
        datetime_str = f"{date_str} {time_str}"
        checkin_time = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
        
        new_record = CheckIn(
            person_id=None,
            alias_id=alias_id if alias_id else None,
            person_name=person_name,
            time=checkin_time,
            place_id="997723",
            place_name="Văn phòng KimQ",
            device_id="manual",
            device_name="Thêm thủ công bởi Admin",
            avatar_url=None
        )
        
        db.session.add(new_record)
        db.session.commit()
        
        return jsonify({"status": "success", "message": f"Đã thêm công thủ công cho {person_name}"}), 200
        
    except Exception as e:
        logging.error(f"Error saving manual checkin: {str(e)}")
        return jsonify({"status": "error", "message": f"Lỗi hệ thống: {str(e)}"}), 500

# Admin Get All Employees Endpoint (Syncs automatically on load)
@app.route('/api/admin/employees', methods=['GET'])
def admin_get_employees():
    if not session.get('is_admin', False):
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    
    try:
        # Sync employee list synchronously from Hanet to ensure latest data is loaded
        try:
            url = "https://partner.hanet.ai/person/getListByPlace"
            payload = {
                "token": HANET_TOKEN,
                "placeID": HANET_PLACE_ID,
                "size": 200
            }
            res = requests.post(url, data=payload, timeout=10)
            if res.status_code == 200:
                res_json = res.json()
                if res_json.get("returnCode") == 1:
                    employees_list = res_json.get("data", [])
                    db_modified = False
                    for emp in employees_list:
                        p_id = emp.get("personID")
                        p_name = emp.get("name", "").strip()
                        p_alias = emp.get("aliasID", "").strip() if emp.get("aliasID") else None
                        if p_id and p_name:
                            db_emp = Employee.query.filter_by(person_id=str(p_id)).first()
                            if not db_emp:
                                db_emp = Employee(person_id=str(p_id), name=p_name, alias_id=p_alias)
                                db.session.add(db_emp)
                                db_modified = True
                            else:
                                if db_emp.name != p_name or db_emp.alias_id != p_alias:
                                    db_emp.name = p_name
                                    db_emp.alias_id = p_alias
                                    db_modified = True
                    if db_modified:
                        db.session.commit()
                        logging.info("Synced employees list synchronously on admin load.")
        except Exception as sync_err:
            logging.error(f"Error syncing employees synchronously: {sync_err}")

        employees = Employee.query.order_by(Employee.name.asc()).all()
        return jsonify({
            "status": "success",
            "data": [e.to_dict() for e in employees]
        }), 200
    except Exception as e:
        logging.error(f"Error fetching employees: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Admin Update/Assign Employee PIN Endpoint
@app.route('/api/admin/employees/pin', methods=['POST'])
def admin_update_employee_pin():
    if not session.get('is_admin', False):
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    
    data = request.json or {}
    person_id = data.get('person_id')
    pin = data.get('pin', '').strip()
    
    if not person_id:
        return jsonify({"status": "error", "message": "Missing person_id"}), 400
        
    # Enforce exactly 6 numeric digits validation if PIN is set
    if pin:
        if not pin.isdigit() or len(pin) != 6:
            return jsonify({"status": "error", "message": "Mã PIN phải gồm đúng 6 chữ số (0-9)!"}), 400
            
    emp = Employee.query.filter_by(person_id=person_id).first()
    if emp:
        emp.pin = pin if pin else None
        db.session.commit()
        return jsonify({"status": "success", "message": "Cập nhật Mã PIN thành công"}), 200
        
    return jsonify({"status": "error", "message": "Không tìm thấy nhân sự"}), 404



# Admin Reset Employee PIN Endpoint
@app.route('/api/admin/employees/reset-pin', methods=['POST'])
def admin_reset_employee_pin():
    if not session.get('is_admin', False):
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    
    data = request.json or {}
    person_id = data.get('person_id')
    
    if not person_id:
        return jsonify({"status": "error", "message": "Missing person_id"}), 400
        
    emp = Employee.query.filter_by(person_id=person_id).first()
    if emp:
        emp.pin = None
        db.session.commit()
        return jsonify({"status": "success", "message": "Đã reset mã PIN thành công!"}), 200
        
    return jsonify({"status": "error", "message": "Không tìm thấy nhân sự"}), 404


# Employee Change PIN Endpoint
@app.route('/api/employee/change-pin', methods=['POST'])
def employee_change_pin():
    emp_id = session.get('employee_id')
    if not emp_id:
        return jsonify({"status": "error", "message": "Bạn chưa đăng nhập với tư cách nhân viên!"}), 401
        
    data = request.json or {}
    current_pin = data.get('current_pin', '').strip()
    new_pin = data.get('new_pin', '').strip()
    
    if not current_pin or not new_pin:
        return jsonify({"status": "error", "message": "Vui lòng nhập đầy đủ mã PIN hiện tại và mã PIN mới!"}), 400
        
    if not new_pin.isdigit() or len(new_pin) != 6:
        return jsonify({"status": "error", "message": "Mã PIN mới phải là chuỗi gồm đúng 6 chữ số!"}), 400
        
    try:
        emp = Employee.query.filter_by(person_id=str(emp_id)).first()
        if not emp:
            return jsonify({"status": "error", "message": "Không tìm thấy thông tin nhân viên!"}), 404
            
        if emp.pin != current_pin:
            return jsonify({"status": "error", "message": "Mã PIN hiện tại không chính xác!"}), 400
            
        emp.pin = new_pin
        db.session.commit()
        return jsonify({"status": "success", "message": "Đổi mã PIN thành công!"}), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error employee changing pin: {e}")
        return jsonify({"status": "error", "message": "Đã xảy ra lỗi hệ thống!"}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
