from typing import Dict, Tuple, FrozenSet, Optional
from schemas import *
from statistics import stdev

# --- Type Aliases ---

Variable = Tuple[Course, FrozenSet[Section]]
Domain = Tuple[TimeSlot, Optional[Room], Optional[Instructor]]

# An Assignment is the current state of the solution being built.
Assignment = Dict[Variable, Domain]

# --- Clear Index Constants for Tuple Access ---

VAR_COURSE = 0
VAR_SECTIONS = 1

DOM_TIMESLOT = 0
DOM_ROOM = 1
DOM_INSTRUCTOR = 2

SLOT_ORDER = {
    time(9, 0): 0,
    time(10, 45): 1,
    time(12, 30): 2,
    time(14, 15): 3 
}

# --- Penalties for Soft Constraints Scoring ---

_GAP_PENALTY = 5.0
_UNDESIRABLE_SLOT_PENALTY = 3.0

# --- Hard Constraint Checking ---

def is_consistent(
    variable: Variable,
    domain: Domain,
    assignment: Assignment
) -> Tuple[bool, Optional[str]]:
    """
    The main orchestrator for hard constraint checks.

    This function is called by the solver for each potential assignment to see if it
    conflicts with any of the already placed classes in the current 'assignment'.
    True if the proposed assignment is consistent (no conflicts), False otherwise.
    """
    if _check_project_day_conflict(variable, domain, assignment):
        return (False, "Project Conflict")

    for existing_variable, existing_domain in assignment.items():
        if _check_instructor_conflict(domain, existing_domain):
            return (False, "Instructor Conflict")
        if _check_room_conflict(domain, existing_domain):
            return (False, "Room Conflict")
        if _check_section_conflict(variable, domain, existing_variable, existing_domain):
            return (False, "Section Conflict")
        
    return (True, None)

def _check_instructor_conflict(proposed_domain: Domain, existing_domain: Domain) -> bool:
    """
    Checks the "Instructor Uniqueness" constraint.
    Returns True if there IS a conflict, False otherwise.
    """
    proposed_instructor = proposed_domain[DOM_INSTRUCTOR]
    existing_instructor = existing_domain[DOM_INSTRUCTOR]

    if proposed_instructor is None or existing_instructor is None:
        return False

    is_same_instructor = proposed_instructor.instructor_id == existing_instructor.instructor_id
    is_same_time = proposed_domain[DOM_TIMESLOT].timeslot_id == existing_domain[DOM_TIMESLOT].timeslot_id

    return is_same_instructor and is_same_time

def _check_room_conflict(proposed_domain: Domain, existing_domain: Domain) -> bool:
    """
    Checks the "Room Uniqueness" constraint.
    Returns True if there IS a conflict, False otherwise.
    """
    proposed_room = proposed_domain[DOM_ROOM]
    existing_room = existing_domain[DOM_ROOM]

    if proposed_room is None or existing_room is None:
        return False

    is_same_room = proposed_room.room_id == existing_room.room_id
    is_same_time = proposed_domain[DOM_TIMESLOT].timeslot_id == existing_domain[DOM_TIMESLOT].timeslot_id

    return is_same_room and is_same_time

def _check_section_conflict(
    proposed_variable: Variable,
    proposed_domain: Domain,
    existing_variable: Variable,
    existing_domain: Domain
) -> bool:
    """
    Checks the "Section Uniqueness" constraint (a section can't be in two places at once).
    Returns True if there IS a conflict, False otherwise.
    """
    shared_sections = proposed_variable[VAR_SECTIONS].intersection(existing_variable[VAR_SECTIONS])

    if not shared_sections:
        return False 

    is_same_time = proposed_domain[DOM_TIMESLOT].timeslot_id == existing_domain[DOM_TIMESLOT].timeslot_id
    
    return is_same_time

def _check_project_day_conflict(
    proposed_variable: Variable,
    proposed_domain: Domain,
    assignment: Assignment
) -> bool:
    """
    Checks the global "Project Day" constraint.
    Returns True if there IS a conflict, False otherwise.
    """
    proposed_course = proposed_variable[VAR_COURSE]
    proposed_year = next(iter(proposed_variable[VAR_SECTIONS])).year
    proposed_day = proposed_domain[DOM_TIMESLOT].day

    proposed_is_project = proposed_course.type == SessionType.PROJECT

    for existing_variable, existing_domain in assignment.items():
        existing_course = existing_variable[VAR_COURSE]
        existing_year = next(iter(existing_variable[VAR_SECTIONS])).year
        existing_day = existing_domain[DOM_TIMESLOT].day

        if proposed_year == existing_year and proposed_day == existing_day:
            existing_is_project = existing_course.type == SessionType.PROJECT

            if proposed_is_project or existing_is_project:
                return True

    return False

# --- Soft Constraint Scoring ---

def calculate_solution_score(schedule: List[ScheduledClass]) -> float:
    """
    The main orchestrator for scoring a complete, valid solution.
    """
    score = 0.0

    section_timeslot_map: Dict[Tuple[int, int], List[TimeSlot]] = {}
    for cls in schedule:
        for section in cls.sections:
            section_key = (section.year, section.section_id)
            section_timeslot_map.setdefault(section_key, []).append(cls.timeslot)

    score += _calculate_student_gap_penalty(section_timeslot_map)
    score += _calculate_undesirable_slot_penalty(schedule)
    score += _calculate_distribution_penalty(section_timeslot_map)

    return score

def _calculate_student_gap_penalty(section_timeslot_map: Dict[Tuple[int, int], List[TimeSlot]]) -> float:
    """
    Calculates the total penalty for all gaps in student schedules.
    """
    score = 0.0
    for _, timeslots in section_timeslot_map.items():
        day_grouping: Dict[DayOfWeek, List[TimeSlot]] = {}
        for ts in timeslots:
            day_grouping.setdefault(ts.day, []).append(ts)

        for _, daily_timeslots in day_grouping.items():
            if len(daily_timeslots) < 2: continue
            daily_timeslots.sort(key=lambda ts: ts.start_time)
            slot_indices = [SLOT_ORDER[ts.start_time] for ts in daily_timeslots]

            for i in range(len(slot_indices) - 1):
                gap_size = (slot_indices[i+1] - slot_indices[i]) - 1
                if gap_size > 0:
                    score += _GAP_PENALTY * gap_size
    return score

def _calculate_undesirable_slot_penalty(schedule: List[ScheduledClass]) -> float:
    """
    Calculates the penalty for scheduling classes in the first or last slot of the day.
    """
    first_last_slots_count = sum([1 for cls in schedule if SLOT_ORDER.get(cls.timeslot.start_time) in [0, 3]])
    return first_last_slots_count * _UNDESIRABLE_SLOT_PENALTY

def _calculate_distribution_penalty(section_timeslot_map: Dict[Tuple[int, int], List[TimeSlot]]) -> float:
    """
    Calculates the penalty for uneven distribution of classes across the week.
    """
    score = 0.0
    for _, timeslots in section_timeslot_map.items():
        daily_counts = {day: 0 for day in DayOfWeek}
        for ts in timeslots:
            daily_counts[ts.day] += 1
        
        class_counts_per_day = list(daily_counts.values())
        if len(class_counts_per_day) < 2: continue

        unbalance_penalty = stdev(class_counts_per_day)
        score += unbalance_penalty
    return score
