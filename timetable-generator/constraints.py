from typing import Dict, List, Optional, Tuple, FrozenSet
from schemas import (
    Course, Section, TimeSlot, Room, Instructor, SessionType,
    ScheduledClass, DayOfWeek, Major
)
from statistics import stdev
from datetime import time

# --- Type Aliases ---
Variable = Tuple[Course, FrozenSet[Section]]
Domain = Tuple[TimeSlot, Optional[Room], Optional[Instructor]]
Assignment = Dict[Variable, Domain]

# --- Index Constants for Tuple Access ---
VAR_COURSE = 0
VAR_SECTIONS = 1
DOM_TIMESLOT = 0
DOM_ROOM = 1
DOM_INSTRUCTOR = 2

# --- Constants for Soft Constraint Scoring ---
GAP_PENALTY = 10.0
UNDESIRABLE_SLOT_PENALTY = 3.0
SLOT_ORDER = {
    time(9, 0): 0,
    time(10, 45): 1,
    time(12, 30): 2,
    time(14, 15): 3
}

# --- Hard Constraint Checking ---

def is_consistent(variable: Variable, domain: Domain, assignment: Assignment) -> Tuple[bool, Optional[str]]:
    """
    The main orchestrator for hard constraint checks.
    Returns (True, None) if consistent, (False, "Reason") otherwise.
    """
    if _check_project_day_conflict(variable, domain, assignment):
        return (False, "Project Day Conflict")
    for existing_variable, existing_domain in assignment.items():
        if _check_instructor_conflict(domain, existing_domain):
            return (False, "Instructor Conflict")
        if _check_room_conflict(domain, existing_domain):
            return (False, "Room Conflict")
        if _check_section_conflict(variable, domain, existing_variable, existing_domain):
            return (False, "Section Conflict")
    return (True, None)

def _check_instructor_conflict(proposed_domain: Domain, existing_domain: Domain) -> bool:
    proposed_instructor = proposed_domain[DOM_INSTRUCTOR]
    existing_instructor = existing_domain[DOM_INSTRUCTOR]
    if proposed_instructor is None or existing_instructor is None: return False
    return (proposed_instructor.instructor_id == existing_instructor.instructor_id and
            proposed_domain[DOM_TIMESLOT].timeslot_id == existing_domain[DOM_TIMESLOT].timeslot_id)

def _check_room_conflict(proposed_domain: Domain, existing_domain: Domain) -> bool:
    proposed_room = proposed_domain[DOM_ROOM]
    existing_room = existing_domain[DOM_ROOM]
    if proposed_room is None or existing_room is None: return False
    return (proposed_room.room_id == existing_room.room_id and
            proposed_domain[DOM_TIMESLOT].timeslot_id == existing_domain[DOM_TIMESLOT].timeslot_id)

def _check_section_conflict(proposed_variable: Variable, proposed_domain: Domain, existing_variable: Variable, existing_domain: Domain) -> bool:
    shared_sections = proposed_variable[VAR_SECTIONS].intersection(existing_variable[VAR_SECTIONS])
    if not shared_sections: return False
    return proposed_domain[DOM_TIMESLOT].timeslot_id == existing_domain[DOM_TIMESLOT].timeslot_id

# --- CORRECTED MAJOR-AWARE PROJECT CONFLICT LOGIC ---
def _check_project_day_conflict(
    proposed_variable: Variable,
    proposed_domain: Domain,
    assignment: Assignment
) -> bool:
    """
    Checks the major-aware "Project Day" constraint.
    A conflict occurs if a project is on the same day as another class for the same year,
    AND they share a major (or one is 'general').
    """
    proposed_course = proposed_variable[VAR_COURSE]
    proposed_is_project = proposed_course.type == SessionType.PROJECT
    
    # Invert the check if the proposed class is not a project
    if not proposed_is_project:
        for existing_variable, existing_domain in assignment.items():
            if existing_variable[VAR_COURSE].type == SessionType.PROJECT:
                if _check_project_day_conflict(existing_variable, existing_domain, {proposed_variable: proposed_domain}):
                    return True # Conflict found
        return False

    # Main logic: The proposed class IS a project.
    proposed_year = next(iter(proposed_variable[VAR_SECTIONS])).year
    proposed_day = proposed_domain[DOM_TIMESLOT].day
    proposed_majors = {s.major for s in proposed_variable[VAR_SECTIONS]}
    is_proposed_general = Major.GENERAL in proposed_majors

    for existing_variable, existing_domain in assignment.items():
        existing_year = next(iter(existing_variable[VAR_SECTIONS])).year
        existing_day = existing_domain[DOM_TIMESLOT].day

        if proposed_year == existing_year and proposed_day == existing_day:
            existing_majors = {s.major for s in existing_variable[VAR_SECTIONS]}
            is_existing_general = Major.GENERAL in existing_majors
            
            # Conflict if either is general, as it applies to all majors in the year.
            if is_proposed_general or is_existing_general:
                return True

            # Conflict if they have any specific major in common.
            if not proposed_majors.isdisjoint(existing_majors):
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
    score = 0.0
    for _, timeslots in section_timeslot_map.items():
        day_grouping: Dict[DayOfWeek, List[TimeSlot]] = {}
        for ts in timeslots: day_grouping.setdefault(ts.day, []).append(ts)
        for _, daily_timeslots in day_grouping.items():
            if len(daily_timeslots) < 2: continue
            daily_timeslots.sort(key=lambda ts: ts.start_time)
            slot_indices = [SLOT_ORDER.get(ts.start_time) for ts in daily_timeslots if SLOT_ORDER.get(ts.start_time) is not None]
            for i in range(len(slot_indices) - 1):
                gap_size = (slot_indices[i+1] - slot_indices[i]) - 1
                if gap_size > 0: score += GAP_PENALTY * gap_size
    return score

def _calculate_undesirable_slot_penalty(schedule: List[ScheduledClass]) -> float:
    first_last_slots_count = sum([1 for cls in schedule if SLOT_ORDER.get(cls.timeslot.start_time) in [0, 3]])
    return first_last_slots_count * UNDESIRABLE_SLOT_PENALTY

def _calculate_distribution_penalty(section_timeslot_map: Dict[Tuple[int, int], List[TimeSlot]]) -> float:
    total_score = 0.0
    for _, timeslots in section_timeslot_map.items():
        daily_counts = {day: 0 for day in DayOfWeek}
        for ts in timeslots: daily_counts[ts.day] += 1
        class_counts_per_day = list(daily_counts.values())
        if len(class_counts_per_day) < 2: continue
        total_score += stdev(class_counts_per_day)
    return total_score

