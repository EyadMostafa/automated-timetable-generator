from pydantic import BaseModel, Field
from enum import Enum
from typing import List, Optional
from datetime import time

# Using Python's standard Enum for controlled vocabularies
class SessionType(str, Enum):
    """Enumeration for the type of a course session."""
    LECTURE = "Lecture"
    LAB = "Lab"
    TUTORIAL = "Tutorial"
    PROJECT = "Project"

class DayOfWeek(str, Enum):
    """Enumeration for the days of the week."""
    SUNDAY = "Sunday"
    MONDAY = "Monday"
    TUESDAY = "Tuesday"
    WEDNESDAY = "Wednesday"
    THURSDAY = "Thursday"

class InstructorRole(str, Enum):
    """Enumeration for the role of an instructor."""
    PROFESSOR = "Professor"
    DOCTOR = "Doctor"
    TEACHING_ASSISTANT = "Teaching Assistant"

# --- Base Models Reflecting Database Tables ---

class Course(BaseModel):
    """Represents a single, unique, schedulable session (e.g., the Lecture for CS101)."""
    course_id: str = Field(description="The unique identifier for the course subject (e.g., 'CS101').")
    course_name: str = Field(description="The name of the course subject (e.g., 'Introduction to Programming').")
    type: SessionType = Field(description="The specific type of this session: Lecture, Lab, or Tutorial.")

    class Config:
        frozen = True

class Instructor(BaseModel):
    """Represents a single instructor, including their role and qualifications."""
    instructor_id: int = Field(description="Primary key. Unique identifier for the instructor.")
    name: str = Field(description="The full name of the instructor.")
    role: InstructorRole = Field(description="The role of the instructor.")
    qualifications: List[str] = Field(description="A list of course_ids the instructor is qualified to teach.")

class Room(BaseModel):
    """Represents a physical room where classes can be held."""
    room_id: str = Field(description="Primary key. Unique identifier for the room (e.g., 'B1-101').")
    types: List[SessionType] = Field(description="The type of room, which must match the course offering type.")
    capacity: int = Field(description="The maximum number of students the room can accommodate.")

class TimeSlot(BaseModel):
    """Represents a single, 1.5-hour discrete time slot in the weekly schedule."""
    timeslot_id: str = Field(description="Primary key. Unique identifier for the time slot (e.g., 'sun_0900_1030').")
    day: DayOfWeek = Field(description="The day of the week for this time slot.")
    start_time: time = Field(description="The starting time of the slot.")
    end_time: time = Field(description="The ending time of the slot.")

class Section(BaseModel):
    """Represents a specific group of students. The primary key is a composite of section_id and year."""
    section_id: int = Field(description="Part of the composite primary key. The identifier for the section within its year (1-9).")
    group_number: int = Field(description="The parent group this section belongs to (1-3).")
    year: int = Field(description="Part of the composite primary key. The academic year of the section (1-4).")
    student_count: int = Field(description="The number of students in this section.")

    class Config:
        frozen = True

class Curriculum(BaseModel):
    """Links a year to the courses they must take. The primary key is a composite of course_id and year."""
    year: int = Field(description="Part of the composite primary key. The academic year this rule applies to.")
    course_id: str = Field(description="Part of the composite primary key. Foreign key linking to the Course.")

# --- A container model to hold all the loaded data ---

class TimetableData(BaseModel):
    """A top-level model to hold all the parsed and validated data."""
    courses: List[Course] = Field(...)
    instructors: List[Instructor] = Field(...)
    rooms: List[Room] = Field(...)
    timeslots: List[TimeSlot] = Field(...)
    sections: List[Section] = Field(...)
    curriculum: List[Curriculum] = Field(...)

# --- Models for the Solver's Output ---

class ScheduledClass(BaseModel):
    """Represents a single, fully scheduled class in the final timetable."""
    course: Course = Field(...)
    timeslot: TimeSlot = Field(...)
    room: Optional[Room] = Field(None, description="The room assigned. Null for 'Project' type.")
    instructor: Optional[Instructor] = Field(None, description="The instructor assigned. Null for 'Project' type.")
    sections: List[Section] = Field(..., description="The list of student sections attending this class.")

class Solution(BaseModel):
    """The complete timetable solution, represented as a flat list of scheduled classes for easy processing."""
    schedule: List[ScheduledClass]
    score: float = Field(0.0)
