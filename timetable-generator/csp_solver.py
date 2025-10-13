from typing import Dict, List, Optional, Tuple, FrozenSet, Iterator
from schemas import (
    TimetableData, Solution, 
    SessionType, Course, Section,
    Instructor, Room, TimeSlot, 
    InstructorRole, ScheduledClass)
from constraints import (
    Variable,
    Domain,
    Assignment,
    is_consistent,
    VAR_COURSE,
    VAR_SECTIONS,
    DOM_TIMESLOT,
    DOM_ROOM,
    DOM_INSTRUCTOR
)
from data_loader import load_timetable_data_from_excel
from copy import deepcopy
from itertools import combinations
from pathlib import Path

STANDARD_SECTION_MAX_SIZE = 15

class CSPSolver:
    """
    The main engine for solving the timetable Constraint Satisfaction Problem.

    This class takes the complete, validated timetable data, formulates the
    problem by defining variables and their domains, and then uses a backtracking
    search algorithm to find a valid solution that satisfies all hard constraints.
    """

    def __init__(self, timetable_data: TimetableData):
        """
        Initializes the solver with all necessary data and prepares
        internal data structures for efficient lookups.
        """
        self.data = timetable_data
        self.course_map : Dict[Tuple[str, SessionType], Course] = {}   # (course_id, session_type) -> Course
        self.curriculum_map: Dict[int, List[str]] = {}                 # year -> List[course_ids]
        self.sections_map: Dict[int, List[Section]] = {}               # year -> List[Section]
        self.instructors_map: Dict[str, List[Instructor]] = {}         # course_id -> List[Instructor]
        self.rooms_map: Dict[SessionType, List[Room]] = {}

        self.unscheduled_sections_map: Dict[Course, FrozenSet[Section]] = {}

        self._initialize_internal_lookups()

    def solve(self) -> Optional[Solution]:
        """
        The main public entry point to start the solving process.
        """
        try:
            assignment = self._backtrack({}, self.unscheduled_sections_map)
            if not assignment: return None
            solution = self._format_solution(assignment)
            return solution
        except Exception as e:
            raise ValueError(f"Fatal Error: failed run the solver: Reason: {e}")
        
    def _initialize_internal_lookups(self):
        """
        Initializes the fast internal lookup maps from the raw TimetableData.
        """
        for course in self.data.courses:
            self.course_map[(course.course_id, course.type)] = course
        
        for curr in self.data.curriculum:
            year = curr.year
            course_id = curr.course_id
            self.curriculum_map.setdefault(year, []).append(course_id)

        for section in self.data.sections:
            year = section.year
            self.sections_map.setdefault(year, []).append(section)

        for instructor in self.data.instructors:
            for qualification in instructor.qualifications:
                self.instructors_map.setdefault(qualification, []).append(instructor)

        for room in self.data.rooms:
            for type in room.types:
                self.rooms_map.setdefault(type, []).append(room)

        for year, course_ids in self.curriculum_map.items():
            sections_for_year = self.sections_map.get(year, [])
            if not sections_for_year:
                continue
            sections_to_schedule = frozenset(sections_for_year)

            for course_id in course_ids:
                for session_type in SessionType:
                    course_key = (course_id, session_type)
                    course_obj = self.course_map.get(course_key)
                    if course_obj:
                        self.unscheduled_sections_map[course_obj] = sections_to_schedule

    def _generate_valid_domains(self, course: Course) -> List[Domain]:
        """ 
        Generates all possible valid domains for a given Course
        """
        if course.type == SessionType.PROJECT:
            return [(ts, None, None) for ts in self.data.timeslots]
        
        timeslots: List[TimeSlot] = self.data.timeslots
        rooms: List[Room] = [room for room in self.rooms_map.get(course.type, [])if course.type in room.types]
        instructors: List[Instructor] = []

        if course.type == SessionType.LECTURE:
            instructors = [inst for inst in self.instructors_map.get(course.course_id, []) if inst.role in [InstructorRole.DOCTOR, InstructorRole.PROFESSOR]]
        elif course.type in [SessionType.LAB, SessionType.TUTORIAL]:
            instructors = [inst for inst in self.instructors_map.get(course.course_id, []) if inst.role == InstructorRole.TEACHING_ASSISTANT]

        valid_domains = []

        for ts in timeslots:
            for room in rooms:
                for instructor in instructors:
                    valid_domains.append((ts, room, instructor))

        return valid_domains

    def _select_next_course_to_schedule(self, unscheduled_sections_map: Dict[Course, FrozenSet[Section]]) -> Tuple[Course, List[Domain]]:
        """
        Selects the next course to schedule using the Minimum Remaining Values (MRV) heuristic.

        This method finds the course that is most constrained (has the fewest possible
        valid assignments) and prioritizes it to fail fast and prune the search tree.
        """
        best_candidate = None
        min_domain_size = float('inf') 

        for course, sections in unscheduled_sections_map.items():
            if not sections:
                continue
            domains = self._generate_valid_domains(course)

            if not domains:
                return (course, [])

            if len(domains) < min_domain_size:
                min_domain_size = len(domains)
                best_candidate = (course, domains)

        return best_candidate

    def _form_valid_groups(
        self,
        unscheduled_sections: FrozenSet[Section],
        room: Room
    ) -> Iterator[FrozenSet[Section]]:
        """
        A generator that yields all valid, non-overlapping subgroups of sections
        that can be scheduled, constrained by room capacity and parent group rules.

        It prioritizes larger groups first to find more efficient solutions faster.
        """
        if room is None:
            if unscheduled_sections:
                yield unscheduled_sections
            return

        sections_by_group: Dict[int, List[Section]] = {}
        for section in unscheduled_sections:
            sections_by_group.setdefault(section.group_number, []).append(section)

        for _, sections_in_group in sections_by_group.items():
            if not sections_in_group:
                continue

            max_size = room.capacity // STANDARD_SECTION_MAX_SIZE

            effective_max_size = min(max_size, len(sections_in_group))

            for size in range(effective_max_size, 0, -1):
                for combo in combinations(sections_in_group, size):
                    yield frozenset(combo)

    def _backtrack(self, assignment: Assignment, unscheduled_sections_map: Dict[Course, FrozenSet[Section]], depth = 0) -> Optional[Assignment]:
        """
        The core recursive backtracking algorithm to find a valid assignment.
        """
        remaining_unscheduled_sections = sum(len(s) for s in unscheduled_sections_map.values())
        print(f"{remaining_unscheduled_sections} unscheduled section-classes remaining")
        if all(not sections for sections in unscheduled_sections_map.values()):
                return assignment

        course, domains = self._select_next_course_to_schedule(unscheduled_sections_map)

        if not domains: return None

        sections_to_schedule = unscheduled_sections_map[course]
            
        for domain in domains:
            if remaining_unscheduled_sections == 46:
                print(f"--- Probing Depth  {remaining_unscheduled_sections} for course {course.course_id} ({course.type}) ---")
                print(f"    Trying Domain: {domain[DOM_TIMESLOT].timeslot_id}, Room: {domain[DOM_ROOM].room_id if domain[DOM_ROOM] else 'None'}, Room: {domain[DOM_INSTRUCTOR].name if domain[DOM_INSTRUCTOR] else 'None'}")
            for section_group in self._form_valid_groups(sections_to_schedule, domain[DOM_ROOM]):

                variable: Variable = (course, section_group)

                consistent, reason = is_consistent(variable, domain, assignment)
                if consistent:
                    new_assignment = deepcopy(assignment)
                    new_assignment[variable] = domain 

                    new_unscheduled_sections_map = deepcopy(unscheduled_sections_map)
                    new_unscheduled_sections_map[course] = new_unscheduled_sections_map[course] - section_group

                    result = self._backtrack(new_assignment, new_unscheduled_sections_map, depth + 1)
                    if result: return result
        return None

    def _format_solution(self, assignment: Assignment) -> Solution:
        """
        Converts the internal assignment dictionary into the final, user-friendly
        Solution Pydantic model.
        """
        schedule = []
        for variable, domain in assignment.items():
            scheduled_class = ScheduledClass(
                course=variable[VAR_COURSE],
                timeslot=domain[DOM_TIMESLOT],
                room=domain[DOM_ROOM],
                instructor=domain[DOM_INSTRUCTOR],
                sections=variable[VAR_SECTIONS]
            )
            schedule.append(scheduled_class)

        solution = Solution(schedule=schedule)
        return solution

if __name__ == '__main__':
       timetable_data = load_timetable_data_from_excel('./Tables.xlsx')
       solver = CSPSolver(timetable_data)
       solution = solver.solve()
       if solution:
           print("Solution Found!")
           Path('./timetable_json.json').write_text(solution.model_dump_json(indent=2))
       else:
           print("No solution could be found that satisfies all hard constraints.")
