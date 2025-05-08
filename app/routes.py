from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_file,
    g,
    session,
)
from datetime import datetime
from app.models import BBQSession, Temperature, Graph, NoteEntry
from app import db
import os
from dotenv import load_dotenv
import io
import pytz
from werkzeug.utils import secure_filename
from app.graph_utils import generate_graph_from_csv
from functools import wraps
from sqlalchemy.sql import func

load_dotenv()

main = Blueprint("main", __name__)

# Define list of common timezones for dropdown selection (can be expanded)
COMMON_TIMEZONES = [
    "UTC",
    "US/Eastern",
    "US/Central",
    "US/Mountain",
    "US/Pacific",
    "Europe/London",
    "Europe/Paris",
    "Asia/Tokyo",
    "Australia/Sydney",
]


# Add error handler for 404 errors
@main.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


# Function to get the user's timezone
def get_timezone():
    """
    Get the user's timezone from session or use default
    """
    # First try to get from session (if user has selected/saved preference)
    user_timezone = session.get("user_timezone")

    # If not in session, try to get from browser
    if not user_timezone:
        user_timezone = request.cookies.get("timezone", "UTC")
        # Store in session for future use
        session["user_timezone"] = user_timezone

    return user_timezone


# Add route for user to change their timezone
@main.route("/set_timezone", methods=["POST"])
def set_timezone():
    """Allow user to set their preferred timezone"""
    timezone_name = request.form.get("timezone", "UTC")

    # Validate the timezone name
    if timezone_name in pytz.all_timezones:
        session["user_timezone"] = timezone_name

        # Also set in cookie for persistence
        response = redirect(request.referrer or url_for("main.index"))
        response.set_cookie(
            "timezone", timezone_name, max_age=30 * 24 * 60 * 60
        )  # 30 days

        flash(f"Timezone set to {timezone_name}", "success")
        return response
    else:
        flash("Invalid timezone selected", "error")
        return redirect(request.referrer or url_for("main.index"))


# Add template helpers for timezone conversion
@main.context_processor
def inject_timezone_utilities():
    """
    Inject timezone utilities into all templates
    """

    def format_datetime(dt, format="%Y-%m-%d %H:%M:%S"):
        """
        Format a datetime in the user's timezone
        """
        if dt is None:
            return ""

        # Ensure datetime is timezone aware - assume UTC if naive
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=pytz.UTC)

        # Convert to user's timezone
        user_tz = pytz.timezone(get_timezone())
        local_dt = dt.astimezone(user_tz)

        # Format according to provided format string
        return local_dt.strftime(format)

    def time_since(dt):
        """
        Return a human-readable string representing time since the datetime
        """
        if dt is None:
            return ""

        # Ensure datetime is timezone aware - assume UTC if naive
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=pytz.UTC)

        # Get current time from database for consistency
        from sqlalchemy import text

        now = datetime.utcnow().replace(tzinfo=pytz.UTC)

        diff = now - dt

        # Convert difference to appropriate units
        seconds = diff.total_seconds()

        if seconds < 60:
            return f"{int(seconds)} seconds ago"
        elif seconds < 3600:
            return f"{int(seconds // 60)} minutes ago"
        elif seconds < 86400:
            return f"{int(seconds // 3600)} hours ago"
        else:
            return f"{int(seconds // 86400)} days ago"

    # Return all utility functions and variables
    return {
        "format_datetime": format_datetime,
        "time_since": time_since,
        "user_timezone": get_timezone,
        "available_timezones": COMMON_TIMEZONES,
    }


# Add this route for CSV upload
@main.route("/session/<int:session_id>/upload_csv", methods=["POST"])
def upload_csv(session_id):
    session = BBQSession.query.get_or_404(session_id)

    if "csv_file" not in request.files:
        flash("No file part")
        return redirect(url_for("main.view_session", session_id=session_id))

    file = request.files["csv_file"]

    if file.filename == "":
        flash("No selected file")
        return redirect(url_for("main.view_session", session_id=session_id))

    if file and file.filename.endswith(".csv"):
        # Read the file
        file_content = file.read()

        try:
            # Generate graph image
            image_data = generate_graph_from_csv(file_content)

            # Create Graph record
            filename = secure_filename(file.filename)
            graph = Graph(
                filename=filename, image_data=image_data, session_id=session_id
            )

            db.session.add(graph)
            db.session.commit()

            flash("CSV uploaded and graph generated successfully")
        except Exception as e:
            flash(f"Error processing CSV: {str(e)}")
            print(f"Error: {str(e)}")
    else:
        flash("Only CSV files are allowed")

    return redirect(url_for("main.view_session", session_id=session_id))


# Add route to view the graph
@main.route("/graph/<int:graph_id>")
def view_graph(graph_id):
    graph = Graph.query.get_or_404(graph_id)
    return send_file(
        io.BytesIO(graph.image_data),
        mimetype="image/png",
        as_attachment=False,
        download_name=f"graph_{graph_id}.png",
    )


# Add route to edit temp
@main.route("/session/<int:session_id>/temp/<int:temp_id>/edit", methods=["POST"])
def edit_temperature(session_id, temp_id):
    session = BBQSession.query.get_or_404(session_id)

# Only allow editing if the session is still active
    if session.end_time:
        flash("Cannot edit temperature readings on completed sessions.", "error")
        return redirect(url_for("main.view_session", session_id=session_id))

    temp = Temperature.query.get_or_404(temp_id)

# Handle empty inputs for meat_temp
    meat_temp_str = request.form.get("meat_temp", "")
    if meat_temp_str.strip():
        try:
            temp.meat_temp = float(meat_temp_str)
        except ValueError:
            flash("Invalid meat temperature value", "error")
            return redirect(url_for("main.view_session", session_id=session_id))
    else:
        temp.meat_temp = None

# Handle empty inputs for smoker_temp
    smoker_temp_str = request.form.get("smoker_temp", "")
    if smoker_temp_str.strip():
        try:
            temp.smoker_temp = float(smoker_temp_str)
        except ValueError:
            flash("Invalid smoker temperature value", "error")
            return redirect(url_for("main.view_session", session_id=session_id))
    else:
        temp.smoker_temp = None

    temp.note = request.form.get("note", "")

    db.session.commit()
    flash("Temperature reading updated successfully", "success")
    return redirect(url_for("main.view_session", session_id=session_id))


# Add route to edit notes
@main.route("/session/<int:session_id>/note/<int:note_id>/edit", methods=["POST"])
def edit_note(session_id, note_id):
    session = BBQSession.query.get_or_404(session_id)

    note = NoteEntry.query.filter_by(id=note_id, session_id=session_id).first_or_404()

    edited_text = request.form.get("edited_note_text", "")
    if edited_text.strip():
        formatted_text = edited_text.replace("\r\n", "<br>").replace("\n", "<br>")
        note.text = formatted_text
        db.session.commit()
        flash("Note updated successfully.", "success")
    else:
        flash("Note cannot be empty.", "error")

    return redirect(url_for("main.view_session", session_id=session_id))


# Add route to delete a graph
@main.route("/session/<int:session_id>/graph/<int:graph_id>/delete", methods=["POST"])
def delete_graph(session_id, graph_id):
    graph = Graph.query.get_or_404(graph_id)
    db.session.delete(graph)
    db.session.commit()
    flash("Graph deleted successfully")
    return redirect(url_for("main.view_session", session_id=session_id))


@main.route("/")
def index():
    sessions = BBQSession.query.order_by(BBQSession.start_time.desc()).all()
    return render_template("index.html", sessions=sessions)


@main.route("/session/new", methods=["GET", "POST"])
def new_session():
    if request.method == "POST":
        title = request.form["title"]
        meat_type = request.form["meat_type"]
        weight = request.form["weight"] or None
        if weight:
            weight = float(weight)
        smoker_type = request.form["smoker_type"]
        wood_type = request.form["wood_type"]
        target_temp = request.form["target_temp"] or None
        if target_temp:
            target_temp = int(target_temp)

        session = BBQSession(
            title=title,
            meat_type=meat_type,
            weight=weight,
            smoker_type=smoker_type,
            wood_type=wood_type,
            target_temp=target_temp,
        )

        db.session.add(session)
        db.session.commit()

        return redirect(url_for("main.view_session", session_id=session.id))

    return render_template("new_session.html")


from datetime import timezone


@main.route("/session/<int:session_id>")
def view_session(session_id):
    session = BBQSession.query.get_or_404(session_id)
    return render_template("session.html", session=session, timezone=timezone)


@main.route("/session/<int:session_id>/edit", methods=["GET", "POST"])
def edit_session(session_id):
    session = BBQSession.query.get_or_404(session_id)

    if request.method == "POST":
        session.title = request.form["title"]
        session.meat_type = request.form["meat_type"]

        weight = request.form["weight"] or None
        if weight:
            session.weight = float(weight)
        else:
            session.weight = None

        session.smoker_type = request.form["smoker_type"]
        session.wood_type = request.form["wood_type"]

        target_temp = request.form["target_temp"] or None
        if target_temp:
            session.target_temp = int(float(target_temp))
        else:
            session.target_temp = None

        # Check if the session is being marked as complete
        if "complete" in request.form and not session.end_time:
            # Instead of datetime.utcnow(), use database function:
            from sqlalchemy import func  # type: ignore

            session.end_time = func.now()


        db.session.commit()
        return redirect(url_for("main.view_session", session_id=session.id))
    # Added timezone=timezone trying to get local times on page
    return render_template("edit_session.html", session=session, timezone=timezone)


# Add route to add temperature
@main.route("/session/<int:session_id>/temp", methods=["POST"])
def add_temperature(session_id):
    session = BBQSession.query.get_or_404(session_id)

    # Handle empty inputs for meat_temp
    meat_temp_str = request.form.get("meat_temp", "")
    meat_temp = None
    if meat_temp_str.strip():
        try:
            meat_temp = float(meat_temp_str)
        except ValueError:
            flash("Invalid meat temperature value", "error")
            return redirect(url_for("main.view_session", session_id=session_id))

    # Handle empty inputs for smoker_temp
    smoker_temp_str = request.form.get("smoker_temp", "")
    smoker_temp = None
    if smoker_temp_str.strip():
        try:
            smoker_temp = float(smoker_temp_str)
        except ValueError:
            flash("Invalid smoker temperature value", "error")
            return redirect(url_for("main.view_session", session_id=session_id))

    note = request.form.get("note", "")

    temp = Temperature(
        meat_temp=meat_temp, smoker_temp=smoker_temp, note=note, session_id=session.id
    )

    db.session.add(temp)
    db.session.commit()

    return redirect(url_for("main.view_session", session_id=session_id))


@main.route("/session/<int:session_id>/delete", methods=["POST"])
def delete_session(session_id):
    session = BBQSession.query.get_or_404(session_id)
    # First delete all related temperature logs
    # TemperatureLog.query.filter_by(session_id=session_id).delete()
    db.session.delete(session)
    db.session.commit()
    return redirect(url_for("main.index"))


@main.route("/session/<int:session_id>/temp/<int:temp_id>/delete", methods=["POST"])
def delete_temperature(session_id, temp_id):
    temp = Temperature.query.get_or_404(temp_id)
    db.session.delete(temp)
    db.session.commit()
    return redirect(url_for("main.view_session", session_id=session_id))




@main.route("/session/<int:session_id>/note", methods=["POST"])
def add_note(session_id):
    session = BBQSession.query.get_or_404(session_id)

    note_text = request.form["note_text"]
    if not note_text.strip():
        flash("Note cannot be empty")
        return redirect(url_for("main.view_session", session_id=session_id))

    note = NoteEntry(text=note_text, session_id=session.id)

    db.session.add(note)
    db.session.commit()

    flash("Note added successfully")
    return redirect(url_for("main.view_session", session_id=session_id))


@main.route("/session/<int:session_id>/note/<int:note_id>/delete", methods=["POST"])
def delete_note(session_id, note_id):
    note = NoteEntry.query.get_or_404(note_id)
    db.session.delete(note)
    db.session.commit()
    flash("Note deleted successfully")
    return redirect(url_for("main.view_session", session_id=session_id))


@main.route("/session/<int:session_id>/complete", methods=["POST"])
def complete_session(session_id):
    # Get the session
    session = BBQSession.query.get_or_404(session_id)

    # Set the end time to current time using database function
    from sqlalchemy import func

    session.end_time = func.now()

    # Save to database
    db.session.commit()

    # Flash a success message
    flash("BBQ session completed successfully!", "success")

    # Redirect back to the session page
    return redirect(url_for("main.view_session", session_id=session_id))


@main.route("/session/<int:session_id>/temp_log_graph")
def view_temp_log_graph(session_id):
    # Get the BBQ session
    session = BBQSession.query.get_or_404(session_id)

    # Get all temperature logs for this session
    from app.models import TemperatureLog

    temp_logs = (
        TemperatureLog.query.filter_by(session_id=session_id)
        .order_by(TemperatureLog.timestamp)
        .all()
    )

    # Use the existing timezone function
    user_timezone = get_timezone()

    # Generate graph
    from app.graph_utils import generate_graph_from_db

    try:
        image_data = generate_graph_from_db(temp_logs, timezone=user_timezone)

        # Return the image
        return send_file(
            io.BytesIO(image_data),
            mimetype="image/png",
            as_attachment=False,
            download_name=f"temp_log_graph_{session_id}.png",
        )
    except Exception as e:
        flash(f"Error generating graph: {str(e)}", "error")
        return redirect(url_for("main.view_session", session_id=session_id))


@main.route("/session/<int:session_id>/add_weather", methods=["POST"])
def add_weather(session_id):
    """Add weather information as a note to the BBQ session"""
    import logging
    # Set up logging
    logger = logging.getLogger(__name__)
    
    # Get the session to make sure it exists
    session = BBQSession.query.get_or_404(session_id)
    
    # Get the zip code from the form submission or from environment variable
    zip_code = os.getenv("DEFAULT_ZIP_CODE")
    logger.info(f"DEFAULT_ZIP_CODE from env: {zip_code}")
    
    if not zip_code:
        flash("Zip code environment variable (DEFAULT_ZIP_CODE) is not set", "error")
        return redirect(url_for("main.view_session", session_id=session_id))
    
    # Import weather_utils here to avoid potential circular imports
    from app.weather_utils import get_weather_by_zip
    
    # Get weather data from our utility function
    weather_result = get_weather_by_zip(zip_code)
    
    if not weather_result["success"]:
        flash(weather_result["message"], "error")
        return redirect(url_for("main.view_session", session_id=session_id))
    
    # Create a new note entry with the detailed formatted weather data
    weather_note = NoteEntry(
        text=weather_result["data"]["formatted_text"], 
        session_id=session_id
    )
    
    # Save to database
    db.session.add(weather_note)
    db.session.commit()
    
    flash("Detailed weather information added successfully", "success")
    return redirect(url_for("main.view_session", session_id=session_id))

