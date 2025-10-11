from pydantic import BaseModel, Field
from enum import Enum
from typing import List
from datetime import time

# Using Python's standard Enum for controlled vocabularies
class SessionType(str, Enum):
    """Enumeration for the type of a course session."""
    LECTURE = "Lecture"
    LAB = "Lab"
    TUTORIAL = "Tutorial" # Added new type

class DayOfWeek(str, Enum):
    """Enumeration for the days of the week."""
    SUNDAY = "Sunday"
    MONDAY = "Monday"
    TUESDAY = "Tuesday"
    WEDNESDAY = "Wednesday"
    THURSDAY = "Thursday"

# --- Base Models Reflecting Database Tables ---

class Course(BaseModel):
    """Represents a single, schedulable course or lab session."""
    course_id: int = Field(description="Primary key. Unique identifier for the course session.")
    course_name: str = Field(description="The full name of the course (e.g., 'Introduction to Programming').")
    type: SessionType = Field(description="The type of the session: Lecture, Lab, or Tutorial.")

class Instructor(BaseModel):
    """Represents a single instructor."""
    instructor_id: int = Field(description="Primary key. Unique identifier for the instructor.")
    name: str = Field(description="The full name of the instructor.")

class Room(BaseModel):
    """Represents a physical room where classes can be held."""
    room_id: int = Field(description="Primary key. Unique identifier for the room.")
    type: SessionType = Field(description="The type of room, which must match the course type.")
    capacity: int = Field(description="The maximum number of students the room can accommodate.")

class TimeSlot(BaseModel):
    """Represents a single, 1.5-hour discrete time slot in the weekly schedule."""
    time_slot_id: int = Field(description="Primary key. Unique identifier for the time slot.")
    day: DayOfWeek = Field(description="The day of the week for this time slot.")
    start_time: time = Field(description="The starting time of the slot.")
    end_time: time = Field(description="The ending time of the slot.")

class Section(BaseModel):
    """Represents a specific group of students. The primary key is a composite of section_id and year."""
    section_id: int = Field(description="Part of the composite primary key. The identifier for the section within its year (1-12).")
    year: int = Field(description="Part of the composite primary key. The academic year of the section (1-4).")
    student_count: int = Field(description="The number of students in this section.")

    class Config:
        frozen = True

class Curriculum(BaseModel):
    """Represents the rule that a specific year must take a specific course."""
    curriculum_id: int = Field(description="Primary key. Unique ID for this curriculum rule.")
    course_id: int = Field(description="Foreign key linking to the Course.")
    year: int = Field(description="The academic year this rule applies to.")

class InstructorQualification(BaseModel):
    """Represents the rule that an instructor is qualified to teach a specific course."""
    instructor_id: int = Field(description="Foreign key linking to the Instructor.")
    course_id: int = Field(description="Foreign key linking to the Course.")

# --- A container model to hold all the loaded data ---

class TimetableData(BaseModel):
    """A top-level model to hold all the parsed and validated data for the timetable problem."""
    courses: List[Course]
    instructors: List[Instructor]
    rooms: List[Room]
    timeslots: List[TimeSlot]
    sections: List[Section]
    curriculum: List[Curriculum]
    qualifications: List[InstructorQualification]

