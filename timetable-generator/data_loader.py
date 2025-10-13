import pandas as pd
from pathlib import Path
from typing import List, Any
from schemas import (
    TimetableData, Course, Instructor, Room, TimeSlot, Section,
    Curriculum, SessionType
)

def _parse_comma_separated_field(value: Any) -> List[str]:
    """
    Safely parses a string that may contain comma-separated values into a list of strings.
    Handles empty, NaN, or non-string values gracefully.
    """
    if pd.isna(value):
        return []
    s_value = str(value)
    if not s_value.strip():
        return []
    items = [item.strip() for item in s_value.split(',')]
    return [item for item in items if item]

def _parse_courses(df: pd.DataFrame) -> List[Course]:
    """
    Parses the courses DataFrame, creating a separate Course object for each type
    listed in the comma-separated 'type' column.
    """
    courses: List[Course] = []
    for _, row in df.iterrows():
        types = _parse_comma_separated_field(row['type'])
        for single_type in types:
            try:
                course = Course(
                    course_id=row['course_id'],
                    course_name=row['course_name'],
                    type=SessionType(single_type) 
                )
                courses.append(course)
            except ValueError:
                print(f"Warning: Skipping invalid course type '{single_type}' for course '{row['course_id']}'.")
    return courses

def _parse_instructors(df: pd.DataFrame) -> List[Instructor]:
    """
    Parses the instructors DataFrame, handling the comma-separated 'qualifications' column.
    """
    instructors: List[Instructor] = []
    for _, row in df.iterrows():
        qualifications = _parse_comma_separated_field(row['qualifications'])
        instructor = Instructor(
            instructor_id=row['instructor_id'],
            name=row['name'],
            role=row['role'],
            qualifications=qualifications
        )
        instructors.append(instructor)
    return instructors

def _parse_rooms(df: pd.DataFrame) -> List[Room]:
    """
    Parses the rooms DataFrame, handling the comma-separated 'types' column.
    """
    rooms: List[Room] = []
    for _, row in df.iterrows():
        types = _parse_comma_separated_field(row['type'])
        room = Room(
            room_id=row['room_id'],
            types=[SessionType(t) for t in types],
            capacity=row['capacity']
        )
        rooms.append(room)
    return rooms

def _parse_timeslots(df: pd.DataFrame) -> List[TimeSlot]:
    """Parses the timeslots DataFrame into a list of TimeSlot objects."""
    timeslots: List[TimeSlot] = []
    for _, row in df.iterrows():
        timeslot = TimeSlot(
            timeslot_id=row['time_slot_id'],
            day=row['day'],
            start_time=row['start_time'],
            end_time=row['end_time']
        )
        timeslots.append(timeslot)
    return timeslots

def _parse_sections(df: pd.DataFrame) -> List[Section]:
    """Parses the sections DataFrame into a list of Section objects."""
    sections: List[Section] = []
    for _, row in df.iterrows():
        section = Section(
            section_id=row['section_id'],
            group_number=row['group_number'],
            year=row['year'],
            student_count=row['student_count']
        )
        sections.append(section)
    return sections

def _parse_curriculum(df: pd.DataFrame) -> List[Curriculum]:
    """Parses the curriculum DataFrame into a list of Curriculum objects."""
    curriculum: List[Curriculum] = []
    for _, row in df.iterrows():
        curr = Curriculum(
            year=row['year'],
            course_id=row['course_id']
        )
        curriculum.append(curr)
    return curriculum

def load_timetable_data_from_excel(file_path: str) -> TimetableData:
    """
    Main public function to read all timetable data from an Excel file,
    parse and validate it, and return a single TimetableData object.
    """
    try:
        file_path_obj = Path(file_path).expanduser()
        if not file_path_obj.exists():
            raise FileNotFoundError(f'Fatal Error: provided file path {file_path_obj} does not exist.')
        
        sheets = pd.read_excel(file_path_obj, sheet_name=None)

        courses: List[Course] = []
        instructors: List[Instructor] = []
        rooms: List[Room] = []
        timeslots: List[TimeSlot] = []
        sections: List[Section] = []
        curriculum: List[Curriculum] = []

        sheet_parser_map = {
            'Courses': _parse_courses,
            'Instructors': _parse_instructors,
            'Rooms': _parse_rooms,
            'TimeSlots': _parse_timeslots,
            'Sections': _parse_sections,
            'Curriculum': _parse_curriculum
        }

        for required_sheet in sheet_parser_map.keys():
            if required_sheet not in sheets:
                raise ValueError(f"Required sheet '{required_sheet}' not found in the Excel file.")

        courses = sheet_parser_map['Courses'](sheets['Courses'])
        instructors = sheet_parser_map['Instructors'](sheets['Instructors'])
        rooms = sheet_parser_map['Rooms'](sheets['Rooms'])
        timeslots = sheet_parser_map['TimeSlots'](sheets['TimeSlots'])
        sections = sheet_parser_map['Sections'](sheets['Sections'])
        curriculum = sheet_parser_map['Curriculum'](sheets['Curriculum'])

        return TimetableData(
            courses=courses,
            instructors=instructors,
            rooms=rooms,
            timeslots=timeslots,
            sections=sections,
            curriculum=curriculum
        )

    except Exception as e:
        raise ValueError(f"Failed to load or parse the timetable data. Reason: {e}")

if __name__ == '__main__':
    try:
        data = load_timetable_data_from_excel('./Tables.xlsx')
        print("Successfully loaded timetable data!")
        print(f"Total individual course sessions to schedule: {len(data.courses)}")
    except ValueError as e:
        print(e)

