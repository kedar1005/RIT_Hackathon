import hashlib
import json
import os
import re
from datetime import datetime
from functools import wraps
from io import BytesIO

from flask import Flask, flash, g, redirect, render_template, request, send_file, session, url_for
from werkzeug.utils import secure_filename

from auth.agent_auth import DEPARTMENTS
from ml.image_model import dual_predict
from ml.model import CATEGORIES, predict_full
from utils.data_utils import (
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
    get_all_workers,
    get_connection,
    get_available_cities_with_coords,
    get_complaint_stats,
    get_complaints_with_coords,
    get_daily_trend,
    get_departments_without_active_workers,
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
    return render_template("index.html", stats=get_complaint_stats())


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
        page_title="Worker Login",
        page_subtitle="Access department complaints and update work progress.",
        form_type="worker_login",
    )


@app.route("/citizen/dashboard", methods=["GET", "POST"])
@login_required(role="citizen")
def citizen_dashboard():
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
    tickets = get_user_tickets(g.current_user["id"])
    unread_tickets = get_unread_count_user(g.current_user["id"])
    if unread_tickets:
        mark_tickets_read_user(g.current_user["id"])

    return render_template(
        "citizen_dashboard.html",
        categories=CATEGORIES,
        urgencies=URGENCY_OPTIONS,
        complaints=complaints,
        tickets=tickets,
        unread_tickets=unread_tickets,
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
    unread_admin = get_unread_count_admin()
    if unread_admin:
        mark_tickets_read_admin()

    return render_template(
        "admin_dashboard.html",
        stats=get_complaint_stats(),
        complaints=search_complaints(term=term, status_filter=status_filter, urgency_filter=urgency_filter, category_filter=category_filter),
        tickets=get_tickets_for_admin(),
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
        trend=get_daily_trend(30),
        leaderboard=get_agent_leaderboard(),
        workers=get_all_workers(),
        departments=DEPARTMENTS,
        missing_departments=get_departments_without_active_workers(),
        pending_count=len(get_pending_workers()),
    )


@app.route("/admin/complaints/<int:complaint_id>/status", methods=["POST"])
@login_required(role="agent")
def admin_update_complaint(complaint_id):
    if not g.is_admin:
        flash("Admin access is required.", "error")
        return redirect(url_for("home"))

    success = update_complaint_status(
        complaint_id,
        request.form.get("status", "").strip(),
        agent_id=g.current_user.get("agent_id"),
        notes=request.form.get("notes", "").strip(),
        work_started_at=datetime.now().isoformat() if request.form.get("status") == "In Progress" else None,
        work_completed_at=datetime.now().isoformat() if request.form.get("status") == "Resolved" else None,
    )
    flash("Complaint updated." if success else "Complaint update failed.", "success" if success else "error")
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

    success = unblock_worker(agent_id)
    flash("Worker unblocked." if success else "Worker could not be unblocked.", "success" if success else "error")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/workers/<agent_id>/role", methods=["POST"])
@login_required(role="agent")
def admin_worker_role(agent_id):
    if not g.is_admin:
        flash("Admin access is required.", "error")
        return redirect(url_for("home"))
        
    new_role = request.form.get("role", "worker")
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE agents SET role = ? WHERE agent_id = ?", (new_role, agent_id))
        conn.commit()
        conn.close()
        flash(f"Worker {agent_id} role updated to {new_role}.", "success")
    except Exception:
        flash(f"Failed to update worker {agent_id} role.", "error")
        
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/export")
@login_required(role="agent")
def admin_export():
    if not g.is_admin:
        flash("Admin access is required.", "error")
        return redirect(url_for("home"))

    dataframe = export_complaints_csv(
        status_filter=None if request.args.get("status", "All") == "All" else request.args.get("status"),
        category_filter=None if request.args.get("category", "All") == "All" else request.args.get("category"),
        urgency_filter=None if request.args.get("urgency", "All") == "All" else request.args.get("urgency"),
    )
    buffer = BytesIO()
    dataframe.to_csv(buffer, index=False)
    buffer.seek(0)
    return send_file(buffer, mimetype="text/csv", as_attachment=True, download_name="complaints_export.csv")


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
    unread_worker = get_unread_count_worker(g.current_user.get("department"))
    if unread_worker:
        mark_tickets_read_worker(g.current_user.get("department"))

    return render_template(
        "worker_dashboard.html",
        complaints=search_complaints(
            term=term,
            status_filter=status_filter,
            urgency_filter=urgency_filter,
            assigned_agent_filter=g.current_user.get("agent_id"),
        ),
        tickets=get_tickets_by_department(g.current_user.get("department")),
        unread_worker=unread_worker,
        selected_status=status_filter,
        selected_urgency=urgency_filter,
        search_term=term,
        is_pending=is_pending,
    )


@app.route("/supervisor/dashboard")
@login_required(role="supervisor")
def supervisor_dashboard():
    # Admin can also access this
    term = request.args.get("term", "").strip()
    status_filter = request.args.get("status", "All")
    urgency_filter = request.args.get("urgency", "All")
    category_filter = request.args.get("category", "All")
    selected_dept = request.args.get("dept", "").strip() or None
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
        stats=get_complaint_stats(),
        complaints=paginated_complaints,
        pending_workers=get_pending_workers(),
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
        is_admin_view=g.is_admin
    )


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
    success = update_complaint_status(
        complaint_id,
        status_value,
        agent_id=g.current_user.get("agent_id"),
        notes=request.form.get("notes", "").strip(),
        work_started_at=datetime.now().isoformat() if status_value == "In Progress" else None,
        work_completed_at=datetime.now().isoformat() if status_value == "Resolved" else None,
    )
    flash("Complaint updated." if success else "Complaint update failed.", "success" if success else "error")
    return redirect(url_for("worker_dashboard"))


if __name__ == "__main__":
    app.run(debug=True)
