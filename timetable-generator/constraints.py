from typing import Dict, Tuple, FrozenSet, Optional
from schemas import (Course, Section, TimeSlot, Room, Instructor, SessionType, Solution)

# --- Type Aliases for Clarity in the Solver ---
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

# --- Hard Constraint Checking ---

def is_consistent(
    variable: Variable,
    domain: Domain,
    assignment: Assignment
) -> bool:
    """
    The main orchestrator for hard constraint checks.

    This function is called by the solver for each potential assignment to see if it
    conflicts with any of the already placed classes in the current 'assignment'.

    Args:
        variable: The variable (Course + Sections) being assigned.
        domain: The domain value (TimeSlot, Room, Instructor) being assigned to it.
        assignment: The current partial assignment of other variables.

    Returns:
        True if the proposed assignment is consistent (no conflicts), False otherwise.
    """
    if _check_project_day_conflict(variable, domain, assignment):
        return False

    for existing_variable, existing_domain in assignment.items():
        if _check_instructor_conflict(domain, existing_domain):
            return False
        if _check_room_conflict(domain, existing_domain):
            return False
        if _check_section_conflict(variable, domain, existing_variable, existing_domain):
            return False
            
    return True

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

def calculate_solution_score(solution: Solution) -> float:
    """
    The main orchestrator for scoring a complete, valid solution.

    It calls all the individual penalty functions and sums their results.
    The lower the score, the better the timetable.

    Args:
        solution: A complete Solution object containing the final schedule.

    Returns:
        A float representing the total penalty score.
    """
    pass


def _calculate_student_gap_penalty(solution: Solution) -> float:
    """
    Calculates the total penalty for all gaps in student schedules.
    A gap is an empty time slot between two classes for the same section on the same day.
    """
    pass


def _calculate_undesirable_slot_penalty(solution: Solution) -> float:
    """
    Calculates the penalty for scheduling classes in undesirable time slots
    (e.g., the first or last slot of the day).
    """
    pass


def _calculate_distribution_penalty(solution: Solution) -> float:
    """
    Calculates the penalty for uneven distribution of classes across the week for sections.
    Uses the standard deviation of classes per day for each section.
    """
    pass
