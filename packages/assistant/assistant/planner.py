"""
Planning System for xSwarm Assistant

Implements GTD-style task management with projects, habits, commitments, and ideas.
The AI uses this to proactively help users plan their day and track progress.

Storage: ~/.xswarm/planning/planner.json
"""

import json
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime, date, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any
from uuid import uuid4

logger = logging.getLogger(__name__)


# ==============================================================================
# ENUMS
# ==============================================================================

class ProjectHealth(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class ProjectStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class TaskStatus(str, Enum):
    INBOX = "inbox"
    NEXT = "next"
    WAITING = "waiting"
    SCHEDULED = "scheduled"
    SOMEDAY = "someday"
    COMPLETE = "complete"


class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EnergyLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class HabitFrequency(str, Enum):
    DAILY = "daily"
    WEEKDAYS = "weekdays"
    WEEKLY = "weekly"


class InteractionMode(str, Enum):
    """Mode of AI interaction based on context."""
    MORNING_BRIEFING = "morning_briefing"
    CHECK_IN = "check_in"
    EVENING_REVIEW = "evening_review"
    CONVERSATIONAL = "conversational"


# ==============================================================================
# DATA CLASSES
# ==============================================================================

@dataclass
class Project:
    """A project with health tracking and folder associations."""
    id: str
    name: str
    description: str = ""
    folders: List[str] = field(default_factory=list)  # Associated code/content folders
    status: str = "active"
    health: str = "green"
    health_reason: str = ""
    next_action: str = ""
    area: str = "work"  # work, personal, health, learning
    target_date: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at


@dataclass
class Habit:
    """A recurring habit with streak tracking and history."""
    id: str
    name: str
    frequency: str = "daily"
    current_streak: int = 0
    best_streak: int = 0
    last_completed: Optional[str] = None  # YYYY-MM-DD
    preferred_time: str = "anytime"  # morning, afternoon, evening, anytime
    min_duration: int = 5  # minutes
    completion_history: List[str] = field(default_factory=list)  # List of YYYY-MM-DD dates
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class Goal:
    """A trackable goal with daily check-ins (e.g., weight, savings, reading pages)."""
    id: str
    name: str
    target_value: float
    current_value: float
    unit: str  # "lbs", "$", "pages", "minutes", etc.
    direction: str = "down"  # "down" (weight loss) or "up" (savings, pages read)
    start_value: float = 0.0
    start_date: str = ""
    target_date: Optional[str] = None  # YYYY-MM-DD
    check_ins: List[Dict[str, Any]] = field(default_factory=list)  # [{date, value, note}]
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.start_date:
            self.start_date = date.today().isoformat()
        if self.start_value == 0.0:
            self.start_value = self.current_value

    def progress_percent(self) -> float:
        """Calculate progress toward goal as percentage."""
        if self.direction == "down":
            # Going down (e.g., weight loss): start -> target
            total_change = self.start_value - self.target_value
            if total_change == 0:
                return 100.0
            current_change = self.start_value - self.current_value
            return min(100.0, max(0.0, (current_change / total_change) * 100))
        else:
            # Going up (e.g., savings): start -> target
            total_change = self.target_value - self.start_value
            if total_change == 0:
                return 100.0
            current_change = self.current_value - self.start_value
            return min(100.0, max(0.0, (current_change / total_change) * 100))


@dataclass
class Task:
    """GTD-style task with contexts and scheduling."""
    id: str
    title: str
    status: str = "inbox"
    priority: str = "medium"
    contexts: List[str] = field(default_factory=lambda: ["@computer"])
    energy: str = "medium"
    duration_min: int = 30
    project_id: Optional[str] = None
    due_date: Optional[str] = None  # YYYY-MM-DD
    scheduled_time: Optional[str] = None  # HH:MM for today's schedule
    completed_at: Optional[str] = None  # ISO datetime when completed
    notes: str = ""
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class Commitment:
    """An external commitment with a deadline."""
    id: str
    description: str
    to_whom: str
    deadline: str  # YYYY-MM-DD
    status: str = "pending"
    project_id: Optional[str] = None
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class Idea:
    """A captured idea for future consideration."""
    id: str
    content: str
    category: str = "feature"  # project, feature, someday, reference
    captured_at: str = ""
    processed: bool = False

    def __post_init__(self):
        if not self.captured_at:
            self.captured_at = datetime.now().isoformat()


@dataclass
class DailyFocus:
    """Today's focus and priorities."""
    date: str  # YYYY-MM-DD
    top_priorities: List[str] = field(default_factory=list)  # Task IDs
    energy_level: str = "medium"
    notes: str = ""


class RecurrenceType(str, Enum):
    """Type of event recurrence."""
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


@dataclass
class CalendarEvent:
    """A calendar event or meeting."""
    id: str
    title: str
    start_time: str  # ISO format datetime
    end_time: str  # ISO format datetime
    description: str = ""
    location: str = ""
    attendees: List[str] = field(default_factory=list)
    recurrence: str = "none"  # RecurrenceType value
    recurrence_end: Optional[str] = None  # YYYY-MM-DD for recurring events
    reminder_minutes: int = 15  # Minutes before event to remind
    project_id: Optional[str] = None
    created_at: str = ""
    # Fields for recurring instances (not persisted, set during expansion)
    _is_recurring_instance: bool = False
    _original_id: Optional[str] = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


# ==============================================================================
# PLANNER DATA (Persistence Layer)
# ==============================================================================

class PlannerData:
    """
    Single-file persistent storage for planning data.
    Follows UserProfile pattern from memory.py.
    """

    DEFAULT_DIR = Path.home() / ".xswarm" / "planning"

    def __init__(self, storage_dir: Optional[Path] = None):
        """Initialize planner storage."""
        self.storage_dir = storage_dir or self.DEFAULT_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._data: Optional[Dict] = None

    def _planner_path(self) -> Path:
        """Get path to planner file."""
        return self.storage_dir / "planner.json"

    def _load(self, force_reload: bool = False) -> Dict:
        """Load data from disk (lazy loading with optional force reload)."""
        if self._data is not None and not force_reload:
            return self._data

        path = self._planner_path()
        if not path.exists():
            self._data = self._default_data()
            return self._data

        try:
            with open(path, 'r', encoding='utf-8') as f:
                self._data = json.load(f)
                return self._data
        except Exception as e:
            logger.warning(f"Failed to load planner data: {e}")
            self._data = self._default_data()
            return self._data

    def reload(self) -> None:
        """Force reload data from disk (useful for widgets that need fresh data)."""
        self._data = None
        self._load()

    def _save(self) -> None:
        """Save data to disk."""
        if self._data is None:
            return

        try:
            self._data["updated_at"] = datetime.now().isoformat()
            with open(self._planner_path(), 'w', encoding='utf-8') as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to save planner data: {e}")

    def _default_data(self) -> Dict:
        """Default empty planner structure."""
        return {
            "version": "1.2",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "last_daily_planning": None,
            "last_review": None,
            "projects": [],
            "habits": [],
            "goals": [],
            "tasks": [],
            "commitments": [],
            "ideas": [],
            "calendar_events": [],
            "daily_focus": None
        }

    def _generate_id(self, prefix: str) -> str:
        """Generate a unique ID with prefix."""
        return f"{prefix}_{uuid4().hex[:8]}"

    # ==========================================================================
    # PROJECTS CRUD
    # ==========================================================================

    def get_projects(self, status: Optional[str] = None) -> List[Project]:
        """Get all projects, optionally filtered by status."""
        data = self._load()
        projects = [Project(**p) for p in data["projects"]]
        if status:
            projects = [p for p in projects if p.status == status]
        return projects

    def get_project(self, project_id: str) -> Optional[Project]:
        """Get a single project by ID."""
        for p in self.get_projects():
            if p.id == project_id:
                return p
        return None

    def add_project(
        self,
        name: str,
        description: str = "",
        folders: Optional[List[str]] = None,
        area: str = "work",
        target_date: Optional[str] = None,
        next_action: str = ""
    ) -> Project:
        """Add a new project."""
        data = self._load()
        project = Project(
            id=self._generate_id("proj"),
            name=name,
            description=description,
            folders=folders or [],
            area=area,
            target_date=target_date,
            next_action=next_action
        )
        data["projects"].append(asdict(project))
        self._save()
        return project

    def update_project(
        self,
        project_id: str,
        **updates
    ) -> Optional[Project]:
        """Update a project's fields."""
        data = self._load()
        for i, p in enumerate(data["projects"]):
            if p["id"] == project_id:
                p.update(updates)
                p["updated_at"] = datetime.now().isoformat()
                self._save()
                return Project(**p)
        return None

    def update_project_health(
        self,
        project_id: str,
        health: str,
        reason: str = ""
    ) -> Optional[Project]:
        """Update project health status."""
        return self.update_project(
            project_id,
            health=health,
            health_reason=reason
        )

    # ==========================================================================
    # HABITS CRUD
    # ==========================================================================

    def get_habits(self) -> List[Habit]:
        """Get all habits."""
        data = self._load()
        return [Habit(**h) for h in data["habits"]]

    def get_habit(self, habit_id: str) -> Optional[Habit]:
        """Get a single habit by ID."""
        for h in self.get_habits():
            if h.id == habit_id:
                return h
        return None

    def get_habit_by_name(self, name: str) -> Optional[Habit]:
        """Get a habit by name (case-insensitive)."""
        name_lower = name.lower().strip()
        for h in self.get_habits():
            if h.name.lower().strip() == name_lower:
                return h
        return None

    def add_habit(
        self,
        name: str,
        frequency: str = "daily",
        preferred_time: str = "anytime",
        min_duration: int = 5
    ) -> Habit:
        """Add a new habit to track."""
        data = self._load()
        habit = Habit(
            id=self._generate_id("hab"),
            name=name,
            frequency=frequency,
            preferred_time=preferred_time,
            min_duration=min_duration
        )
        data["habits"].append(asdict(habit))
        self._save()
        return habit

    def log_habit(self, habit_id: str, log_date: Optional[str] = None) -> Optional[Habit]:
        """
        Log habit completion for a date (default: today).
        Updates streak automatically and tracks completion history.
        """
        data = self._load()
        today = log_date or date.today().isoformat()

        for i, h in enumerate(data["habits"]):
            if h["id"] == habit_id:
                last = h.get("last_completed")

                # Already logged today
                if last == today:
                    return Habit(**h)

                # Calculate streak
                if last:
                    last_date = date.fromisoformat(last)
                    today_date = date.fromisoformat(today)
                    days_diff = (today_date - last_date).days

                    if days_diff == 1:
                        # Consecutive day - extend streak
                        h["current_streak"] = h.get("current_streak", 0) + 1
                    elif days_diff > 1:
                        # Streak broken - restart
                        h["current_streak"] = 1
                    # days_diff == 0 shouldn't happen (caught above)
                else:
                    # First ever completion
                    h["current_streak"] = 1

                h["last_completed"] = today
                h["best_streak"] = max(h.get("best_streak", 0), h["current_streak"])

                # Track completion history for visual streak representation
                if "completion_history" not in h:
                    h["completion_history"] = []
                if today not in h["completion_history"]:
                    h["completion_history"].append(today)
                    # Keep history sorted and limited to last 365 days
                    h["completion_history"].sort()
                    if len(h["completion_history"]) > 365:
                        h["completion_history"] = h["completion_history"][-365:]

                self._save()
                return Habit(**h)

        return None

    def log_habit_by_name(self, name: str, log_date: Optional[str] = None) -> Optional[Habit]:
        """Log habit completion by name."""
        habit = self.get_habit_by_name(name)
        if habit:
            return self.log_habit(habit.id, log_date)
        return None

    def get_habits_due_today(self) -> List[Habit]:
        """Get habits that should be done today but haven't been logged."""
        today = date.today()
        today_str = today.isoformat()
        weekday = today.weekday()  # 0=Monday, 6=Sunday

        due = []
        for habit in self.get_habits():
            # Check if already done today
            if habit.last_completed == today_str:
                continue

            # Check frequency
            if habit.frequency == "daily":
                due.append(habit)
            elif habit.frequency == "weekdays" and weekday < 5:
                due.append(habit)
            elif habit.frequency == "weekly":
                # Check if done this week
                if habit.last_completed:
                    last = date.fromisoformat(habit.last_completed)
                    # If last completion was more than 7 days ago
                    if (today - last).days >= 7:
                        due.append(habit)
                else:
                    due.append(habit)

        return due

    def get_streaks_at_risk(self) -> List[Habit]:
        """Get habits with streaks that will break if not logged today."""
        today_str = date.today().isoformat()
        at_risk = []

        for habit in self.get_habits():
            # Has a streak and not yet logged today
            if habit.current_streak > 0 and habit.last_completed != today_str:
                at_risk.append(habit)

        return at_risk

    def get_habit_streak_visual(self, habit_id: str, weeks: int = 12) -> List[List[bool]]:
        """
        Get a visual grid of habit completion for streak visualization.
        Returns a list of weeks, each containing 7 days (Mon-Sun).
        True = completed, False = not completed.
        """
        habit = self.get_habit(habit_id)
        if not habit:
            return []

        today = date.today()
        history_set = set(habit.completion_history)

        # Generate grid for last N weeks
        grid = []
        # Start from the beginning of the oldest week we want to show
        start_date = today - timedelta(days=(weeks * 7) + today.weekday())

        for week_num in range(weeks):
            week = []
            for day_num in range(7):  # Mon=0 to Sun=6
                check_date = start_date + timedelta(days=(week_num * 7) + day_num)
                if check_date <= today:
                    completed = check_date.isoformat() in history_set
                    week.append(completed)
                else:
                    week.append(None)  # Future date
            grid.append(week)

        return grid

    # ==========================================================================
    # GOALS CRUD
    # ==========================================================================

    def get_goals(self) -> List[Goal]:
        """Get all goals."""
        data = self._load()
        goals_data = data.get("goals", [])
        return [Goal(**g) for g in goals_data]

    def get_goal(self, goal_id: str) -> Optional[Goal]:
        """Get a single goal by ID."""
        for g in self.get_goals():
            if g.id == goal_id:
                return g
        return None

    def get_goal_by_name(self, name: str) -> Optional[Goal]:
        """Get a goal by name (case-insensitive)."""
        name_lower = name.lower().strip()
        for g in self.get_goals():
            if g.name.lower().strip() == name_lower:
                return g
        return None

    def add_goal(
        self,
        name: str,
        target_value: float,
        current_value: float,
        unit: str,
        direction: str = "down",
        target_date: Optional[str] = None
    ) -> Goal:
        """
        Add a new trackable goal.

        Args:
            name: Goal name (e.g., "Weight", "Savings", "Pages Read")
            target_value: Target value to reach
            current_value: Starting/current value
            unit: Unit of measurement (e.g., "lbs", "$", "pages")
            direction: "down" for decreasing (weight loss) or "up" for increasing (savings)
            target_date: Optional target date to reach the goal (YYYY-MM-DD)
        """
        data = self._load()
        if "goals" not in data:
            data["goals"] = []

        goal = Goal(
            id=self._generate_id("goal"),
            name=name,
            target_value=target_value,
            current_value=current_value,
            unit=unit,
            direction=direction,
            start_value=current_value,
            target_date=target_date
        )
        data["goals"].append(asdict(goal))
        self._save()
        return goal

    def log_goal_checkin(
        self,
        goal_id: str,
        value: float,
        note: str = "",
        checkin_date: Optional[str] = None
    ) -> Optional[Goal]:
        """
        Log a check-in for a goal (e.g., weigh-in, savings update).
        Updates the current value and records the check-in.
        """
        data = self._load()
        today = checkin_date or date.today().isoformat()

        for g in data.get("goals", []):
            if g["id"] == goal_id:
                # Update current value
                g["current_value"] = value

                # Record check-in
                if "check_ins" not in g:
                    g["check_ins"] = []

                g["check_ins"].append({
                    "date": today,
                    "value": value,
                    "note": note
                })

                # Keep check-ins sorted by date
                g["check_ins"].sort(key=lambda x: x["date"])

                self._save()
                return Goal(**g)

        return None

    def log_goal_checkin_by_name(
        self,
        name: str,
        value: float,
        note: str = "",
        checkin_date: Optional[str] = None
    ) -> Optional[Goal]:
        """Log a goal check-in by name."""
        goal = self.get_goal_by_name(name)
        if goal:
            return self.log_goal_checkin(goal.id, value, note, checkin_date)
        return None

    def update_goal(self, goal_id: str, **updates) -> Optional[Goal]:
        """Update a goal's fields."""
        data = self._load()
        for g in data.get("goals", []):
            if g["id"] == goal_id:
                for key, value in updates.items():
                    if key in g and value is not None:
                        g[key] = value
                self._save()
                return Goal(**g)
        return None

    def delete_goal(self, goal_id: str) -> bool:
        """Delete a goal by ID."""
        data = self._load()
        goals = data.get("goals", [])
        original_len = len(goals)
        data["goals"] = [g for g in goals if g["id"] != goal_id]
        if len(data["goals"]) < original_len:
            self._save()
            return True
        return False

    def get_goal_progress_visual(self, goal_id: str) -> Dict[str, Any]:
        """
        Get visual progress data for a goal including trend information.
        Returns data suitable for progress bar and trend visualization.
        """
        goal = self.get_goal(goal_id)
        if not goal:
            return {}

        progress = goal.progress_percent()

        # Calculate trend from last 7 check-ins
        trend = "stable"
        recent_checkins = goal.check_ins[-7:] if len(goal.check_ins) >= 2 else []

        if len(recent_checkins) >= 2:
            first_value = recent_checkins[0]["value"]
            last_value = recent_checkins[-1]["value"]

            if goal.direction == "down":
                # For weight loss: lower is better
                if last_value < first_value:
                    trend = "improving"
                elif last_value > first_value:
                    trend = "declining"
            else:
                # For savings: higher is better
                if last_value > first_value:
                    trend = "improving"
                elif last_value < first_value:
                    trend = "declining"

        return {
            "name": goal.name,
            "current": goal.current_value,
            "target": goal.target_value,
            "start": goal.start_value,
            "unit": goal.unit,
            "direction": goal.direction,
            "progress_percent": progress,
            "trend": trend,
            "checkins_count": len(goal.check_ins),
            "target_date": goal.target_date,
            "recent_checkins": goal.check_ins[-5:] if goal.check_ins else []
        }

    # ==========================================================================
    # TASKS CRUD
    # ==========================================================================

    def get_tasks(
        self,
        status: Optional[str] = None,
        context: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> List[Task]:
        """Get tasks with optional filters."""
        data = self._load()
        tasks = [Task(**t) for t in data["tasks"]]

        if status:
            tasks = [t for t in tasks if t.status == status]
        if context:
            tasks = [t for t in tasks if context in t.contexts]
        if project_id:
            tasks = [t for t in tasks if t.project_id == project_id]

        return tasks

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a single task by ID."""
        for t in self.get_tasks():
            if t.id == task_id:
                return t
        return None

    def add_task(
        self,
        title: str,
        priority: str = "medium",
        contexts: Optional[List[str]] = None,
        energy: str = "medium",
        duration_min: int = 30,
        project_id: Optional[str] = None,
        due_date: Optional[str] = None,
        scheduled_time: Optional[str] = None,
        status: str = "inbox",
        notes: str = "",
        auto_schedule: bool = True
    ) -> Task:
        """Add a new task. Auto-schedules by default."""
        data = self._load()
        task = Task(
            id=self._generate_id("task"),
            title=title,
            priority=priority,
            contexts=contexts or ["@computer"],
            energy=energy,
            duration_min=duration_min,
            project_id=project_id,
            due_date=due_date,
            scheduled_time=scheduled_time,
            status=status,
            notes=notes
        )
        data["tasks"].append(asdict(task))
        self._save()

        # Auto-schedule all unscheduled tasks if enabled
        if auto_schedule and not scheduled_time:
            self.auto_schedule_tasks()
            # Reload to get updated task with scheduled_time
            self.reload()
            updated = self.get_task(task.id)
            if updated:
                return updated

        return task

    def complete_task(self, task_id: str, reschedule: bool = True) -> Optional[Task]:
        """Mark a task as complete with timestamp. Reschedules remaining tasks by default."""
        data = self._load()
        for i, t in enumerate(data["tasks"]):
            if t["id"] == task_id:
                t["status"] = "complete"
                t["completed_at"] = datetime.now().isoformat()
                self._save()

                # Reschedule remaining tasks to fill the gap
                if reschedule:
                    self.auto_schedule_tasks()

                return Task(**t)
        return None

    def update_task(self, task_id: str, **updates) -> Optional[Task]:
        """Update task fields."""
        data = self._load()
        for i, t in enumerate(data["tasks"]):
            if t["id"] == task_id:
                t.update(updates)
                self._save()
                return Task(**t)
        return None

    def auto_schedule_tasks(self, work_start: str = "09:00", work_end: str = "18:00") -> int:
        """
        Auto-schedule unscheduled tasks into available time slots.
        Returns number of tasks scheduled.

        Algorithm:
        0. Clear scheduled_time for past tasks (GPS-like: adjust to reality)
        1. Build timeline of blocked time (events, habits, already-scheduled tasks)
        2. Find gaps in timeline
        3. Assign unscheduled tasks to gaps by priority
        """
        from datetime import datetime as dt

        now = dt.now()
        today_str = now.date().isoformat()
        current_time = now.strftime("%H:%M")

        # Parse work hours
        def time_to_minutes(t: str) -> int:
            """Convert HH:MM to minutes since midnight."""
            h, m = map(int, t.split(":"))
            return h * 60 + m

        def minutes_to_time(mins: int) -> str:
            """Convert minutes since midnight to HH:MM."""
            h = mins // 60
            m = mins % 60
            return f"{h:02d}:{m:02d}"

        work_start_mins = time_to_minutes(work_start)
        work_end_mins = time_to_minutes(work_end)
        current_mins = time_to_minutes(current_time)

        # Start from now if within work hours, otherwise from work start
        schedule_start = max(work_start_mins, current_mins)

        # Can't schedule if past work hours
        if schedule_start >= work_end_mins:
            return 0

        # 0. GPS-like adjustment: Clear ALL scheduled_time and reschedule from scratch
        # This ensures priorities are always respected and schedule reacts to changes
        data = self._load()
        tasks_cleared = 0
        for task in data["tasks"]:
            if task.get("status") not in ["complete", "someday"]:
                if task.get("scheduled_time"):
                    task["scheduled_time"] = None
                    tasks_cleared += 1
        if tasks_cleared > 0:
            self._save()
            self.reload()  # Reload after clearing

        # 1. Build list of blocked time intervals [(start_mins, end_mins), ...]
        blocked = []

        # Block calendar events
        for event in self.get_todays_events():
            try:
                if "T" in event.start_time:
                    event_time = event.start_time[11:16]
                    start = time_to_minutes(event_time)
                    # Assume 60 min default duration
                    end = start + 60
                    blocked.append((start, end))
            except Exception:
                continue

        # Block habits at their preferred times
        today = date.today()
        weekday = today.weekday()
        time_map = {"morning": (480, 540), "afternoon": (840, 900), "evening": (1140, 1200)}  # 8-9, 14-15, 19-20

        for habit in self.get_habits():
            # Check if habit is for today
            show_today = False
            if habit.frequency == "daily":
                show_today = True
            elif habit.frequency == "weekdays" and weekday < 5:
                show_today = True
            elif habit.frequency == "weekly":
                show_today = True

            if show_today and habit.preferred_time in time_map:
                start, end = time_map[habit.preferred_time]
                blocked.append((start, end))

        # Block already-scheduled tasks
        for task in self.get_tasks():
            if task.scheduled_time and task.status not in ["complete", "someday"]:
                try:
                    start = time_to_minutes(task.scheduled_time)
                    end = start + task.duration_min
                    blocked.append((start, end))
                except Exception:
                    continue

        # Sort and merge overlapping blocks
        blocked.sort()
        merged = []
        for start, end in blocked:
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))

        # 2. Find available time slots
        available = []
        prev_end = schedule_start

        for block_start, block_end in merged:
            if block_start > prev_end:
                # Gap found
                available.append((prev_end, block_start))
            prev_end = max(prev_end, block_end)

        # Add time until work end
        if prev_end < work_end_mins:
            available.append((prev_end, work_end_mins))

        # 3. Get unscheduled tasks (inbox, next, scheduled without time)
        unscheduled = []
        for task in self.get_tasks():
            if task.status in ["inbox", "next", "scheduled"]:
                if not task.scheduled_time:
                    unscheduled.append(task)

        # Sort by priority (critical first, then high, medium, low)
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        unscheduled.sort(key=lambda t: priority_order.get(t.priority, 2))

        # 4. Schedule tasks into available slots using bin-packing approach
        # Track used time per slot: [(slot_idx, used_minutes), ...]
        slot_usage = [0] * len(available)  # Minutes used in each slot
        scheduled_count = 0

        for task in unscheduled:
            duration = task.duration_min or 30

            # Find the first slot that can fit this task
            scheduled = False
            for slot_idx, (slot_start, slot_end) in enumerate(available):
                slot_capacity = slot_end - slot_start
                slot_remaining = slot_capacity - slot_usage[slot_idx]

                if duration <= slot_remaining:
                    # Schedule this task in this slot
                    scheduled_time = minutes_to_time(slot_start + slot_usage[slot_idx])
                    self.update_task(task.id, scheduled_time=scheduled_time, status="scheduled")
                    slot_usage[slot_idx] += duration
                    scheduled_count += 1
                    scheduled = True
                    break

            # If task didn't fit anywhere, it stays unscheduled (skip it, try next task)

        return scheduled_count

    def reschedule_day(self, work_start: str = "09:00", work_end: str = "18:00") -> int:
        """
        Clear all scheduled times and reschedule from scratch.
        Like GPS recalculating entire route when you go significantly off course.
        """
        data = self._load()

        # Clear scheduled_time for all non-complete tasks
        for task in data["tasks"]:
            if task.get("status") not in ["complete", "someday"]:
                task["scheduled_time"] = None

        self._save()

        # Now auto-schedule everything fresh
        return self.auto_schedule_tasks(work_start, work_end)

    def get_overdue_tasks(self) -> List[Task]:
        """Get tasks that are past their due date."""
        today = date.today().isoformat()
        overdue = []

        for task in self.get_tasks():
            if task.status not in ["complete", "someday"]:
                if task.due_date and task.due_date < today:
                    overdue.append(task)

        return overdue

    # ==========================================================================
    # COMMITMENTS CRUD
    # ==========================================================================

    def get_commitments(self, include_completed: bool = False) -> List[Commitment]:
        """Get commitments."""
        data = self._load()
        commitments = [Commitment(**c) for c in data["commitments"]]

        if not include_completed:
            commitments = [c for c in commitments if c.status == "pending"]

        return commitments

    def add_commitment(
        self,
        description: str,
        to_whom: str,
        deadline: str,
        project_id: Optional[str] = None
    ) -> Commitment:
        """Add a commitment."""
        data = self._load()
        commitment = Commitment(
            id=self._generate_id("com"),
            description=description,
            to_whom=to_whom,
            deadline=deadline,
            project_id=project_id
        )
        data["commitments"].append(asdict(commitment))
        self._save()
        return commitment

    def complete_commitment(self, commitment_id: str) -> Optional[Commitment]:
        """Mark commitment as complete."""
        data = self._load()
        for c in data["commitments"]:
            if c["id"] == commitment_id:
                c["status"] = "complete"
                self._save()
                return Commitment(**c)
        return None

    def get_upcoming_commitments(self, days: int = 7) -> List[Commitment]:
        """Get commitments due within N days."""
        today = date.today()
        cutoff = (today + timedelta(days=days)).isoformat()
        today_str = today.isoformat()

        upcoming = []
        for c in self.get_commitments():
            if today_str <= c.deadline <= cutoff:
                upcoming.append(c)

        # Sort by deadline
        upcoming.sort(key=lambda x: x.deadline)
        return upcoming

    def get_overdue_commitments(self) -> List[Commitment]:
        """Get commitments that are past deadline."""
        today = date.today().isoformat()
        return [c for c in self.get_commitments() if c.deadline < today]

    # ==========================================================================
    # IDEAS CRUD
    # ==========================================================================

    def get_ideas(self, processed: Optional[bool] = None) -> List[Idea]:
        """Get ideas."""
        data = self._load()
        ideas = [Idea(**i) for i in data["ideas"]]

        if processed is not None:
            ideas = [i for i in ideas if i.processed == processed]

        return ideas

    def capture_idea(self, content: str, category: str = "feature") -> Idea:
        """Capture a new idea."""
        data = self._load()
        idea = Idea(
            id=self._generate_id("idea"),
            content=content,
            category=category
        )
        data["ideas"].append(asdict(idea))
        self._save()
        return idea

    def process_idea(self, idea_id: str) -> Optional[Idea]:
        """Mark idea as processed."""
        data = self._load()
        for i in data["ideas"]:
            if i["id"] == idea_id:
                i["processed"] = True
                self._save()
                return Idea(**i)
        return None

    def delete_idea(self, idea_id: str) -> bool:
        """Delete an idea by ID."""
        data = self._load()
        original_len = len(data["ideas"])
        data["ideas"] = [i for i in data["ideas"] if i["id"] != idea_id]
        if len(data["ideas"]) < original_len:
            self._save()
            return True
        return False

    # ==========================================================================
    # CALENDAR EVENTS CRUD
    # ==========================================================================

    def _expand_recurring_event(
        self,
        event: Dict[str, Any],
        start_date: str,
        end_date: str
    ) -> List[Dict[str, Any]]:
        """
        Expand a recurring event into instances within the date range.
        Returns list of event dicts (virtual instances with modified start/end times).
        """
        recurrence = event.get("recurrence", "none")
        if recurrence == "none":
            return []

        instances = []
        event_start = datetime.fromisoformat(event["start_time"])
        event_end = datetime.fromisoformat(event["end_time"])
        duration = event_end - event_start

        # Determine recurrence end date
        recurrence_end_str = event.get("recurrence_end")
        if recurrence_end_str:
            recurrence_end = date.fromisoformat(recurrence_end_str)
        else:
            # Default: 1 year from original event if no end specified
            recurrence_end = event_start.date() + timedelta(days=365)

        # Parse query range
        query_start = date.fromisoformat(start_date)
        query_end = date.fromisoformat(end_date)

        # Determine delta based on recurrence type
        if recurrence == "daily":
            delta = timedelta(days=1)
        elif recurrence == "weekly":
            delta = timedelta(weeks=1)
        elif recurrence == "biweekly":
            delta = timedelta(weeks=2)
        elif recurrence == "monthly":
            delta = None  # Handle monthly specially
        elif recurrence == "yearly":
            delta = None  # Handle yearly specially
        else:
            return []

        # Generate instances
        current = event_start
        iteration = 0
        max_iterations = 1000  # Safety limit

        while iteration < max_iterations:
            iteration += 1
            current_date = current.date()

            # Stop if past recurrence end
            if current_date > recurrence_end:
                break

            # Stop if past query range
            if current_date > query_end:
                break

            # Include if within query range AND not the original event date
            original_date = event_start.date()
            if query_start <= current_date <= query_end and current_date != original_date:
                # Create virtual instance
                instance = event.copy()
                instance["start_time"] = current.isoformat()
                instance["end_time"] = (current + duration).isoformat()
                # Mark as recurring instance (useful for UI)
                instance["_is_recurring_instance"] = True
                instance["_original_id"] = event["id"]
                instances.append(instance)

            # Advance to next occurrence
            if delta:
                current = current + delta
            elif recurrence == "monthly":
                # Add one month, preserving day of month
                month = current.month + 1
                year = current.year
                if month > 12:
                    month = 1
                    year += 1
                # Handle month overflow (e.g., Jan 31 -> Feb 28)
                day = min(current.day, 28)  # Safe default
                try:
                    current = current.replace(year=year, month=month, day=current.day)
                except ValueError:
                    current = current.replace(year=year, month=month, day=day)
            elif recurrence == "yearly":
                # Add one year
                try:
                    current = current.replace(year=current.year + 1)
                except ValueError:
                    # Feb 29 on non-leap year
                    current = current.replace(year=current.year + 1, day=28)

        return instances

    def get_calendar_events(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        expand_recurring: bool = True
    ) -> List[CalendarEvent]:
        """
        Get calendar events, optionally filtered by date range.
        If expand_recurring=True, recurring events are expanded into instances.
        """
        data = self._load()
        events = data.get("calendar_events", [])
        result = []

        # Default date range for expansion (if not specified)
        if expand_recurring and not start_date:
            start_date = date.today().isoformat()
        if expand_recurring and not end_date:
            end_date = (date.today() + timedelta(days=30)).isoformat()

        for e in events:
            event_date = e["start_time"][:10]

            # Check if original event is in range
            in_range = True
            if start_date and event_date < start_date:
                in_range = False
            if end_date and event_date > end_date:
                in_range = False

            if in_range:
                result.append(e)

            # Expand recurring events if requested
            if expand_recurring and e.get("recurrence", "none") != "none":
                instances = self._expand_recurring_event(e, start_date, end_date)
                result.extend(instances)

        # Sort by start time
        result.sort(key=lambda x: x["start_time"])

        return [CalendarEvent(**e) for e in result]

    def get_calendar_event(self, event_id: str) -> Optional[CalendarEvent]:
        """Get a specific calendar event by ID."""
        data = self._load()
        for e in data.get("calendar_events", []):
            if e["id"] == event_id:
                return CalendarEvent(**e)
        return None

    def add_calendar_event(
        self,
        title: str,
        start_time: str,
        end_time: str,
        description: str = "",
        location: str = "",
        attendees: Optional[List[str]] = None,
        recurrence: str = "none",
        recurrence_end: Optional[str] = None,
        reminder_minutes: int = 15,
        project_id: Optional[str] = None
    ) -> CalendarEvent:
        """Add a new calendar event."""
        data = self._load()
        if "calendar_events" not in data:
            data["calendar_events"] = []

        event = CalendarEvent(
            id=self._generate_id("evt"),
            title=title,
            start_time=start_time,
            end_time=end_time,
            description=description,
            location=location,
            attendees=attendees or [],
            recurrence=recurrence,
            recurrence_end=recurrence_end,
            reminder_minutes=reminder_minutes,
            project_id=project_id
        )
        data["calendar_events"].append(asdict(event))
        self._save()
        return event

    def update_calendar_event(
        self, event_id: str, **updates
    ) -> Optional[CalendarEvent]:
        """Update a calendar event."""
        data = self._load()
        for e in data.get("calendar_events", []):
            if e["id"] == event_id:
                for key, value in updates.items():
                    if key in e and value is not None:
                        e[key] = value
                self._save()
                return CalendarEvent(**e)
        return None

    def delete_calendar_event(self, event_id: str) -> bool:
        """Delete a calendar event by ID."""
        data = self._load()
        events = data.get("calendar_events", [])
        original_len = len(events)
        data["calendar_events"] = [e for e in events if e["id"] != event_id]
        if len(data["calendar_events"]) < original_len:
            self._save()
            return True
        return False

    def get_upcoming_events(self, days: int = 7) -> List[CalendarEvent]:
        """Get events in the next N days."""
        today = date.today()
        end = today + timedelta(days=days)
        return self.get_calendar_events(
            start_date=today.isoformat(),
            end_date=end.isoformat()
        )

    def get_todays_events(self) -> List[CalendarEvent]:
        """Get all events for today."""
        today = date.today().isoformat()
        return self.get_calendar_events(start_date=today, end_date=today)

    # ==========================================================================
    # DELETE METHODS FOR OTHER ENTITIES
    # ==========================================================================

    def delete_task(self, task_id: str) -> bool:
        """Delete a task by ID."""
        data = self._load()
        original_len = len(data["tasks"])
        data["tasks"] = [t for t in data["tasks"] if t["id"] != task_id]
        if len(data["tasks"]) < original_len:
            self._save()
            return True
        return False

    def delete_project(self, project_id: str) -> bool:
        """Delete a project by ID."""
        data = self._load()
        original_len = len(data["projects"])
        data["projects"] = [p for p in data["projects"] if p["id"] != project_id]
        if len(data["projects"]) < original_len:
            self._save()
            return True
        return False

    def delete_habit(self, habit_id: str) -> bool:
        """Delete a habit by ID."""
        data = self._load()
        original_len = len(data["habits"])
        data["habits"] = [h for h in data["habits"] if h["id"] != habit_id]
        if len(data["habits"]) < original_len:
            self._save()
            return True
        return False

    def delete_commitment(self, commitment_id: str) -> bool:
        """Delete a commitment by ID."""
        data = self._load()
        original_len = len(data["commitments"])
        data["commitments"] = [c for c in data["commitments"] if c["id"] != commitment_id]
        if len(data["commitments"]) < original_len:
            self._save()
            return True
        return False

    def update_habit(self, habit_id: str, **updates) -> Optional[Habit]:
        """Update a habit."""
        data = self._load()
        for h in data["habits"]:
            if h["id"] == habit_id:
                for key, value in updates.items():
                    if key in h and value is not None:
                        h[key] = value
                self._save()
                return Habit(**h)
        return None

    # ==========================================================================
    # DAILY PLANNING
    # ==========================================================================

    def was_planning_done_today(self) -> bool:
        """Check if daily planning was completed today."""
        data = self._load()
        last = data.get("last_daily_planning")
        if not last:
            return False
        return last[:10] == date.today().isoformat()

    def mark_planning_done(self) -> None:
        """Mark daily planning as complete."""
        data = self._load()
        data["last_daily_planning"] = datetime.now().isoformat()
        self._save()

    def was_review_done_today(self) -> bool:
        """Check if evening review was done today."""
        data = self._load()
        last = data.get("last_review")
        if not last:
            return False
        return last[:10] == date.today().isoformat()

    def mark_review_done(self) -> None:
        """Mark evening review as complete."""
        data = self._load()
        data["last_review"] = datetime.now().isoformat()
        self._save()

    def set_daily_focus(
        self,
        priorities: List[str],
        energy_level: str = "medium",
        notes: str = ""
    ) -> DailyFocus:
        """Set today's focus and priorities."""
        data = self._load()
        focus = DailyFocus(
            date=date.today().isoformat(),
            top_priorities=priorities,
            energy_level=energy_level,
            notes=notes
        )
        data["daily_focus"] = asdict(focus)
        self._save()
        return focus

    def get_daily_focus(self) -> Optional[DailyFocus]:
        """Get today's focus (if set)."""
        data = self._load()
        focus_data = data.get("daily_focus")
        if focus_data and focus_data.get("date") == date.today().isoformat():
            return DailyFocus(**focus_data)
        return None

    # ==========================================================================
    # SUMMARY / CONTEXT GENERATION
    # ==========================================================================

    def get_planning_summary(self) -> Dict[str, Any]:
        """Get summary for AI context injection."""
        today = date.today()
        today_str = today.isoformat()

        # Projects
        active_projects = self.get_projects(status="active")
        projects_needing_attention = [
            p for p in active_projects
            if p.health in ("yellow", "red")
        ]

        # Tasks
        pending_tasks = self.get_tasks(status="next") + self.get_tasks(status="inbox")
        overdue_tasks = self.get_overdue_tasks()

        # Group tasks by context
        tasks_by_context: Dict[str, int] = {}
        for t in pending_tasks:
            for ctx in t.contexts:
                tasks_by_context[ctx] = tasks_by_context.get(ctx, 0) + 1

        # Habits
        habits = self.get_habits()
        habits_due = self.get_habits_due_today()
        streaks_at_risk = self.get_streaks_at_risk()

        # Goals
        goals = self.get_goals()
        goals_summary = []
        for g in goals:
            progress = g.progress_percent()
            # Determine if goal needs attention (stalled or behind pace)
            needs_attention = False
            if g.check_ins:
                # Check if any check-in in last 7 days
                last_checkin = g.check_ins[-1]["date"] if g.check_ins else None
                if last_checkin:
                    days_since = (today - date.fromisoformat(last_checkin)).days
                    if days_since > 7:
                        needs_attention = True

            goals_summary.append({
                "name": g.name,
                "current": g.current_value,
                "target": g.target_value,
                "unit": g.unit,
                "direction": g.direction,
                "progress_percent": progress,
                "needs_attention": needs_attention,
                "target_date": g.target_date
            })

        # Commitments
        upcoming_commitments = self.get_upcoming_commitments(days=7)
        overdue_commitments = self.get_overdue_commitments()

        # Ideas
        unprocessed_ideas = len(self.get_ideas(processed=False))

        return {
            "date": today_str,
            "planning_done": self.was_planning_done_today(),
            "review_done": self.was_review_done_today(),

            # Projects
            "active_projects_count": len(active_projects),
            "active_projects": [
                {"name": p.name, "health": p.health, "health_reason": p.health_reason}
                for p in active_projects
            ],
            "projects_needing_attention": [
                {"name": p.name, "health": p.health, "reason": p.health_reason}
                for p in projects_needing_attention
            ],

            # Tasks
            "pending_tasks_count": len(pending_tasks),
            "overdue_tasks_count": len(overdue_tasks),
            "overdue_tasks": [
                {"title": t.title, "due": t.due_date, "priority": t.priority}
                for t in overdue_tasks
            ],
            "tasks_by_context": tasks_by_context,

            # Habits
            "habits_count": len(habits),
            "habits_due_today": [
                {"name": h.name, "streak": h.current_streak}
                for h in habits_due
            ],
            "streaks_at_risk": [
                {"name": h.name, "streak": h.current_streak, "best": h.best_streak}
                for h in streaks_at_risk
            ],

            # Goals
            "goals_count": len(goals),
            "goals": goals_summary,
            "goals_needing_attention": [
                g for g in goals_summary if g["needs_attention"]
            ],

            # Commitments
            "upcoming_commitments": [
                {"description": c.description, "to": c.to_whom, "deadline": c.deadline}
                for c in upcoming_commitments
            ],
            "overdue_commitments": [
                {"description": c.description, "to": c.to_whom, "deadline": c.deadline}
                for c in overdue_commitments
            ],

            # Ideas
            "unprocessed_ideas_count": unprocessed_ideas,

            # Focus
            "daily_focus": asdict(self.get_daily_focus()) if self.get_daily_focus() else None
        }


# ==============================================================================
# PLANNING SESSION (AI Interaction Manager)
# ==============================================================================

class PlanningSession:
    """
    Manages the daily planning conversation flow.
    Builds context for injection into ChatEngine preamble.
    """

    def __init__(self, planner: PlannerData, user_name: Optional[str] = None):
        self.planner = planner
        self.user_name = user_name or "sir"

    def get_interaction_mode(self) -> InteractionMode:
        """
        Determine current interaction mode based on context.
        Auto-initiates morning briefing on first contact.
        """
        now = datetime.now()
        hour = now.hour

        # First contact of day? Auto-initiate morning briefing
        if not self.planner.was_planning_done_today():
            return InteractionMode.MORNING_BRIEFING

        # Evening review time? (after 8pm)
        if hour >= 20 and not self.planner.was_review_done_today():
            return InteractionMode.EVENING_REVIEW

        # Check for urgent triggers (aggressive interruption)
        if self._has_urgent_triggers():
            return InteractionMode.CHECK_IN

        return InteractionMode.CONVERSATIONAL

    def _has_urgent_triggers(self) -> bool:
        """Check if there are urgent items requiring interruption."""
        now = datetime.now()
        hour = now.hour

        # Streak risk after 6pm
        if hour >= 18:
            if self.planner.get_streaks_at_risk():
                return True

        # Overdue commitments
        if self.planner.get_overdue_commitments():
            return True

        # Red project health
        for p in self.planner.get_projects(status="active"):
            if p.health == "red":
                return True

        return False

    def get_urgent_triggers(self) -> List[Dict[str, Any]]:
        """Get list of urgent triggers for check-in mode."""
        triggers = []
        now = datetime.now()
        hour = now.hour

        # Streaks at risk (after 6pm)
        if hour >= 18:
            for habit in self.planner.get_streaks_at_risk():
                triggers.append({
                    "type": "streak_risk",
                    "message": f"Your {habit.name} streak ({habit.current_streak} days) is at risk",
                    "habit_name": habit.name,
                    "streak": habit.current_streak
                })

        # Overdue commitments
        for c in self.planner.get_overdue_commitments():
            triggers.append({
                "type": "overdue_commitment",
                "message": f"Commitment to {c.to_whom} is overdue: {c.description}",
                "commitment": c.description,
                "to_whom": c.to_whom,
                "deadline": c.deadline
            })

        # Red projects
        for p in self.planner.get_projects(status="active"):
            if p.health == "red":
                triggers.append({
                    "type": "project_health",
                    "message": f"Project '{p.name}' is at red health: {p.health_reason}",
                    "project": p.name,
                    "reason": p.health_reason
                })

        return triggers

    def get_planning_context(self) -> str:
        """
        Build planning context string for AI injection.
        This is injected into the persona preamble.
        """
        mode = self.get_interaction_mode()
        summary = self.planner.get_planning_summary()

        if mode == InteractionMode.MORNING_BRIEFING:
            return self._build_morning_context(summary)
        elif mode == InteractionMode.CHECK_IN:
            return self._build_checkin_context(summary)
        elif mode == InteractionMode.EVENING_REVIEW:
            return self._build_evening_context(summary)
        else:
            return self._build_conversational_context(summary)

    def _build_morning_context(self, summary: Dict[str, Any]) -> str:
        """Build morning briefing context."""
        # Check if this is a new user with no planning data
        is_empty = (
            summary["active_projects_count"] == 0 and
            summary["habits_count"] == 0 and
            summary["pending_tasks_count"] == 0
        )

        if is_empty:
            return self._build_onboarding_context(summary)

        return self._build_returning_user_morning_context(summary)

    def _build_onboarding_context(self, summary: Dict[str, Any]) -> str:
        """Build onboarding context for new users with no planning data."""
        lines = [
            "<planning_mode type=\"onboarding\">",
            f"Today is {self._format_date(summary['date'])}.",
            "",
            "**IMPORTANT: This is a NEW USER with NO planning data yet.**",
            "You must ACTIVELY DRIVE the conversation to establish their planning system.",
            "",
            "---",
            "**Your role:** You are conducting an onboarding planning session.",
            "",
            "STEP 1 - INTRODUCE THE SYSTEM (briefly):",
            "- Explain you'll help them track goals, habits, projects, and daily tasks",
            "- This is a daily check-in system inspired by GTD and Atomic Habits",
            "- Keep it conversational, not overwhelming",
            "",
            "STEP 2 - ASK ABOUT THEIR GOALS:",
            "- \"What's the most important thing you're working toward right now?\"",
            "- Listen for: career goals, health goals, learning goals, creative projects",
            "- Add these as Projects using the add_project tool",
            "",
            "STEP 3 - ESTABLISH ATOMIC HABITS:",
            "- \"What small daily habits would move you toward those goals?\"",
            "- Suggest: exercise, reading, meditation, writing, learning, etc.",
            "- Keep habits SMALL and DAILY (5-15 min) - atomic habits compound",
            "- Add using add_habit tool with appropriate preferred_time",
            "",
            "STEP 4 - CAPTURE IMMEDIATE TASKS:",
            "- \"What's on your plate today or this week?\"",
            "- Add urgent items using add_task tool",
            "- Ask about any commitments/promises made to others",
            "",
            "STEP 5 - SET TODAY'S FOCUS:",
            "- Help them pick 1-3 priorities for today",
            "- Use set_day_priorities tool",
            "- Mark planning done with mark_planning_done tool",
            "",
            "**CONVERSATION STYLE:**",
            "- Be warm and encouraging, not robotic",
            "- Ask ONE question at a time, wait for response",
            "- Use tools to add items AS the user mentions them",
            "- Summarize what you've captured periodically",
            f"- Address user as '{self.user_name}'",
            "",
            "START by greeting warmly and explaining you'd like to help them set up",
            "their planning system. Then ask about their most important goal.",
            "</planning_mode>"
        ]
        return "\n".join(lines)

    def _build_returning_user_morning_context(self, summary: Dict[str, Any]) -> str:
        """Build morning context for users with existing planning data."""
        lines = [
            "<planning_mode type=\"morning_briefing\">",
            f"Today is {self._format_date(summary['date'])}.",
            "This is the user's first interaction today. Daily planning not yet done.",
            ""
        ]

        # Projects needing attention
        if summary["projects_needing_attention"]:
            lines.append("**Projects needing attention:**")
            for p in summary["projects_needing_attention"]:
                lines.append(f"- {p['name']} ({p['health']}): {p['reason']}")
            lines.append("")

        # Overdue items
        if summary["overdue_commitments"]:
            lines.append("**OVERDUE commitments:**")
            for c in summary["overdue_commitments"]:
                lines.append(f"- To {c['to']}: {c['description']} (was due {c['deadline']})")
            lines.append("")

        if summary["overdue_tasks"]:
            lines.append("**Overdue tasks:**")
            for t in summary["overdue_tasks"][:3]:
                lines.append(f"- {t['title']} (due {t['due']})")
            lines.append("")

        # Upcoming commitments
        if summary["upcoming_commitments"]:
            lines.append("**Commitments this week:**")
            for c in summary["upcoming_commitments"][:3]:
                lines.append(f"- {c['description']} to {c['to']} (due {c['deadline']})")
            lines.append("")

        # Habits status
        if summary["habits_due_today"]:
            lines.append("**Habits due today:**")
            for h in summary["habits_due_today"]:
                streak_note = f" (streak: {h['streak']})" if h['streak'] > 0 else ""
                lines.append(f"- {h['name']}{streak_note}")
            lines.append("")

        # Streaks at risk
        if summary["streaks_at_risk"]:
            lines.append("**Streaks at risk if not done today:**")
            for h in summary["streaks_at_risk"]:
                lines.append(f"- {h['name']}: {h['streak']} day streak (best: {h['best']})")
            lines.append("")

        # Task summary
        lines.append(f"Pending tasks: {summary['pending_tasks_count']}")
        if summary["tasks_by_context"]:
            ctx_str = ", ".join(f"{k}: {v}" for k, v in summary["tasks_by_context"].items())
            lines.append(f"By context: {ctx_str}")
        lines.append("")

        # Instructions for AI
        lines.extend([
            "---",
            "**Your role:** You are initiating the daily planning session.",
            "- Greet warmly, lead with the MOST CRITICAL item first (not a list dump)",
            "- Propose a concrete plan for the day, don't ask 'what do you want to do?'",
            "- Ask about energy level to adjust recommendations",
            "- Protect streaks and deadlines",
            f"- Address user as '{self.user_name}'",
            "",
            "After planning is confirmed, call the 'mark_planning_done' tool.",
            "</planning_mode>"
        ])

        return "\n".join(lines)

    def _build_checkin_context(self, summary: Dict[str, Any]) -> str:
        """Build mid-day check-in context (aggressive interruption)."""
        triggers = self.get_urgent_triggers()

        lines = [
            "<planning_mode type=\"check_in\">",
            "**URGENT CHECK-IN REQUIRED**",
            "",
            "You are interrupting because something needs immediate attention:",
            ""
        ]

        for trigger in triggers:
            lines.append(f"- [{trigger['type'].upper()}] {trigger['message']}")

        lines.extend([
            "",
            "---",
            "**Your role:** Be direct about why you're interrupting.",
            "- Propose a solution, don't just surface the problem",
            "- Be caring but insistent - you're protecting the user from themselves",
            "- For streaks: suggest minimal viable action ('even 5 minutes counts')",
            "- For deadlines: propose immediate action or explicit rescheduling",
            "</planning_mode>"
        ])

        return "\n".join(lines)

    def _build_evening_context(self, summary: Dict[str, Any]) -> str:
        """Build evening review context."""
        lines = [
            "<planning_mode type=\"evening_review\">",
            f"Today is {self._format_date(summary['date'])}. Evening review time.",
            ""
        ]

        # Habit status
        habits = self.planner.get_habits()
        today = date.today().isoformat()

        completed_habits = [h for h in habits if h.last_completed == today]
        missed_habits = [h for h in habits if h.last_completed != today]

        if completed_habits:
            lines.append("**Habits completed today:**")
            for h in completed_habits:
                lines.append(f"- {h.name} (streak: {h.current_streak})")
            lines.append("")

        if missed_habits:
            lines.append("**Habits NOT completed (streaks at risk!):**")
            for h in missed_habits:
                if h.current_streak > 0:
                    lines.append(f"- {h.name} (will lose {h.current_streak} day streak!)")
                else:
                    lines.append(f"- {h.name}")
            lines.append("")

        # Task summary for the day
        # Note: would need completion timestamp to filter by today for true "completed_today"
        lines.extend([
            f"Tasks pending: {summary['pending_tasks_count']}",
            f"Overdue tasks: {summary['overdue_tasks_count']}",
            "",
            "---",
            "**Your role:** Conduct evening review.",
            "- Summarize accomplishments (be specific, not generic praise)",
            "- Acknowledge deferrals without judgment",
            "- Confirm streak status - last chance to save them!",
            "- Briefly seed tomorrow (don't plan it)",
            "",
            "After review, call the 'mark_review_done' tool.",
            "</planning_mode>"
        ])

        return "\n".join(lines)

    def _build_conversational_context(self, summary: Dict[str, Any]) -> str:
        """Build minimal context for normal conversation."""
        lines = [
            "<planning_context>",
            f"Date: {self._format_date(summary['date'])}",
            f"Daily planning: {'done' if summary['planning_done'] else 'not done'}",
        ]

        # Brief status
        if summary["streaks_at_risk"]:
            at_risk = [h["name"] for h in summary["streaks_at_risk"]]
            lines.append(f"Streaks at risk: {', '.join(at_risk)}")

        if summary["overdue_commitments"]:
            lines.append(f"Overdue commitments: {len(summary['overdue_commitments'])}")

        lines.append("")
        lines.append("Planning tools available: add_task, complete_task, log_habit, capture_idea, etc.")
        lines.append("</planning_context>")

        return "\n".join(lines)

    def _format_date(self, date_str: str) -> str:
        """Format date string nicely."""
        d = date.fromisoformat(date_str)
        return d.strftime("%A, %B %d, %Y")
