from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app, origins=["http://localhost:3000"])

# In-memory event storage
events = []

#def parse_datetime(date_string):
#    """Parse datetime string with flexible format handling."""
#    if not date_string:
#        return None
#    try:
#        # First try with seconds
#        return datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S")
#    except ValueError:
#        try:
#            # Then try without seconds
#            return datetime.strptime(date_string, "%Y-%m-%dT%H:%M")
#        except ValueError:
#            raise ValueError(f"Invalid datetime format: {date_string}")
def parse_datetime(date_string):
    """Parse datetime string with ISO format handling."""
    if not date_string:
        return None

    if date_string.endswith('Z'):
        date_string = date_string[:-1]  
    if '.' in date_string:
        date_string = date_string.split('.')[0]  
        
    try:
        return datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        try:
            return datetime.strptime(date_string, "%Y-%m-%dT%H:%M")
        except ValueError:
            raise ValueError(f"Invalid datetime format: {date_string}")
        
def parse_preferred_time(preferred_time):
    """Parse preferred time string in format 'HH:MM - HH:MM'."""
    if not preferred_time:
        return None, None
    try:
        start_time, end_time = preferred_time.split("-")
        start = datetime.strptime(start_time.strip(), "%H:%M").time()
        end = datetime.strptime(end_time.strip(), "%H:%M").time()
        return start, end
    except (ValueError, AttributeError):
        raise ValueError(f"Invalid preferred time format: {preferred_time}")

@app.route("/events", methods=["GET"])
def get_events():
    """Fetch all events."""
    return jsonify(events)
@app.route("/events/<int:event_id>", methods=["DELETE"])
def delete_event(event_id):
    """Delete an event and its recurring instances if applicable."""
    # Find the event by ID
    event_to_delete = None
    for event in events[:]:  # Create a copy of the list to safely modify it
        if event.get("id") == event_id:
            event_to_delete = event
            events.remove(event)
            break
    
    if not event_to_delete:
        return jsonify({"error": "Event not found"}), 404
        
    # If it's a recurring parent event, delete all its instances
    if event_to_delete["type"].startswith("recurring"):
        for event in events[:]:  # Create a copy of the list to safely modify it
            if event.get("type") == "recurring_instance" and event.get("parent_id") == event_id:
                events.remove(event)
                
    return jsonify({"message": "Event deleted successfully"}), 200
@app.route("/events", methods=["POST"])
def create_event():
    """Create a new event with conflict checking."""
    data = request.json
    event_type = data.get("type", "fixed")
    
    # Validate required fields based on event type
    if not validate_event_data(data, event_type):
        return jsonify({"error": "Missing required fields"}), 400

    new_event = {
        "id": len(events) + 1,
        "title": data["title"],
        "priority": data["priority"],
        "type": event_type
    }

    if event_type == "fixed":
        new_event.update({
            "start": data["start"],
            "end": data["end"]
        })
        if check_conflicts(new_event):
            return jsonify({"error": "Time slot is occupied"}), 409
        events.append(new_event)
        
    elif event_type.startswith("recurring"):
        success = handle_recurring_event(data, new_event)
        if not success:
            return jsonify({"error": "Could not schedule recurring event"}), 409
            
    elif event_type.startswith("flexible"):
        success = handle_flexible_event(data, new_event)
        if not success:
            return jsonify({"error": "Could not schedule flexible event"}), 409
    
    return jsonify(new_event), 201

def validate_event_data(data, event_type):
    """Validate required fields based on event type."""
    base_fields = ["title", "priority"]
    
    type_fields = {
        "fixed": ["start", "end"],
        "recurring_with_preferred_time": ["duration", "frequency", "start_date"],
        "recurring_without_preferred_time": ["duration", "frequency", "start_date"],
        "flexible_with_preferred_time": ["duration", "earliest_start", "deadline"],
        "flexible_without_preferred_time": ["duration", "earliest_start", "deadline"]
    }
    
    required_fields = base_fields + type_fields.get(event_type, [])
    return all(field in data and data[field] for field in required_fields)

def check_conflicts(new_event):
    """Check if the new event conflicts with existing events."""
    new_start = parse_datetime(new_event["start"])
    new_end = parse_datetime(new_event["end"])
    
    if not new_start or not new_end:
        return True

    for event in events:
        if "start" not in event or "end" not in event:
            continue
            
        event_start = parse_datetime(event["start"])
        event_end = parse_datetime(event["end"])
        
        if event_start and event_end:
            if max(new_start, event_start) < min(new_end, event_end):
                return True
    return False

def handle_recurring_event(data, new_event):
    """Handle recurring event scheduling."""
    duration = timedelta(minutes=int(data["duration"]))
    frequency = int(data["frequency"])
    start_date = parse_datetime(data.get("start_date"))
    
    if not start_date:
        return False
    
    # Schedule for 30 days from the start date
    end_date = start_date + timedelta(days=30)
    
    scheduled_instances = []
    current_date = start_date
    
    while current_date <= end_date:
        if data.get("type") == "recurring_with_preferred_time" and data.get("preferred_time"):
            try:
                pref_start, pref_end = parse_preferred_time(data["preferred_time"])
                
                # Try to schedule within preferred time
                day_start = datetime.combine(current_date.date(), pref_start)
                day_end = datetime.combine(current_date.date(), pref_end)
            except ValueError as e:
                print(f"Error parsing preferred time: {e}")
                return False
        else:
            # For recurring_without_preferred_time, try whole day
            day_start = current_date.replace(hour=0, minute=0, second=0)
            day_end = current_date.replace(hour=23, minute=59, second=59)
        
        slot = find_available_slot(day_start, day_end, duration)
        if slot:
            instance = {
                "id": len(events) + len(scheduled_instances) + 1,
                "title": data["title"],
                "priority": data["priority"],
                "type": "recurring_instance",
                "start": slot[0].isoformat(),
                "end": slot[1].isoformat(),
                "parent_id": new_event["id"]
            }
            scheduled_instances.append(instance)
        
        current_date += timedelta(days=frequency)
    
    if scheduled_instances:
        events.extend(scheduled_instances)
        return True
    return False

def handle_recurring_event(event_data, new_event):
    """Handle recurring event scheduling."""
    try:
        duration = timedelta(minutes=int(event_data.get("duration", 0)))
        frequency = int(event_data.get("frequency", 1))
        start_date = datetime.now()  # Use current time for rescheduling
        
        end_date = start_date + timedelta(days=30)
        scheduled_instances = []
        current_date = start_date
        
        while current_date <= end_date:
            day_start = current_date.replace(hour=0, minute=0, second=0)
            day_end = current_date.replace(hour=23, minute=59, second=59)
            
            if event_data.get("type") == "recurring_with_preferred_time" and event_data.get("preferred_time"):
                try:
                    pref_start, pref_end = parse_preferred_time(event_data["preferred_time"])
                    day_start = datetime.combine(current_date.date(), pref_start)
                    day_end = datetime.combine(current_date.date(), pref_end)
                except ValueError:
                    return False
            
            slot = find_available_slot(day_start, day_end, duration)
            if slot:
                instance = {
                    "id": len(events) + len(scheduled_instances) + 1,
                    "title": event_data["title"],
                    "priority": event_data["priority"],
                    "type": "recurring_instance",
                    "start": slot[0].isoformat(),
                    "end": slot[1].isoformat(),
                    "parent_id": new_event["id"]
                }
                scheduled_instances.append(instance)
            current_date += timedelta(days=frequency)
        
        if scheduled_instances:
            events.extend(scheduled_instances)
            return True
        return False
    except (KeyError, ValueError, TypeError):
        return False
    
def handle_flexible_event(data, new_event):
    """Handle flexible event scheduling."""
    duration = timedelta(minutes=int(data["duration"]))
    earliest_start = parse_datetime(data["earliest_start"])
    deadline = parse_datetime(data["deadline"])
    
    if not earliest_start or not deadline:
        return False
        
    if data.get("type") == "flexible_with_preferred_time" and data.get("preferred_time"):
        try:
            pref_start, pref_end = parse_preferred_time(data["preferred_time"])
            
            # Try to find a slot within preferred time windows
            current_date = earliest_start.date()
            while current_date <= deadline.date():
                day_start = max(
                    datetime.combine(current_date, pref_start),
                    earliest_start if current_date == earliest_start.date() else datetime.min
                )
                day_end = min(
                    datetime.combine(current_date, pref_end),
                    deadline if current_date == deadline.date() else datetime.max
                )
                
                slot = find_available_slot(day_start, day_end, duration)
                if slot:
                    new_event.update({
                        "start": slot[0].isoformat(),
                        "end": slot[1].isoformat()
                    })
                    events.append(new_event)
                    return True
                    
                current_date += timedelta(days=1)
        except ValueError as e:
            print(f"Error parsing preferred time: {e}")
            return False
    else:
        # Try to find any available slot
        slot = find_available_slot(earliest_start, deadline, duration)
        if slot:
            new_event.update({
                "start": slot[0].isoformat(),
                "end": slot[1].isoformat()
            })
            events.append(new_event)
            return True
            
    return False

def find_available_slot(start_time, end_time, duration, interval_minutes=15):
    """Find an available time slot within the given range."""
    current_time = start_time
    
    while current_time + duration <= end_time:
        proposed_event = {
            "start": current_time.isoformat(),
            "end": (current_time + duration).isoformat()
        }
        
        if not check_conflicts(proposed_event):
            return current_time, current_time + duration
            
        current_time += timedelta(minutes=interval_minutes)
    
    return None

@app.route("/statistics", methods=["GET"])
def get_statistics():
    """Get event statistics for the current week."""
    today = datetime.now()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=7)
    
    week_events = []
    for event in events:
        if "start" not in event:
            continue
        event_start = parse_datetime(event["start"])
        if event_start and week_start <= event_start <= week_end:
            week_events.append(event)
    
    event_durations = {}
    for event in week_events:
        event_start = parse_datetime(event["start"])
        event_end = parse_datetime(event["end"])
        if event_start and event_end:
            duration = (event_end - event_start).total_seconds() / 60
            
            title = event["title"]
            if title in event_durations:
                event_durations[title] += duration
            else:
                event_durations[title] = duration
    
    sorted_events = sorted(
        event_durations.items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    return jsonify({
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "event_durations": dict(sorted_events)
    })

@app.route("/reschedule", methods=["POST"])
def reschedule_events():
    """Reschedule non-fixed events within a specified time frame."""
    data = request.json
    start_date = parse_datetime(data.get("start_date"))
    end_date = parse_datetime(data.get("end_date"))
    
    if not start_date or not end_date:
        return jsonify({"error": "Invalid date range"}), 400
    
    events_to_reschedule = []
    fixed_events = []
    
    # First, group recurring instances by parent_id
    recurring_parents = {}
    
    for event in events[:]:
        if "start" not in event:
            continue
            
        event_start = parse_datetime(event["start"])
        if not event_start or not (start_date <= event_start <= end_date):
            continue
            
        if event["type"] == "fixed":
            fixed_events.append(event)
        elif event["type"] == "recurring_instance":
            parent_id = event.get("parent_id")
            if parent_id:
                if parent_id not in recurring_parents:
                    # Find original recurring event properties
                    for e in events:
                        if e.get("id") == parent_id:
                            recurring_parents[parent_id] = {
                                "title": e["title"],
                                "priority": e["priority"],
                                "type": e["type"],
                                "duration": e.get("duration", "60"),  # Default 60 minutes
                                "frequency": e.get("frequency", "1"),  # Default daily
                                "preferred_time": e.get("preferred_time"),
                                "start_date": event_start.isoformat()
                            }
                            break
                events.remove(event)
        else:
            events.remove(event)
            events_to_reschedule.append(event)
    
    # Add recurring parent events to reschedule list
    for parent_id, parent_data in recurring_parents.items():
        events_to_reschedule.append({
            "id": parent_id,
            **parent_data
        })
    
    # Sort by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}
    events_to_reschedule.sort(key=lambda x: priority_order[x["priority"]])
    
    rescheduled_events = []
    failed_events = []
    
    for event in events_to_reschedule:
        if event["type"].startswith("recurring"):
            success = handle_recurring_event(event, event)
        elif event["type"].startswith("flexible"):
            success = handle_flexible_event(event, event)
        else:
            success = False
            
        if success:
            rescheduled_events.append(event)
        else:
            failed_events.append(event)
    
    return jsonify({
        "success": len(rescheduled_events),
        "failed": len(failed_events),
        "failed_events": failed_events
    })

def handle_recurring_event(data, new_event):
    """Handle recurring event scheduling."""
    duration = timedelta(minutes=int(data["duration"]))
    frequency = int(data["frequency"])
    start_date = parse_datetime(data.get("start_date"))
    
    if not start_date:
        return False
    
    end_date = start_date + timedelta(days=30)
    scheduled_instances = []
    current_date = start_date
    
    while current_date <= end_date:
        if data.get("type") == "recurring_with_preferred_time" and data.get("preferred_time"):
            try:
                pref_start, pref_end = parse_preferred_time(data["preferred_time"])
                
                # First try preferred time window
                day_start = datetime.combine(current_date.date(), pref_start)
                day_end = datetime.combine(current_date.date(), pref_end)
                
                slot = find_available_slot(day_start, day_end, duration)
                
                # If no slot in preferred time, try whole day
                if not slot:
                    day_start = current_date.replace(hour=0, minute=0, second=0)
                    day_end = current_date.replace(hour=23, minute=59, second=59)
                    slot = find_available_slot(day_start, day_end, duration)
                    
            except ValueError as e:
                print(f"Error parsing preferred time: {e}")
                return False
        else:
            day_start = current_date.replace(hour=0, minute=0, second=0)
            day_end = current_date.replace(hour=23, minute=59, second=59)
            slot = find_available_slot(day_start, day_end, duration)
        
        if slot:
            instance = {
                "id": len(events) + len(scheduled_instances) + 1,
                "title": data["title"],
                "priority": data["priority"],
                "type": "recurring_instance",
                "start": slot[0].isoformat(),
                "end": slot[1].isoformat(),
                "parent_id": new_event["id"]
            }
            scheduled_instances.append(instance)
        
        current_date += timedelta(days=frequency)
    
    if scheduled_instances:
        events.extend(scheduled_instances)
        return True
    return False

def handle_flexible_event(data, new_event):
    """Handle flexible event scheduling."""
    duration = timedelta(minutes=int(data["duration"]))
    earliest_start = parse_datetime(data["earliest_start"])
    deadline = parse_datetime(data["deadline"])
    
    if not earliest_start or not deadline:
        return False
        
    if data.get("type") == "flexible_with_preferred_time" and data.get("preferred_time"):
        try:
            pref_start, pref_end = parse_preferred_time(data["preferred_time"])
            
            # Try within preferred time windows first
            current_date = earliest_start.date()
            while current_date <= deadline.date():
                day_start = max(
                    datetime.combine(current_date, pref_start),
                    earliest_start if current_date == earliest_start.date() else datetime.min
                )
                day_end = min(
                    datetime.combine(current_date, pref_end),
                    deadline if current_date == deadline.date() else datetime.max
                )
                
                slot = find_available_slot(day_start, day_end, duration)
                if slot:
                    new_event.update({
                        "start": slot[0].isoformat(),
                        "end": slot[1].isoformat()
                    })
                    events.append(new_event)
                    return True
                    
                current_date += timedelta(days=1)
                
            # If no slot found in preferred times, try the whole time range
            slot = find_available_slot(earliest_start, deadline, duration)
            if slot:
                new_event.update({
                    "start": slot[0].isoformat(),
                    "end": slot[1].isoformat()
                })
                events.append(new_event)
                return True
                
        except ValueError as e:
            print(f"Error parsing preferred time: {e}")
            return False
    else:
        # Try to find any available slot in the whole range
        slot = find_available_slot(earliest_start, deadline, duration)
        if slot:
            new_event.update({
                "start": slot[0].isoformat(),
                "end": slot[1].isoformat()
            })
            events.append(new_event)
            return True
            
    return False
if __name__ == "__main__":
    app.run(debug=True)