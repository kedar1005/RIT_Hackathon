import hashlib
import json
import os
import re
from collections import Counter
from datetime import datetime
from functools import wraps
from io import BytesIO

from flask import Flask, flash, g, redirect, render_template, request, send_file, send_from_directory, session, url_for
from werkzeug.utils import secure_filename

from auth.agent_auth import DEPARTMENTS
from ml.model_tracker import (
    get_agent_leaderboard_chart,
    get_category_distribution_chart,
    get_daily_trend_chart,
    get_urgency_donut,
)
from ml.image_model import dual_predict
from ml.model import CATEGORIES, check_and_retrain, predict_full
from plotly.io import to_html
from utils.data_utils import (
    add_correction,
    add_agent,
    add_complaint,
    add_feedback,
    add_ticket,
    add_user,
    authenticate_agent,
    authenticate_user,
    check_duplicate,
    cleanup_sessions,
    create_session,
    delete_session,
    export_complaints_csv,
    get_active_session,
    get_agent_leaderboard,
    get_all_corrections,
    get_all_workers,
    get_connection,
    get_available_cities_with_coords,
    get_complaint_by_id,
    get_complaint_stats,
    get_complaints_with_coords,
    get_correction_count_since_last_training,
    get_daily_trend,
    get_departments_without_active_workers,
    get_all_complaints,
    get_model_versions,
    get_tickets_by_department,
    get_tickets_for_admin,
    get_unread_count_admin,
    get_unread_count_user,
    get_unread_count_worker,
    get_user_complaints,
    get_user_tickets,
    init_database,
    is_worker_blocked,
    mark_tickets_read_admin,
    mark_tickets_read_user,
    mark_tickets_read_worker,
    search_complaints,
    unblock_worker,
    update_complaint_status,
    warn_worker,
    block_worker,
    restore_worker,
    get_pending_workers,
    get_workers_by_department,
)
from utils.geo_utils import extract_gps_from_image, geocode_address, get_image_hash_from_bytes


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "assets", "uploaded_images")
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
URGENCY_OPTIONS = ["Low", "Medium", "High"]
CATEGORY_TO_DEPT = {
    "Roads & Potholes": "Roads & Infrastructure",
    "Streetlight & Electricity": "Electricity & Streetlights",
    "Garbage & Waste Management": "Sanitation & Waste",
    "Water Supply Issues": "Water Supply",
    "Drainage & Water Logging": "Drainage & Sewerage",
    "Tree Fall & Maintenance": "Parks & Tree Maintenance",
    "Traffic & Parking": "Traffic Management",
    "Public Safety & Others": "Public Safety & General",
}

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "citizen-ai-flask-dev")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
PAGE_SIZE = 5


def _hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def _validate_email(email):
    return bool(re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email or ""))


def _validate_password(password):
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    if not re.search(r"[a-zA-Z]", password):
        return False, "Password must contain at least one letter."
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one number."
    return True, ""


def _validate_agent_id(agent_id):
    return bool(re.match(r"^AGT\d{4}$", (agent_id or "").upper()))


def _allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _save_uploaded_image(file_storage, user_id):
    if not file_storage or not file_storage.filename or not _allowed_file(file_storage.filename):
        return None, None

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    extension = file_storage.filename.rsplit(".", 1)[1].lower()
    filename = secure_filename(f"complaint_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{extension}")
    save_path = os.path.join(UPLOAD_DIR, filename)
    image_bytes = file_storage.read()
    with open(save_path, "wb") as handle:
        handle.write(image_bytes)
    return save_path, image_bytes


def _serialize_map_points(points):
    return json.dumps([
        {
            "id": point.get("id"),
            "lat": point.get("lat"),
            "lon": point.get("lon"),
            "category": point.get("category"),
            "status": point.get("status"),
            "urgency": point.get("ai_urgency"),
            "address": point.get("address"),
            "created_at": point.get("created_at"),
        }
        for point in points
    ])


def _build_media_url(path_value):
    if not path_value:
        return None
    normalized = os.path.abspath(path_value)
    if not normalized.startswith(os.path.abspath(UPLOAD_DIR)):
        return None
    filename = os.path.basename(normalized)
    return url_for("uploaded_media", filename=filename)


def _human_duration(started_at, completed_at=None):
    if not started_at:
        return None
    try:
        start_dt = datetime.fromisoformat(started_at)
        end_dt = datetime.fromisoformat(completed_at) if completed_at else datetime.now()
        elapsed = end_dt - start_dt
        total_minutes = max(int(elapsed.total_seconds() / 60), 0)
        hours = total_minutes // 60
        minutes = total_minutes % 60
        return f"{hours}h {minutes}m" if hours else f"{minutes}m"
    except Exception:
        return None


def _enrich_complaint(complaint):
    detail = get_complaint_by_id(complaint["id"]) or complaint
    detail["proof_url"] = _build_media_url(detail.get("completion_image"))
    detail["complaint_image_url"] = _build_media_url(detail.get("image_path"))
    detail["work_duration"] = _human_duration(detail.get("work_started_at"), detail.get("work_completed_at"))
    return detail


def _figure_html(fig):
    if fig is None:
        return None
    try:
        return to_html(fig, full_html=False, include_plotlyjs="cdn", config={"displayModeBar": False, "responsive": True})
    except Exception:
        return None


def _paginate_items(items, page):
    total_items = len(items)
    total_pages = max((total_items + PAGE_SIZE - 1) // PAGE_SIZE, 1)
    current_page = min(max(page, 1), total_pages)
    start = (current_page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    return {
        "items": items[start:end],
        "page": current_page,
        "total_pages": total_pages,
        "total_items": total_items,
        "has_prev": current_page > 1,
        "has_next": current_page < total_pages,
        "prev_page": current_page - 1,
        "next_page": current_page + 1,
    }


def _parse_iso_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _filter_analytics_complaints(complaints, date_from=None, date_to=None, department_filter="All", priority_filter="All"):
    filtered = []
    start_date = _parse_iso_date(date_from)
    end_date = _parse_iso_date(date_to)

    for complaint in complaints:
        if department_filter != "All" and (complaint.get("department") or "") != department_filter:
            continue
        if priority_filter != "All" and (complaint.get("ai_urgency") or "") != priority_filter:
            continue

        created_at = complaint.get("created_at")
        created_date = None
        if created_at:
            try:
                created_date = datetime.fromisoformat(str(created_at)).date()
            except Exception:
                created_date = None

        if start_date and (created_date is None or created_date < start_date):
            continue
        if end_date and (created_date is None or created_date > end_date):
            continue
        filtered.append(complaint)

    return filtered


def _build_filtered_stats(complaints):
    by_category_counter = Counter(complaint.get("category") or "Unknown" for complaint in complaints)
    urgency_counter = Counter(complaint.get("ai_urgency") or "Medium" for complaint in complaints)

    resolution_hours = []
    for complaint in complaints:
        created_at = complaint.get("created_at")
        resolved_at = complaint.get("resolved_at")
        if not created_at or not resolved_at:
            continue
        try:
            created_dt = datetime.fromisoformat(str(created_at))
            resolved_dt = datetime.fromisoformat(str(resolved_at))
            resolution_hours.append(max((resolved_dt - created_dt).total_seconds() / 3600, 0))
        except Exception:
            continue

    avg_resolution_hours = sum(resolution_hours) / len(resolution_hours) if resolution_hours else 0

    return {
        "by_category": [
            {"category": category, "count": count}
            for category, count in sorted(by_category_counter.items(), key=lambda item: item[1], reverse=True)
        ],
        "urgency_high": urgency_counter.get("High", 0),
        "urgency_medium": urgency_counter.get("Medium", 0),
        "urgency_low": urgency_counter.get("Low", 0),
        "avg_resolution_hours": avg_resolution_hours,
    }


def _build_filtered_daily_trend(complaints):
    trend_counter = Counter()
    for complaint in complaints:
        created_at = complaint.get("created_at")
        if not created_at:
            continue
        try:
            day = datetime.fromisoformat(str(created_at)).strftime("%Y-%m-%d")
        except Exception:
            continue
        trend_counter[day] += 1

    return [
        {"day": day, "count": trend_counter[day]}
        for day in sorted(trend_counter.keys())
    ]


def _build_filtered_leaderboard(complaints):
    agent_names = {"AGT0001": "System Administrator"}
    for worker in get_all_workers():
        agent_names[worker.get("agent_id")] = worker.get("name") or worker.get("agent_id")

    resolved_counter = Counter()
    for complaint in complaints:
        agent_id = complaint.get("assigned_agent")
        if agent_id and complaint.get("status") == "Resolved":
            resolved_counter[agent_id] += 1

    return [
        {"name": agent_names.get(agent_id, agent_id), "agent_id": agent_id, "total_resolved": count}
        for agent_id, count in resolved_counter.most_common()
    ]


def _build_department_performance(complaints, workers):
    worker_count_by_department = Counter()
    for worker in workers:
        department = (worker.get("department") or "").strip()
        if not department:
            continue
        if worker.get("status") == "blocked":
            continue
        worker_count_by_department[department] += 1

    grouped = {department: [] for department in DEPARTMENTS}
    for complaint in complaints:
        department = complaint.get("department") or "Public Safety & General"
        grouped.setdefault(department, []).append(complaint)

    rows = []
    for department in DEPARTMENTS:
        dept_complaints = grouped.get(department, [])
        total = len(dept_complaints)
        resolved = sum(1 for item in dept_complaints if item.get("status") == "Resolved")
        pending = sum(1 for item in dept_complaints if item.get("status") == "Pending")
        in_progress = sum(1 for item in dept_complaints if item.get("status") == "In Progress")

        hours = []
        for item in dept_complaints:
            created_at = item.get("created_at")
            resolved_at = item.get("resolved_at")
            if not created_at or not resolved_at:
                continue
            try:
                start = datetime.fromisoformat(str(created_at))
                end = datetime.fromisoformat(str(resolved_at))
                hours.append(max((end - start).total_seconds() / 3600, 0))
            except Exception:
                continue

        avg_hours = (sum(hours) / len(hours)) if hours else 0
        resolution_rate = ((resolved / total) * 100) if total else 0

        rows.append(
            {
                "department": department,
                "total": total,
                "resolved": resolved,
                "pending": pending,
                "in_progress": in_progress,
                "avg_hours": round(avg_hours, 1),
                "staff": worker_count_by_department.get(department, 0),
                "resolution_rate": round(resolution_rate, 1),
            }
        )

    return rows


def _build_hod_roster(department_rows, workers):
    supervisors = {}
    fallback_by_department = {}

    for worker in workers:
        department = (worker.get("department") or "").strip()
        if not department:
            continue
        if department not in fallback_by_department:
            fallback_by_department[department] = worker
        if worker.get("role") == "supervisor":
            supervisors[department] = worker

    roster = []
    for row in department_rows:
        if row.get("total", 0) == 0 and row.get("staff", 0) == 0:
            continue
        department = row["department"]
        lead = supervisors.get(department) or fallback_by_department.get(department)
        roster.append(
            {
                "department": department,
                "name": lead.get("name") if lead else "Unassigned",
                "staff": row.get("staff", 0),
                "cases": row.get("total", 0),
                "resolution_rate": row.get("resolution_rate", 0),
            }
        )

    return roster


def login_required(role=None):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if not g.current_user:
                flash("Please sign in to continue.", "error")
                return redirect(url_for("home"))
            if role and g.user_type != role:
                if not (role == "supervisor" and g.is_admin):
                    flash("You do not have access to that page.", "error")
                    return redirect(url_for("home"))
            return view_func(*args, **kwargs)

        return wrapped

    return decorator


@app.before_request
def load_current_user():
    init_database()
    cleanup_sessions()

    g.current_user = None
    g.user_type = None
    g.is_admin = False

    session_id = session.get("session_id")
    if not session_id:
        return

    active = get_active_session(session_id)
    if not active:
        session.clear()
        return

    g.current_user = active["user_data"]
    g.user_type = active["session_info"]["user_type"]
    
    # Map role to user_type if it's an agent/worker
    if g.user_type in ["agent", "worker"]:
        role = g.current_user.get("role")
        if role:
            g.user_type = role
            
    g.is_admin = g.user_type == "agent" and g.current_user.get("agent_id") == "AGT0001"


@app.context_processor
def inject_template_context():
    return {
        "current_user": g.get("current_user"),
        "current_role": g.get("user_type"),
        "is_admin": g.get("is_admin", False),
        "current_year": datetime.now().year,
    }


@app.route("/")
def home():
    stats = get_complaint_stats()
    homepage_totals = {
        "registered_complaints": stats.get("total", 0),
        "resolved_complaints": stats.get("resolved", 0),
        "total_employees": len(get_all_workers()),
        "total_departments": len(DEPARTMENTS),
    }
    return render_template("index.html", totals=homepage_totals)


@app.route("/media/<path:filename>")
def uploaded_media(filename):
    return send_from_directory(UPLOAD_DIR, filename)


@app.route("/logout")
def logout():
    session_id = session.get("session_id")
    if session_id:
        delete_session(session_id)
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("home"))


@app.route("/citizen/login", methods=["GET", "POST"])
def citizen_login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not email or not password:
            flash("Please fill in email and password.", "error")
        elif not _validate_email(email):
            flash("Please enter a valid email address.", "error")
        else:
            user = authenticate_user(email, _hash_password(password))
            if user:
                session["session_id"] = create_session(user["id"], "citizen", duration_minutes=60)
                flash(f"Welcome back, {user['name']}.", "success")
                return redirect(url_for("citizen_dashboard"))
            flash("Invalid email or password.", "error")

    return render_template(
        "auth.html",
        page_title="Citizen Sign In",
        page_subtitle="Report issues, track resolution, and stay updated.",
        form_type="citizen_login",
    )


@app.route("/citizen/register", methods=["GET", "POST"])
def citizen_register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        confirm = request.form.get("confirm_password", "").strip()
        pincode = request.form.get("pincode", "").strip()
        identity_id = request.form.get("identity_id", "").strip()

        if not all([name, email, password, confirm, pincode, identity_id]):
            flash("Please complete all registration fields.", "error")
        elif not pincode.startswith("416"):
            flash("Registration is currently limited to Kolhapur pincodes starting with 416.", "error")
        elif not _validate_email(email):
            flash("Please enter a valid email address.", "error")
        elif password != confirm:
            flash("Passwords do not match.", "error")
        else:
            is_aadhaar = identity_id.isdigit() and len(identity_id) == 12
            is_citizen_id = identity_id.isalnum() and len(identity_id) >= 6
            valid, message = _validate_password(password)
            if not (is_aadhaar or is_citizen_id):
                flash("Enter a valid Aadhaar number or citizen ID.", "error")
            elif not valid:
                flash(message, "error")
            else:
                user_id = add_user(
                    name,
                    email,
                    _hash_password(password),
                    city="Kolhapur",
                    pincode=pincode,
                    identity_id=identity_id,
                )
                if user_id:
                    session["session_id"] = create_session(user_id, "citizen", duration_minutes=60)
                    flash("Account created successfully.", "success")
                    return redirect(url_for("citizen_dashboard"))
                flash("This email is already registered.", "error")

    return render_template(
        "auth.html",
        page_title="Create Citizen Account",
        page_subtitle="Simple registration for reporting and tracking city issues.",
        form_type="citizen_register",
    )


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        agent_id = request.form.get("agent_id", "").strip().upper()
        password = request.form.get("password", "").strip()

        if not agent_id or not password:
            flash("Please fill in all fields.", "error")
        elif not _validate_agent_id(agent_id):
            flash("Agent ID must be in the format AGT0001.", "error")
        elif agent_id == "AGT0001" and password == "admin123":
            session["session_id"] = create_session(0, "agent", duration_minutes=60)
            flash("Admin access granted.", "success")
            return redirect(url_for("admin_dashboard"))
        else:
            agent = authenticate_agent(agent_id, _hash_password(password))
            if agent and agent.get("agent_id") == "AGT0001":
                session["session_id"] = create_session(agent["id"], "agent", duration_minutes=60)
                flash("Admin access granted.", "success")
                return redirect(url_for("admin_dashboard"))
            flash("Invalid admin credentials.", "error")

    return render_template(
        "auth.html",
        page_title="Admin Login",
        page_subtitle="Manage complaints, workers, analytics, and exports.",
        form_type="admin_login",
    )


@app.route("/worker/login", methods=["GET", "POST"])
def worker_login():
    if request.method == "POST":
        agent_id = request.form.get("agent_id", "").strip().upper()
        password = request.form.get("password", "").strip()

        if not agent_id or not password:
            flash("Please fill in all fields.", "error")
        elif not _validate_agent_id(agent_id):
            flash("Agent ID must be in the format AGT0002.", "error")
        else:
            agent = authenticate_agent(agent_id, _hash_password(password))
            if agent:
                role = agent.get("role", "worker")
                session["session_id"] = create_session(agent["id"], role, duration_minutes=60)
                flash(f"Welcome, {agent['name']}.", "success")
                if role == "supervisor":
                    return redirect(url_for("supervisor_dashboard"))
                return redirect(url_for("worker_dashboard"))
            flash("Invalid worker credentials.", "error")

    return render_template(
        "auth.html",
        page_title="Employee Login",
        page_subtitle="Access department complaints and update work progress.",
        form_type="worker_login",
    )


@app.route("/citizen/dashboard", methods=["GET", "POST"])
@login_required(role="citizen")
def citizen_dashboard():
    status_filter = request.args.get("status", "All")
    urgency_filter = request.args.get("urgency", "All")
    search_term = request.args.get("term", "").strip().lower()
    page = request.args.get("page", default=1, type=int)

    if request.method == "POST":
        category = request.form.get("category", "").strip()
        user_urgency = request.form.get("user_urgency", "Medium").strip()
        address = request.form.get("address", "").strip()
        landmark = request.form.get("landmark", "").strip()
        description = request.form.get("description", "").strip()
        uploaded_file = request.files.get("image")

        if not description or len(description) < 10:
            flash("Please describe the issue in at least 10 characters.", "error")
        elif not address:
            flash("Please add the issue location.", "error")
        elif category not in CATEGORIES:
            flash("Please choose a valid complaint category.", "error")
        else:
            image_path, image_bytes = _save_uploaded_image(uploaded_file, g.current_user["id"])
            image_hash = get_image_hash_from_bytes(image_bytes) if image_bytes else None
            lat, lon = None, None

            if image_hash and check_duplicate(image_hash):
                flash("A similar photo already exists in the system. The complaint was still submitted for review.", "warning")
            if image_path:
                exif_lat, exif_lon = extract_gps_from_image(image_path)
                if exif_lat and exif_lon:
                    lat, lon = exif_lat, exif_lon
            if lat is None and address:
                geo_lat, geo_lon = geocode_address(address)
                if geo_lat and geo_lon:
                    lat, lon = geo_lat, geo_lon

            try:
                ai_result = dual_predict(description, category, image_path) if image_path else predict_full(description, category)
            except Exception:
                ai_result = predict_full(description, category)

            complaint_id = add_complaint(
                user_id=g.current_user["id"],
                category=ai_result.get("category", category),
                description=description,
                address=address,
                landmark=landmark,
                image_path=image_path,
                image_hash=image_hash,
                lat=lat,
                lon=lon,
                ai_urgency=ai_result.get("urgency", "Medium"),
                user_urgency=user_urgency,
                ai_confidence=ai_result.get("confidence", 0.0),
                ai_method=ai_result.get("method", "text"),
                estimated_resolution=ai_result.get("resolution_time", ""),
                department=CATEGORY_TO_DEPT.get(ai_result.get("category", category), "Public Safety & General"),
            )
            if complaint_id:
                flash(f"Complaint submitted successfully. Tracking ID: CMP-{complaint_id:04d}", "success")
                return redirect(url_for("citizen_dashboard"))
            flash("The complaint could not be saved. Please try again.", "error")

    complaints = get_user_complaints(g.current_user["id"])
    filtered_complaints = complaints
    if status_filter != "All":
        filtered_complaints = [c for c in filtered_complaints if c.get("status") == status_filter]
    if urgency_filter != "All":
        filtered_complaints = [c for c in filtered_complaints if c.get("ai_urgency") == urgency_filter]
    if search_term:
        filtered_complaints = [
            c for c in filtered_complaints
            if search_term in (c.get("description") or "").lower()
            or search_term in (c.get("category") or "").lower()
            or search_term in (c.get("address") or "").lower()
        ]
    pagination = _paginate_items(filtered_complaints, page)
    complaint_details = {complaint["id"]: _enrich_complaint(complaint) for complaint in complaints}
    tickets = get_user_tickets(g.current_user["id"])
    for ticket in tickets:
        detail = get_complaint_by_id(ticket.get("complaint_id")) if ticket.get("complaint_id") else None
        ticket["proof_url"] = _build_media_url(detail.get("completion_image")) if detail else None
    unread_tickets = get_unread_count_user(g.current_user["id"])
    if unread_tickets:
        mark_tickets_read_user(g.current_user["id"])

    return render_template(
        "citizen_dashboard.html",
        categories=CATEGORIES,
        urgencies=URGENCY_OPTIONS,
        complaints=pagination["items"],
        complaint_stats={
            "total": len(complaints),
            "pending": len([c for c in complaints if c.get("status") == "Pending"]),
            "in_progress": len([c for c in complaints if c.get("status") == "In Progress"]),
            "resolved": len([c for c in complaints if c.get("status") == "Resolved"]),
        },
        complaint_details=complaint_details,
        tickets=tickets,
        unread_tickets=unread_tickets,
        selected_status=status_filter,
        selected_urgency=urgency_filter,
        search_term=search_term,
        pagination=pagination,
    )


@app.route("/citizen/complaints/<int:complaint_id>/feedback", methods=["POST"])
@login_required(role="citizen")
def citizen_feedback(complaint_id):
    rating = request.form.get("rating", "").strip()
    comment = request.form.get("comment", "").strip()
    if not rating.isdigit() or not (1 <= int(rating) <= 5):
        flash("Please choose a rating from 1 to 5.", "error")
    elif add_feedback(complaint_id, g.current_user["id"], int(rating), comment):
        flash("Feedback submitted. Thank you.", "success")
    else:
        flash("Feedback could not be saved.", "error")
    return redirect(url_for("citizen_dashboard"))


@app.route("/citizen/complaints/<int:complaint_id>/ticket", methods=["POST"])
@login_required(role="citizen")
def citizen_ticket(complaint_id):
    message = request.form.get("message", "").strip()
    department = request.form.get("department", "").strip()
    if not message:
        flash("Please enter a ticket message.", "error")
    elif add_ticket(complaint_id, g.current_user["id"], message, department):
        flash("Support ticket submitted.", "success")
    else:
        flash("Ticket could not be submitted.", "error")
    return redirect(url_for("citizen_dashboard"))


@app.route("/admin/dashboard")
@login_required(role="agent")
def admin_dashboard():
    if not g.is_admin:
        flash("Admin access is required.", "error")
        return redirect(url_for("home"))

    term = request.args.get("term", "").strip()
    status_filter = request.args.get("status", "All")
    urgency_filter = request.args.get("urgency", "All")
    category_filter = request.args.get("category", "All")
    city_filter = request.args.get("city", "All")
    date_from = request.args.get("date_from", "").strip() or None
    date_to = request.args.get("date_to", "").strip() or None
    analytics_date_from = request.args.get("analytics_date_from", "").strip() or None
    analytics_date_to = request.args.get("analytics_date_to", "").strip() or None
    analytics_department = request.args.get("analytics_department", "All")
    analytics_priority = request.args.get("analytics_priority", "All")
    dept_filter = request.args.get("dept", "All")
    page = request.args.get("page", default=1, type=int)
    unread_admin = get_unread_count_admin()

    complaints = search_complaints(
        term=term,
        status_filter=status_filter,
        urgency_filter=urgency_filter,
        category_filter=category_filter,
        department_filter=dept_filter if dept_filter != "All" else None
    )
    pagination = _paginate_items(complaints, page)
    complaint_details = {complaint["id"]: _enrich_complaint(complaint) for complaint in complaints}
    tickets = get_tickets_for_admin()
    for ticket in tickets:
        detail = get_complaint_by_id(ticket.get("complaint_id")) if ticket.get("complaint_id") else None
        ticket["proof_url"] = _build_media_url(detail.get("completion_image")) if detail else None
        ticket["complaint_image_url"] = _build_media_url(detail.get("image_path")) if detail else None
    if unread_admin:
        mark_tickets_read_admin()

    stats = get_complaint_stats()
    all_complaints = get_all_complaints()
    analytics_complaints = _filter_analytics_complaints(
        all_complaints,
        date_from=analytics_date_from,
        date_to=analytics_date_to,
        department_filter=analytics_department,
        priority_filter=analytics_priority,
    )
    analytics_stats = _build_filtered_stats(analytics_complaints)
    daily_trend = _build_filtered_daily_trend(analytics_complaints)
    leaderboard = _build_filtered_leaderboard(analytics_complaints)
    analytics_workers = get_all_workers()
    analytics_department_rows = _build_department_performance(analytics_complaints, analytics_workers)
    analytics_hod_roster = _build_hod_roster(analytics_department_rows, analytics_workers)
    avg_resolution_hours = analytics_stats.get("avg_resolution_hours", 0)
    avg_resolution_display = f"{avg_resolution_hours/24:.1f}d" if avg_resolution_hours > 24 else f"{avg_resolution_hours:.0f}h"
    analytics_departments = sorted({complaint.get("department") for complaint in all_complaints if complaint.get("department")})

    return render_template(
        "admin_dashboard.html",
        stats=stats,
        complaints=pagination["items"],
        selected_department=dept_filter,
        complaint_details=complaint_details,
        tickets=tickets,
        unread_admin=unread_admin,
        map_points_json=_serialize_map_points(get_complaints_with_coords(city_filter=city_filter, date_from=date_from, date_to=date_to)),
        cities=get_available_cities_with_coords(),
        selected_city=city_filter,
        selected_date_from=date_from or "",
        selected_date_to=date_to or "",
        selected_status=status_filter,
        selected_urgency=urgency_filter,
        selected_category=category_filter,
        search_term=term,
        categories=["All"] + CATEGORIES,
        trend=daily_trend,
        leaderboard=leaderboard,
        workers=get_all_workers(),
        departments=DEPARTMENTS,
        missing_departments=get_departments_without_active_workers(),
        pending_count=len(get_pending_workers()),
        correction_count=get_correction_count_since_last_training(),
        model_versions=list(reversed(get_model_versions())),
        recent_corrections=get_all_corrections()[:12],
        pagination=pagination,
        analytics_date_from=analytics_date_from or "",
        analytics_date_to=analytics_date_to or "",
        analytics_department=analytics_department,
        analytics_priority=analytics_priority,
        analytics_departments=analytics_departments,
        analytics_filtered_count=len(analytics_complaints),
        analytics_category_chart=_figure_html(get_category_distribution_chart(analytics_stats.get("by_category", []))) if analytics_stats.get("by_category") else None,
        analytics_urgency_chart=_figure_html(
            get_urgency_donut(
                analytics_stats.get("urgency_high", 0),
                analytics_stats.get("urgency_medium", 0),
                analytics_stats.get("urgency_low", 0),
            )
        ),
        analytics_daily_chart=_figure_html(get_daily_trend_chart(daily_trend)) if daily_trend else None,
        analytics_leaderboard_chart=_figure_html(get_agent_leaderboard_chart(leaderboard)) if leaderboard else None,
        analytics_avg_resolution=avg_resolution_display,
        analytics_department_rows=analytics_department_rows,
        analytics_hod_roster=analytics_hod_roster,
        analytics_total_resolved=sum(1 for complaint in analytics_complaints if complaint.get("status") == "Resolved"),
        analytics_total_pending=sum(1 for complaint in analytics_complaints if complaint.get("status") == "Pending"),
        analytics_total_in_progress=sum(1 for complaint in analytics_complaints if complaint.get("status") == "In Progress"),
    )


@app.route("/admin/inbox")
@login_required(role="agent")
def admin_inbox():
    if not g.is_admin:
        flash("Admin access is required.", "error")
        return redirect(url_for("home"))

    unread_admin = get_unread_count_admin()
    tickets = get_tickets_for_admin()
    for ticket in tickets:
        detail = get_complaint_by_id(ticket.get("complaint_id")) if ticket.get("complaint_id") else None
        ticket["proof_url"] = _build_media_url(detail.get("completion_image")) if detail else None
        ticket["complaint_image_url"] = _build_media_url(detail.get("image_path")) if detail else None

    if unread_admin:
        mark_tickets_read_admin()

    return render_template(
        "admin_inbox.html",
        tickets=tickets,
        unread_admin=unread_admin,
        missing_departments=get_departments_without_active_workers(),
    )


@app.route("/admin/complaints/<int:complaint_id>/status", methods=["POST"])
@login_required(role="agent")
def admin_update_complaint(complaint_id):
    if not g.is_admin:
        flash("Admin access is required.", "error")
        return redirect(url_for("home"))

    status_value = request.form.get("status", "").strip()
    proof_path = None
    proof_file = request.files.get("proof_image")
    if status_value == "Resolved" and proof_file and proof_file.filename:
        proof_path, _ = _save_uploaded_image(proof_file, complaint_id)

    success = update_complaint_status(
        complaint_id,
        status_value,
        agent_id=g.current_user.get("agent_id"),
        notes=request.form.get("notes", "").strip(),
        work_started_at=datetime.now().isoformat() if status_value == "In Progress" else None,
        work_completed_at=datetime.now().isoformat() if status_value == "Resolved" else None,
        completion_image=proof_path,
    )
    flash("Complaint updated." if success else "Complaint update failed.", "success" if success else "error")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/complaints/<int:complaint_id>/correction", methods=["POST"])
@login_required(role="agent")
def admin_submit_correction(complaint_id):
    if not g.is_admin:
        flash("Admin access is required.", "error")
        return redirect(url_for("home"))

    complaint = get_complaint_by_id(complaint_id)
    if not complaint:
        flash("Complaint not found.", "error")
        return redirect(url_for("admin_dashboard"))

    success = add_correction(
        complaint_id=complaint_id,
        original_prediction=complaint.get("category"),
        corrected_label=request.form.get("corrected_category", "").strip(),
        original_urgency=complaint.get("ai_urgency"),
        corrected_urgency=request.form.get("corrected_urgency", "").strip(),
        corrected_by=g.current_user.get("agent_id"),
        image_path=complaint.get("image_path"),
        description=complaint.get("description"),
        category=request.form.get("corrected_category", "").strip(),
    )
    flash("AI correction recorded." if success else "AI correction failed.", "success" if success else "error")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/ai/retrain", methods=["POST"])
@login_required(role="agent")
def admin_retrain_ai():
    if not g.is_admin:
        flash("Admin access is required.", "error")
        return redirect(url_for("home"))

    result = check_and_retrain()
    if result.get("retrained"):
        flash(
            f"Model retrained to version {result['version']} with {result['new_accuracy'] * 100:.1f}% accuracy.",
            "success",
        )
    else:
        flash(
            result.get("error") or f"Retraining not triggered yet. Corrections: {result.get('correction_count', 0)}/15.",
            "info",
        )
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/workers/add", methods=["POST"])
@login_required(role="agent")
def admin_add_worker():
    if not g.is_admin:
        flash("Admin access is required.", "error")
        return redirect(url_for("home"))

    name = request.form.get("name", "").strip()
    agent_id = request.form.get("agent_id", "").strip().upper()
    department = request.form.get("department", "").strip()
    password = request.form.get("password", "").strip()

    if not all([name, agent_id, department, password]):
        flash("Please complete all worker fields.", "error")
    elif not _validate_agent_id(agent_id):
        flash("Agent ID must be in the format AGT0002.", "error")
    else:
        created = add_agent(name, agent_id, _hash_password(password), department)
        flash("Worker created successfully." if created else "Worker could not be created.", "success" if created else "error")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/workers/<agent_id>/warn", methods=["POST"])
@login_required(role="agent")
def admin_warn_worker(agent_id):
    if not g.is_admin:
        flash("Admin access is required.", "error")
        return redirect(url_for("home"))

    count, is_now_pending = warn_worker(agent_id)
    if count is None:
        flash("Worker warning could not be recorded.", "error")
    elif is_now_pending:
        flash(f"{agent_id} has been moved to pending status after {count} warnings. A supervisor must review.", "warning")
    else:
        flash(f"Warning recorded for {agent_id}. Total warnings: {count}.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/workers/<agent_id>/unblock", methods=["POST"])
@login_required(role="agent")
def admin_unblock_worker(agent_id):
    if not g.is_admin:
        flash("Admin access is required.", "error")
        return redirect(url_for("home"))

    success = restore_worker(agent_id)
    flash("Worker unblocked." if success else "Worker could not be unblocked.", "success" if success else "error")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/workers/<agent_id>/role", methods=["POST"])
@app.route("/admin/worker/update/<agent_id>", methods=["POST"])
@login_required(role="agent")
def admin_worker_role(agent_id):
    if not g.is_admin:
        flash("Admin access is required.", "error")
        return redirect(url_for("home"))
        
    new_role = request.form.get("role", "worker")
    new_dept = request.form.get("department")
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if new_dept:
            cursor.execute("UPDATE agents SET role = ?, department = ? WHERE agent_id = ?", (new_role, new_dept, agent_id))
        else:
            cursor.execute("UPDATE agents SET role = ? WHERE agent_id = ?", (new_role, agent_id))
        conn.commit()
        conn.close()
        flash(f"Worker {agent_id} updated successfully.", "success")
    except Exception as e:
        flash(f"Failed to update worker {agent_id}: {str(e)}", "error")
        
    return redirect(url_for("admin_dashboard", tab="admin-workforce"))


@app.route("/admin/export")
@login_required(role="agent")
def admin_export():
    if not g.is_admin:
        flash("Admin access is required.", "error")
        return redirect(url_for("home"))

    export_format = request.args.get("export_format", "csv").lower()
    
    dataframe = export_complaints_csv(
        status_filter=None if request.args.get("status", "All") == "All" else request.args.get("status"),
        category_filter=None if request.args.get("category", "All") == "All" else request.args.get("category"),
        urgency_filter=None if request.args.get("urgency", "All") == "All" else request.args.get("urgency"),
    )
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    base_name = f"complaints_export_{timestamp}"
    buffer = BytesIO()

    if export_format == "json":
        json_data = dataframe.to_json(orient="records", indent=4)
        buffer.write(json_data.encode('utf-8'))
        buffer.seek(0)
        return send_file(buffer, mimetype="application/json", as_attachment=True, download_name=f"{base_name}.json")
        
    elif export_format == "word":
        from utils.report_utils import generate_word_report
        word_bytes = generate_word_report(dataframe)
        buffer.write(word_bytes)
        buffer.seek(0)
        return send_file(buffer, mimetype="application/msword", as_attachment=True, download_name=f"{base_name}.doc")
        
    elif export_format == "pdf":
        from utils.report_utils import generate_pdf_report
        pdf_bytes = generate_pdf_report(dataframe)
        buffer.write(pdf_bytes)
        buffer.seek(0)
        return send_file(buffer, mimetype="application/pdf", as_attachment=True, download_name=f"{base_name}.pdf")
        
    else:
        # Default CSV
        dataframe.to_csv(buffer, index=False)
        buffer.seek(0)
        return send_file(buffer, mimetype="text/csv", as_attachment=True, download_name=f"{base_name}.csv")




@app.route("/worker/dashboard")
@login_required()
def worker_dashboard():
    # Allow workers and supervisors to see their dashboard (if a supervisor has a department)
    if g.user_type not in ["worker", "supervisor"]:
        flash("Access denied.", "error")
        return redirect(url_for("home"))

    if g.current_user.get("status") == "blocked":
        flash("This worker account is currently blocked. Please contact admin.", "error")
        return redirect(url_for("logout"))

    is_pending = g.current_user.get("status") == "pending"
    
    term = request.args.get("term", "").strip()
    status_filter = request.args.get("status", "All")
    urgency_filter = request.args.get("urgency", "All")
    page = request.args.get("page", default=1, type=int)
    unread_worker = get_unread_count_worker(g.current_user.get("department"))
    if unread_worker:
        mark_tickets_read_worker(g.current_user.get("department"))

    complaints = search_complaints(
        term=term,
        status_filter=status_filter,
        urgency_filter=urgency_filter,
        department_filter=g.current_user.get("department"),
    )
    pagination = _paginate_items(complaints, page)
    complaint_details = {complaint["id"]: _enrich_complaint(complaint) for complaint in complaints}
    tickets = get_tickets_by_department(g.current_user.get("department"))
    for ticket in tickets:
        detail = get_complaint_by_id(ticket.get("complaint_id")) if ticket.get("complaint_id") else None
        ticket["proof_url"] = _build_media_url(detail.get("completion_image")) if detail else None

    return render_template(
        "worker_dashboard.html",
        complaints=pagination["items"],
        complaint_details=complaint_details,
        tickets=tickets,
        unread_worker=unread_worker,
        selected_status=status_filter,
        selected_urgency=urgency_filter,
        search_term=term,
        is_pending=is_pending,
        pagination=pagination,
    )


@app.route("/supervisor/dashboard")
@login_required(role="supervisor")
def supervisor_dashboard():
    # Admin can also access this
    term = request.args.get("term", "").strip()
    status_filter = request.args.get("status", "All")
    urgency_filter = request.args.get("urgency", "All")
    category_filter = request.args.get("category", "All")
    selected_dept = g.current_user.get("department") if not g.is_admin else (request.args.get("dept", "").strip() or None)
    page = int(request.args.get("page", 1))
    per_page = 5
    
    from auth.agent_auth import DEPARTMENTS
    
    all_filtered_complaints = search_complaints(
        term=term, 
        status_filter=status_filter, 
        urgency_filter=urgency_filter, 
        category_filter=category_filter,
        department_filter=selected_dept
    )
    
    total_complaints = len(all_filtered_complaints)
    total_pages = (total_complaints + per_page - 1) // per_page
    start_idx = (page - 1) * per_page
    paginated_complaints = all_filtered_complaints[start_idx : start_idx + per_page]
    
    return render_template(
        "supervisor_dashboard.html",
        stats=get_complaint_stats(department=selected_dept),
        complaints=paginated_complaints,
        pending_workers=get_pending_workers(department=selected_dept),
        categories=["All"] + CATEGORIES,
        departments=DEPARTMENTS,
        selected_status=status_filter,
        selected_urgency=urgency_filter,
        selected_category=category_filter,
        selected_dept=selected_dept,
        search_term=term,
        current_page=page,
        total_pages=total_pages,
        total_count=total_complaints,
        dept_workers=get_workers_by_department(selected_dept) if selected_dept else [],
        all_system_workers=get_all_workers(),
        is_admin_view=g.is_admin
    )


@app.route("/supervisor/worker/claim", methods=["POST"])
@login_required(role="supervisor")
def supervisor_claim_worker():
    worker_id = request.form.get("worker_id")
    department = g.current_user.get("department")
    
    if not worker_id:
        flash("Worker ID is required.", "error")
        return redirect(url_for("supervisor_dashboard", tab="supervisor-team"))
        
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE agents SET department = ? WHERE agent_id = ?", (department, worker_id))
        conn.commit()
        conn.close()
        flash(f"Worker {worker_id} successfully claimed for {department}.", "success")
    except Exception as e:
        flash(f"Failed to claim worker: {str(e)}", "error")
        
    return redirect(url_for("supervisor_dashboard", tab="supervisor-team"))


@app.route("/supervisor/worker/add", methods=["POST"])
@login_required(role="supervisor")
def supervisor_add_worker():
    name = request.form.get("name", "").strip()
    agent_id = request.form.get("agent_id", "").strip().upper()
    password = request.form.get("password", "").strip()
    department = g.current_user.get("department")
    
    if not all([name, agent_id, password]):
        flash("Please complete all worker fields.", "error")
    elif not _validate_agent_id(agent_id):
        flash("Agent ID must be in the format AGT0002.", "error")
    else:
        created = add_agent(name, agent_id, _hash_password(password), department)
        flash("Worker created successfully." if created else "Worker could not be created.", "success" if created else "error")
        
    return redirect(url_for("supervisor_dashboard", tab="supervisor-team"))


@app.route("/supervisor/team/assign", methods=["POST"])
@login_required(role="supervisor")
def supervisor_assign_lead():
    worker_id = request.form.get("worker_id")
    lead_id = request.form.get("lead_id")
    
    if not worker_id:
        flash("Worker ID is required.", "error")
        return redirect(url_for("supervisor_dashboard"))
        
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE agents SET lead_id = ? WHERE agent_id = ?", (lead_id or None, worker_id))
        conn.commit()
        conn.close()
        flash(f"Worker {worker_id} assignment updated.", "success")
    except Exception as e:
        flash(f"Failed to assign lead: {str(e)}", "error")
        
    return redirect(url_for("supervisor_dashboard", tab="supervisor-team"))


@app.route("/supervisor/complaints/<int:complaint_id>/assign", methods=["POST"])
@login_required(role="supervisor")
def supervisor_assign_worker(complaint_id):
    worker_id = request.form.get("worker_id", "").strip()
    if not worker_id:
        flash("Please select a worker to assign.", "error")
    else:
        success = update_complaint_status(complaint_id, "In Progress", agent_id=worker_id, notes="Assigned by supervisor")
        if success:
            flash(f"Complaint assigned to {worker_id}.", "success")
        else:
            flash("Failed to assign complaint.", "error")
            
    return redirect(url_for("supervisor_dashboard", dept=request.form.get("dept")))


@app.route("/supervisor/block/<agent_id>", methods=["POST"])
@login_required(role="supervisor")
def supervisor_block(agent_id):
    success = block_worker(agent_id)
    if success:
        flash(f"Worker {agent_id} has been blocked.", "success")
    else:
        flash(f"Failed to block worker {agent_id}.", "error")
    return redirect(url_for("supervisor_dashboard"))


@app.route("/supervisor/restore/<agent_id>", methods=["POST"])
@login_required(role="supervisor")
def supervisor_restore(agent_id):
    success = restore_worker(agent_id)
    if success:
        flash(f"Worker {agent_id} has been restored to active status.", "success")
    else:
        flash(f"Failed to restore worker {agent_id}.", "error")
    return redirect(url_for("supervisor_dashboard"))


@app.route("/worker/complaints/<int:complaint_id>/status", methods=["POST"])
@login_required()
def worker_update_complaint(complaint_id):
    if g.user_type not in ["worker", "supervisor"]:
        return redirect(url_for("home"))
        
    if g.current_user.get("status") != "active":
        flash("Only active workers can update complaints.", "error")
        return redirect(url_for("worker_dashboard"))

    status_value = request.form.get("status", "").strip()
    proof_path = None
    proof_file = request.files.get("proof_image")
    existing_detail = get_complaint_by_id(complaint_id)
    existing_proof = existing_detail.get("completion_image") if existing_detail else None
    if status_value == "Resolved" and not existing_proof and (not proof_file or not proof_file.filename):
        flash("Please upload a photo as proof of work before resolving the complaint.", "error")
        return redirect(url_for("worker_dashboard"))
    if status_value == "Resolved" and proof_file and proof_file.filename:
        proof_path, _ = _save_uploaded_image(proof_file, complaint_id)

    success = update_complaint_status(
        complaint_id,
        status_value,
        agent_id=g.current_user.get("agent_id"),
        notes=request.form.get("notes", "").strip(),
        work_started_at=datetime.now().isoformat() if status_value == "In Progress" else None,
        work_completed_at=datetime.now().isoformat() if status_value == "Resolved" else None,
        completion_image=proof_path,
    )
    flash("Complaint updated." if success else "Complaint update failed.", "success" if success else "error")
    return redirect(url_for("worker_dashboard"))


if __name__ == "__main__":
    app.run(debug=True)
