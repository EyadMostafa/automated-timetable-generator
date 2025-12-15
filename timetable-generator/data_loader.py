import pandas as pd
from pathlib import Path
from typing import List, Any, Dict
from schemas import (
    TimetableData, Course, Instructor, Room, TimeSlot, Section,
    Curriculum, SessionType
)

def _clean_str(value: Any) -> str:
    """
    Helper to ensure strings are stripped of whitespace.
    Only used for text fields.
    """
    if pd.isna(value):
        return ""
    return str(value).strip()

def _parse_comma_separated_field(value: Any) -> List[str]:
    """
    Safely parses a string that may contain comma-separated values into a list of strings.
    """
    if pd.isna(value):
        return []
    s_value = str(value)
    if not s_value.strip():
        return []
    items = [item.strip() for item in s_value.split(',')]
    return [item for item in items if item]

def _parse_courses(df: pd.DataFrame) -> List[Course]:
    courses: List[Course] = []
    for _, row in df.iterrows():
        types = _parse_comma_separated_field(row['type'])
        
        # Clean the string identifiers
        c_id = _clean_str(row['course_id'])
        c_name = _clean_str(row['course_name'])
        
        for single_type in types:
            try:
                course = Course(
                    course_id=c_id,
                    course_name=c_name,
                    type=SessionType(single_type) 
                )
                courses.append(course)
            except ValueError:
                print(f"Warning: Skipping invalid course type '{single_type}' for course '{c_id}'.")
    return courses

def _parse_instructors(df: pd.DataFrame) -> List[Instructor]:
    instructors: List[Instructor] = []
    for _, row in df.iterrows():
        qualifications = _parse_comma_separated_field(row['qualifications'])
        instructor = Instructor(
            instructor_id=row['instructor_id'], # Keep ID as is (int)
            name=_clean_str(row['name']),
            role=_clean_str(row['role']),
            qualifications=qualifications
        )
        instructors.append(instructor)
    return instructors

def _parse_rooms(df: pd.DataFrame) -> List[Room]:
    rooms: List[Room] = []
    for _, row in df.iterrows():
        types = _parse_comma_separated_field(row['type'])
        room = Room(
            room_id=_clean_str(row['room_id']),
            types=[SessionType(t) for t in types],
            capacity=row['capacity'] # Keep capacity as is (int)
        )
        rooms.append(room)
    return rooms

def _parse_timeslots(df: pd.DataFrame) -> List[TimeSlot]:
    timeslots: List[TimeSlot] = []
    for _, row in df.iterrows():
        timeslot = TimeSlot(
            timeslot_id=_clean_str(row['time_slot_id']),
            day=_clean_str(row['day']),
            start_time=row['start_time'], # Keep as time object
            end_time=row['end_time']      # Keep as time object
        )
        timeslots.append(timeslot)
    return timeslots

def _parse_sections(df: pd.DataFrame) -> List[Section]:
    sections: List[Section] = []
    for _, row in df.iterrows():
        section = Section(
            section_id=row['section_id'],       # Keep as int
            group_number=row['group_number'],   # Keep as int
            year=row['year'],                   # Keep as int
            major=_clean_str(row['major']),
            student_count=row['student_count']  # Keep as int
        )
        sections.append(section)
    return sections

def _parse_curriculum(df: pd.DataFrame) -> List[Curriculum]:
    curriculum: List[Curriculum] = []
    for _, row in df.iterrows():
        curr = Curriculum(
            year=row['year'],                   # Keep as int
            major=_clean_str(row['major']),
            course_id=_clean_str(row['course_id'])
        )
        curriculum.append(curr)
    return curriculum

def load_timetable_data_from_excel(file_path_or_buffer) -> TimetableData:
    """
    Main public function to read all timetable data from an Excel file.
    Accepts file path (str) or buffer (UploadedFile).
    """
    try:
        # Handle file paths vs Streamlit buffers
        if isinstance(file_path_or_buffer, str):
            file_path_obj = Path(file_path_or_buffer).expanduser()
            if not file_path_obj.exists():
                raise FileNotFoundError(f'Fatal Error: provided file path {file_path_obj} does not exist.')
            xls = pd.ExcelFile(file_path_obj)
        else:
            xls = pd.ExcelFile(file_path_or_buffer)
        
        sheet_names = ['Courses', 'Instructors', 'Rooms', 'TimeSlots', 'Sections', 'Curriculum']
        data_frames: Dict[str, pd.DataFrame] = {}
        
        for sheet in sheet_names:
            if sheet not in xls.sheet_names:
                raise ValueError(f"Required sheet '{sheet}' not found in the Excel file.")
            data_frames[sheet] = pd.read_excel(xls, sheet_name=sheet)

        # --- FIX: Removed the generic df.apply(str.strip) block that caused crashes on time objects ---
        # The specific parsers above now handle cleaning safely.

        courses = _parse_courses(data_frames['Courses'])
        instructors = _parse_instructors(data_frames['Instructors'])
        rooms = _parse_rooms(data_frames['Rooms'])
        timeslots = _parse_timeslots(data_frames['TimeSlots'])
        sections = _parse_sections(data_frames['Sections'])
        curriculum = _parse_curriculum(data_frames['Curriculum'])

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