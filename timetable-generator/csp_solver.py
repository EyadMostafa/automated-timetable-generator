import time
from typing import Dict, List, Optional, Tuple, FrozenSet, Iterator
from schemas import (
    TimetableData, Solution,
    SessionType, Course, Section,
    Instructor, Room, TimeSlot,
    InstructorRole, ScheduledClass, SolverMode
)
from constraints import (
    Variable,
    Domain,
    Assignment,
    is_consistent,
    calculate_solution_score,
    DOM_ROOM
)
from data_loader import load_timetable_data_from_excel
from copy import deepcopy
from itertools import combinations
from pathlib import Path

STANDARD_SECTION_PLANNING_SIZE = 15

class CSPSolver:
    """
    The main engine for solving the timetable Constraint Satisfaction Problem.
    """

    def __init__(self, timetable_data: TimetableData, mode: SolverMode):
        """
        Initializes the solver with all necessary data and prepares
        internal data structures for efficient lookups.
        """
        self.data = timetable_data
        self.mode = mode

        self.course_map: Dict[Tuple[str, SessionType], Course] = {}
        self.curriculum_map: Dict[int, List[str]] = {}
        self.sections_map: Dict[int, List[Section]] = {}
        self.instructors_map: Dict[str, List[Instructor]] = {}
        self.rooms_map: Dict[SessionType, List[Room]] = {}
        self.unscheduled_sections_map: Dict[Course, FrozenSet[Section]] = {}

        self.best_assignment: Optional[Assignment] = None
        self.best_score: float = float('inf')
        self.search_terminated: bool = False
        
        self._initialize_internal_lookups()

    def solve(self, timeout_seconds: int = 300) -> Optional[Solution]:
        """
        The main public entry point to start the solving process.
        """
        try:
            print(f"Starting solver in '{self.mode.value}' mode...")
            if self.mode == SolverMode.OPTIMIZE:
                print(f"Searching for the best solution within {timeout_seconds} seconds.")
            
            start_time = time.time()
            initial_assignment: Assignment = {}
            
            final_assignment = self._backtrack(initial_assignment, self.unscheduled_sections_map, start_time, timeout_seconds)
            
            if self.mode == SolverMode.OPTIMIZE:
                final_assignment = self.best_assignment

            if not final_assignment:
                return None
            
            solution = self._format_solution(final_assignment)
            if self.mode == SolverMode.OPTIMIZE:
                solution.score = self.best_score
            else:
                solution.score = calculate_solution_score(solution.schedule)
            
            return solution
        except Exception as e:
            raise ValueError(f"Fatal Error: failed to run the solver. Reason: {e}")

    def _initialize_internal_lookups(self):
        """
        Initializes the fast internal lookup maps from the raw TimetableData.
        """
        for course in self.data.courses:
            self.course_map[(course.course_id, course.type)] = course
        
        for curr in self.data.curriculum:
            self.curriculum_map.setdefault(curr.year, []).append(curr.course_id)

        for section in self.data.sections:
            self.sections_map.setdefault(section.year, []).append(section)

        for instructor in self.data.instructors:
            for qualification in instructor.qualifications:
                self.instructors_map.setdefault(qualification, []).append(instructor)

        for room in self.data.rooms:
            for room_type in room.types:
                self.rooms_map.setdefault(room_type, []).append(room)

        for year, course_ids in self.curriculum_map.items():
            sections_for_year = self.sections_map.get(year, [])
            if not sections_for_year: continue
            sections_to_schedule = frozenset(sections_for_year)
            for course_id in course_ids:
                for session_type in SessionType:
                    course_key = (course_id, session_type)
                    course_obj = self.course_map.get(course_key)
                    if course_obj:
                        self.unscheduled_sections_map[course_obj] = sections_to_schedule

    def _generate_valid_domains(self, course: Course) -> List[Domain]:
        """ 
        Generates all possible valid domain tuples for a given Course.
        """
        if course.type == SessionType.PROJECT:
            return [(ts, None, None) for ts in self.data.timeslots]
        
        valid_rooms = self.rooms_map.get(course.type, [])
        qualified_instructors = self.instructors_map.get(course.course_id, [])
        valid_instructors: List[Instructor] = []
        if course.type == SessionType.LECTURE:
            valid_instructors = [inst for inst in qualified_instructors if inst.role in [InstructorRole.DOCTOR, InstructorRole.PROFESSOR]]
        elif course.type in [SessionType.LAB, SessionType.TUTORIAL]:
            valid_instructors = [inst for inst in qualified_instructors if inst.role == InstructorRole.TEACHING_ASSISTANT]
        
        if not valid_rooms or not valid_instructors:
            return []

        return [(ts, room, instructor) for ts in self.data.timeslots for room in valid_rooms for instructor in valid_instructors]

    def _select_next_course_to_schedule(self, unscheduled_sections_map: Dict[Course, FrozenSet[Section]]) -> Optional[Tuple[Course, List[Domain]]]:
        """
        Selects the next course to schedule using the MRV heuristic.
        """
        best_candidate = None
        min_domain_size = float('inf')
        for course, sections in unscheduled_sections_map.items():
            if not sections: continue
            domains = self._generate_valid_domains(course)
            if not domains: return (course, [])
            if len(domains) < min_domain_size:
                min_domain_size = len(domains)
                best_candidate = (course, domains)
        return best_candidate

    def _form_valid_groups(self, unscheduled_sections: FrozenSet[Section], room: Optional[Room]) -> Iterator[FrozenSet[Section]]:
        """
        A generator that yields all valid subgroups of sections.
        """
        if room is None:
            if unscheduled_sections: yield unscheduled_sections
            return

        sections_by_group: Dict[int, List[Section]] = {}
        for section in unscheduled_sections:
            sections_by_group.setdefault(section.group_number, []).append(section)

        for _, sections_in_group in sections_by_group.items():
            if not sections_in_group: continue
            max_size = room.capacity // STANDARD_SECTION_PLANNING_SIZE
            effective_max_size = min(max_size, len(sections_in_group))
            for size in range(effective_max_size, 0, -1):
                for combo in combinations(sections_in_group, size):
                    yield frozenset(combo)

    def _backtrack(self, assignment: Assignment, unscheduled_sections_map: Dict[Course, FrozenSet[Section]], start_time: float, timeout_seconds: int) -> Optional[Assignment]:
        """
        The core recursive backtracking algorithm, supporting both solver modes.
        """
        if self.mode == SolverMode.OPTIMIZE:
            if self.search_terminated: return None
            if time.time() - start_time > timeout_seconds:
                if not self.search_terminated:
                    print("\n--- Timeout reached! Terminating search. ---")
                    self.search_terminated = True
                return None
        
        if all(not sections for sections in unscheduled_sections_map.values()):
            if self.mode == SolverMode.FIND_FIRST:
                return assignment
            else:
                solution = self._format_solution(assignment)
                score = calculate_solution_score(solution.schedule)
                if score < self.best_score:
                    print(f"Found a new best solution with score: {score:.2f} (Elapsed time: {time.time() - start_time:.2f}s)")
                    self.best_score = score
                    self.best_assignment = assignment
                return None

        selection = self._select_next_course_to_schedule(unscheduled_sections_map)
        if selection is None: return None
        course, domains = selection
        if not domains: return None

        sections_to_schedule = unscheduled_sections_map[course]

        for domain in domains:
            if self.mode == SolverMode.OPTIMIZE and self.search_terminated: return None
            for section_group in self._form_valid_groups(sections_to_schedule, domain[DOM_ROOM]):
                if self.mode == SolverMode.OPTIMIZE and self.search_terminated: return None
                
                variable: Variable = (course, section_group)
                is_valid, conflict_msg = is_consistent(variable, domain, assignment)

                if is_valid:
                    new_assignment = assignment.copy()
                    new_assignment[variable] = domain

                    new_unscheduled_map = deepcopy(unscheduled_sections_map)
                    original_set = new_unscheduled_map[course]
                    updated_set = original_set - section_group
                    new_unscheduled_map[course] = updated_set
                    
                    result = self._backtrack(new_assignment, new_unscheduled_map, start_time, timeout_seconds)
                    
                    if self.mode == SolverMode.FIND_FIRST and result is not None:
                        return result
                # else: print(conflict_msg)
        
        return None

    def _format_solution(self, assignment: Assignment) -> Solution:
        """
        Converts the internal assignment dictionary into the final Solution Pydantic model.
        """
        schedule = []
        for variable, domain in assignment.items():
            scheduled_class = ScheduledClass(
                course=variable[0],
                timeslot=domain[0],
                room=domain[1],
                instructor=domain[2],
                sections=list(variable[1])
            )
            schedule.append(scheduled_class)
        return Solution(schedule=schedule)

if __name__ == '__main__':
    try:
        timetable_data = load_timetable_data_from_excel('./Tables.xlsx')

        dir_path = Path('../timetables')
        dir_path.mkdir(parents=True, exist_ok=True)
        
        # # --- Example of running in OPTIMIZE mode ---
        # print("--- RUNNING IN OPTIMIZE MODE ---")
        # solver_optimize = CSPSolver(timetable_data, mode=SolverMode.OPTIMIZE)
        # solution_optimize = solver_optimize.solve(timeout_seconds=60)
        # if solution_optimize:
        #     print(f"\nOptimization Complete! Best solution found with score: {solution_optimize.score:.2f}")
        #     Path(dir_path/'timetable_optimized.json').write_text(solution_optimize.model_dump_json(indent=2))
        #     print("Optimized solution saved to timetable_optimized.json")
        # else:
        #     print("No solution could be found.")
            
        # print("\n" + "="*50 + "\n")

        # --- Example of running in FIND_FIRST mode ---
        print("--- RUNNING IN FIND FIRST MODE ---")
        solver_first = CSPSolver(timetable_data, mode=SolverMode.FIND_FIRST)
        solution_first = solver_first.solve()
        if solution_first:
            print(f"\nFirst solution found! Score: {solution_first.score:.2f}")
            Path(dir_path/'timetable_first.json').write_text(solution_first.model_dump_json(indent=2))
            print("First solution saved to timetable_first.json")
        else:
            print("No solution could be found.")

    except (ValueError, FileNotFoundError) as e:
        print(e)

