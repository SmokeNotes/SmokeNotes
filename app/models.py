from app import db
from sqlalchemy.sql import func
from sqlalchemy import DateTime

class BBQSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    meat_type = db.Column(db.String(50), nullable=False)
    weight = db.Column(db.Float)
    smoker_type = db.Column(db.String(50))
    wood_type = db.Column(db.String(50))
    target_temp = db.Column(db.Integer)
    # Use timezone-aware DateTime, stored as UTC
    start_time = db.Column(DateTime(timezone=True), server_default=func.now())
    end_time = db.Column(DateTime(timezone=True))
    notes = db.Column(db.Text)
    
    temperatures = db.relationship(
        "Temperature", backref="session", lazy=True, cascade="all, delete-orphan"
    )
    log_entries = db.relationship(
        "TemperatureLog", backref="session", lazy=True, cascade="all, delete-orphan"
    )
    graphs = db.relationship(
        "Graph", backref="session", lazy=True, cascade="all, delete-orphan"
    )
    notes_entries = db.relationship(
        "NoteEntry", backref="session", lazy="dynamic", cascade="all, delete-orphan"
    )
    
    def duration(self):
        if self.end_time:
            delta = self.end_time - self.start_time
        else:
            # Always use database time for consistency
            from sqlalchemy import text
            current_time = db.session.execute(text("SELECT NOW()")).scalar()
            delta = current_time - self.start_time
        
        # Calculate total seconds
        total_seconds = int(delta.total_seconds())
        # Format as hours and minutes
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours} hour {minutes:02d} min"
        else:
            return f"{minutes} min {seconds} sec"
    
    def __repr__(self):
        return f"BBQSession('{self.title}', '{self.meat_type}')"


class Temperature(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Use timezone-aware DateTime, stored as UTC
    timestamp = db.Column(DateTime(timezone=True), server_default=func.now())
    meat_temp = db.Column(db.Float)
    smoker_temp = db.Column(db.Float)
    note = db.Column(db.String(200))
    session_id = db.Column(db.Integer, db.ForeignKey("bbq_session.id"), nullable=False)
    
    def __repr__(self):
        return f"Temperature(meat: {self.meat_temp}°F, smoker: {self.smoker_temp}°F)"


class Graph(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)
    image_data = db.Column(db.LargeBinary, nullable=False)
    # Use timezone-aware DateTime, stored as UTC
    created_at = db.Column(DateTime(timezone=True), server_default=func.now())
    session_id = db.Column(db.Integer, db.ForeignKey("bbq_session.id"), nullable=False)
    
    def __repr__(self):
        return f"Graph(session_id={self.session_id})"


class NoteEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    # Use timezone-aware DateTime, stored as UTC
    timestamp = db.Column(DateTime(timezone=True), server_default=func.now())
    session_id = db.Column(
        db.Integer, db.ForeignKey("bbq_session.id", ondelete="CASCADE"), nullable=False
    )
    
    def __repr__(self):
        return f"<NoteEntry {self.id} for Session {self.session_id}>"


class TemperatureLog(db.Model):
    __tablename__ = "temperature_log"
    
    id = db.Column(db.Integer, primary_key=True)
    cook_id = db.Column(db.Integer, index=True)
    session_id = db.Column(db.Integer, db.ForeignKey("bbq_session.id"), nullable=False)
    # Use timezone-aware DateTime, stored as UTC
    timestamp = db.Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    set_temp = db.Column(db.Float)
    pit_temp = db.Column(db.Float)
    meat_temp1 = db.Column(db.Float)
    blower = db.Column(db.Float)
    
    def __repr__(self):
        return f"<TempLog {self.timestamp} | Cook {self.cook_id}>"
