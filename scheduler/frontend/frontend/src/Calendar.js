import React, { useState, useEffect } from "react";
import FullCalendar from "@fullcalendar/react";
import dayGridPlugin from "@fullcalendar/daygrid";
import timeGridPlugin from "@fullcalendar/timegrid";
import interactionPlugin from "@fullcalendar/interaction";
import axios from "axios";

const Calendar = () => {
  const [events, setEvents] = useState([]);
  const [activeForm, setActiveForm] = useState(null);
  const [statistics, setStatistics] = useState(null);
  const [formData, setFormData] = useState({
    title: "",
    priority: "medium",
    start: "",
    end: "",
    duration: "",
    frequency: "",
    start_date: "",
    preferred_time: "",
    earliest_start: "",
    deadline: "",
  });

  const fetchEvents = async () => {
    try {
      const response = await axios.get("http://localhost:5000/events");
      setEvents(response.data);
    } catch (error) {
      console.error("Error fetching events:", error);
    }
  };

  useEffect(() => {
    fetchEvents();
  }, []);

  const fetchStatistics = async () => {
    try {
      const response = await axios.get("http://localhost:5000/statistics");
      setStatistics(response.data);
    } catch (error) {
      console.error("Error fetching statistics:", error);
    }
  };

  const handleReschedule = async () => {
    try {
      const today = new Date();
      const thirtyDaysFromNow = new Date(today);
      thirtyDaysFromNow.setDate(today.getDate() + 30);

      const response = await axios.post("http://localhost:5000/reschedule", {
        start_date: today.toISOString(),
        end_date: thirtyDaysFromNow.toISOString(),
      });

      if (response.data.failed.length > 0) {
        alert(`${response.data.failed.length} events could not be rescheduled.`);
      } else {
        alert(`Successfully rescheduled ${response.data.success} events.`);
      }
      
      fetchEvents();
    } catch (error) {
      console.error("Error rescheduling events:", error);
      alert("Failed to reschedule events.");
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
  };

  const resetForm = () => {
    setFormData({
      title: "",
      priority: "medium",
      start: "",
      end: "",
      duration: "",
      frequency: "",
      start_date: "",
      preferred_time: "",
      earliest_start: "",
      deadline: "",
    });
    setActiveForm(null);
    setStatistics(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const eventData = {
        ...formData,
        type: activeForm,
      };

      const response = await axios.post("http://localhost:5000/events", eventData);
      setEvents([...events, response.data]);
      alert("Event added successfully!");
      resetForm();
    } catch (error) {
      if (error.response?.status === 409) {
        alert("The time slot for this event is already occupied.");
      } else {
        console.error("Error adding event:", error);
        alert("Failed to add event. Please check the console for details.");
      }
    }
  };

  const handleEventClick = async (clickInfo) => {
    if (window.confirm(`Are you sure you want to delete '${clickInfo.event.title}'?`)) {
      try {
        await axios.delete(`http://localhost:5000/events/${clickInfo.event.id}`);
        await fetchEvents();
        alert("Event deleted successfully!");
      } catch (error) {
        console.error("Error deleting event:", error);
        alert("Failed to delete event. Please try again.");
      }
    }
  };

  const renderForm = () => {
    if (!activeForm) return null;

    return (
      <form onSubmit={handleSubmit} className="event-form">
        <h3>{activeForm.replace(/_/g, " ").toUpperCase()}</h3>
        
        <div className="form-group">
          <label>Title:</label>
          <input
            type="text"
            name="title"
            value={formData.title}
            onChange={handleInputChange}
            required
          />
        </div>
        
        <div className="form-group">
          <label>Priority:</label>
          <select name="priority" value={formData.priority} onChange={handleInputChange}>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>

        {activeForm === "fixed" && (
          <>
            <div className="form-group">
              <label>Start Time:</label>
              <input
                type="datetime-local"
                name="start"
                value={formData.start}
                onChange={handleInputChange}
                required
              />
            </div>
            <div className="form-group">
              <label>End Time:</label>
              <input
                type="datetime-local"
                name="end"
                value={formData.end}
                onChange={handleInputChange}
                required
              />
            </div>
          </>
        )}

        {activeForm.startsWith("recurring") && (
          <>
            <div className="form-group">
              <label>Start Date:</label>
              <input
                type="datetime-local"
                name="start_date"
                value={formData.start_date}
                onChange={handleInputChange}
                required
              />
            </div>
            <div className="form-group">
              <label>Duration (minutes):</label>
              <input
                type="number"
                name="duration"
                value={formData.duration}
                onChange={handleInputChange}
                required
                min="1"
              />
            </div>
            <div className="form-group">
              <label>Frequency (days):</label>
              <input
                type="number"
                name="frequency"
                value={formData.frequency}
                onChange={handleInputChange}
                required
                min="1"
              />
            </div>
          </>
        )}

        {activeForm.includes("with_preferred_time") && (
          <div className="form-group">
            <label>Preferred Time (HH:MM - HH:MM):</label>
            <input
              type="text"
              name="preferred_time"
              value={formData.preferred_time}
              onChange={handleInputChange}
              placeholder="09:00 - 17:00"
              required
            />
          </div>
        )}

        {activeForm.startsWith("flexible") && (
          <>
            <div className="form-group">
              <label>Duration (minutes):</label>
              <input
                type="number"
                name="duration"
                value={formData.duration}
                onChange={handleInputChange}
                required
                min="1"
              />
            </div>
            <div className="form-group">
              <label>Earliest Start:</label>
              <input
                type="datetime-local"
                name="earliest_start"
                value={formData.earliest_start}
                onChange={handleInputChange}
                required
              />
            </div>
            <div className="form-group">
              <label>Deadline:</label>
              <input
                type="datetime-local"
                name="deadline"
                value={formData.deadline}
                onChange={handleInputChange}
                required
              />
            </div>
          </>
        )}

        <div className="form-buttons">
          <button type="submit">Create Event</button>
          <button type="button" onClick={resetForm}>Cancel</button>
        </div>
      </form>
    );
  };

  return (
    <div className="calendar-container">
      <h1>Event Scheduler</h1>
      
      <div className="top-controls">
        <div className="event-buttons">
          <button onClick={() => setActiveForm("fixed")}>
            Fixed Event
          </button>
          <button onClick={() => setActiveForm("recurring_with_preferred_time")}>
            Recurring (Preferred Time)
          </button>
          <button onClick={() => setActiveForm("recurring_without_preferred_time")}>
            Recurring (Any Time)
          </button>
          <button onClick={() => setActiveForm("flexible_with_preferred_time")}>
            Flexible (Preferred Time)
          </button>
          <button onClick={() => setActiveForm("flexible_without_preferred_time")}>
            Flexible (Any Time)
          </button>
        </div>
        
        <div className="utility-buttons">
          <button onClick={handleReschedule} className="utility-button">
            Reschedule Events
          </button>
          <button onClick={fetchStatistics} className="utility-button">
            View Statistics
          </button>
        </div>
      </div>

      {statistics && (
        <div className="statistics-panel">
          <h3>Weekly Statistics</h3>
          <p>Week of: {new Date(statistics.week_start).toLocaleDateString()}</p>
          <div className="statistics-grid">
            {Object.entries(statistics.event_durations).map(([title, duration]) => (
              <div key={title} className="stat-item">
                <strong>{title}:</strong> {Math.round(duration)} minutes
              </div>
            ))}
          </div>
          <button className="close-button" onClick={() => setStatistics(null)}>Close</button>
        </div>
      )}

      {renderForm()}

      <div className="calendar">
        <FullCalendar
          plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
          initialView="timeGridWeek"
          headerToolbar={{
            left: "prev,next today",
            center: "title",
            right: "dayGridMonth,timeGridWeek,timeGridDay",
          }}
          events={events}
          editable={false}
          selectable={true}
          height="auto"
          eventClick={handleEventClick}
        />
      </div>

      <style jsx>{`
        .calendar-container {
          padding: 20px;
          max-width: 1200px;
          margin: 0 auto;
        }
        
        h1 {
          text-align: center;
          color: #333;
          margin-bottom: 20px;
        }
        
        .top-controls {
          display: flex;
          justify-content: space-between;
          align-items: start;
          margin-bottom: 20px;
          gap: 20px;
        }
        
        .event-buttons {
          display: flex;
          gap: 10px;
          flex-wrap: wrap;
        }
        
        .utility-buttons {
          display: flex;
          gap: 10px;
        }
        
        button {
          padding: 10px 15px;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-size: 14px;
          transition: background-color 0.3s;
        }
        
        .event-buttons button {
          background-color: #4CAF50;
          color: white;
        }
        
        .utility-button {
          background-color: #2196F3;
          color: white;
        }
        
        button:hover {
          opacity: 0.9;
        }
        
        .statistics-panel {
          margin: 20px 0;
          padding: 20px;
          border: 1px solid #ddd;
          border-radius: 4px;
          background-color: #f9f9f9;
          position: relative;
        }
        
        .statistics-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
          gap: 15px;
          margin-top: 15px;
        }
        
        .stat-item {
          padding: 15px;
          background-color: white;
          border-radius: 4px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .close-button {
          position: absolute;
          top: 10px;
          right: 10px;
          background-color: #f44336;
          color: white;
          padding: 5px 10px;
        }
        
        .event-form {
          margin: 20px 0;
          padding: 20px;
          border: 1px solid #ddd;
          border-radius: 4px;
          background-color: #f9f9f9;
        }
        
        .form-group {
          margin-bottom: 15px;
        }
        
        .form-group label {
          display: block;
          margin-bottom: 5px;
          font-weight: bold;
        }
        
        .form-group input,
        .form-group select {
          width: 100%;
          padding: 8px;
          border: 1px solid #ddd;
          border-radius: 4px;
          font-size: 14px;
        }
        
        .form-buttons {
          display: flex;
          gap: 10px;
          margin-top: 20px;
        }
        
        .form-buttons button[type="submit"] {
          background-color: #4CAF50;
          color: white;
        }
        
        .form-buttons button[type="button"] {
          background-color: #f44336;
          color: white;
        }
        
        .calendar {
          margin-top: 20px;
          border: 1px solid #ddd;
          border-radius: 4px;
          padding: 10px;
          background-color: white;
        }
      `}</style>
    </div>
  );
};

export default Calendar;