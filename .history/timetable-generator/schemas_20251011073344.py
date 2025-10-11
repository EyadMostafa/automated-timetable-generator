from pydantic import BaseModel, Field
from enum import Enum
from typing import List
from datetime import time

# Using Python's standard Enum for controlled vocabularies
class SessionType(str, Enum):
    """Enumeration for the type of a course session."""
    LECTURE = "Lecture"
    LAB = "Lab"

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
    CourseID: int = Field(description="Primary key. Unique identifier for the course session.")
    CourseName: str = Field(description="The full name of the course (e.g., 'Introduction to Programming').")
    Type: SessionType = Field(description="The type of the session, either a Lecture or a Lab.")

class Instructor(BaseModel):
    """Represents a single instructor."""
    InstructorID: int = Field(description="Primary key. Unique identifier for the instructor.")
    Name: str = Field(description="The full name of the instructor.")

class Room(BaseModel):
    """Represents a physical room where classes can be held."""
    RoomID: int = Field(description="Primary key. Unique identifier for the room.")
    Type: SessionType = Field(description="The type of room, which must match the course type.")
    Capacity: int = Field(description="The maximum number of students the room can accommodate.")

class TimeSlot(BaseModel):
    """Represents a single, discrete time slot in the weekly schedule."""
    TimeSlotID: int = Field(description="Primary key. Unique identifier for the time slot.")
    Day: DayOfWeek = Field(description="The day of the week for this time slot.")
    StartTime: time = Field(description="The starting time of the slot.")
    EndTime: time = Field(description="The ending time of the slot.")

class Section(BaseModel):
    """Represents a specific group of students. The primary key is a composite of SectionID and Year."""
    SectionID: int = Field(description="Part of the composite primary key. The identifier for the section within its year (1-12).")
    Year: int = Field(description="Part of the composite primary key. The academic year of the section (1-4).")
    StudentCount: int = Field(description="The number of students in this section.")

    class Config:
        # Pydantic v2 feature for making the model hashable for use in sets/dicts
        frozen = True

class Curriculum(BaseModel):
    """Represents the rule that a specific year must take a specific course."""
    CurriculumID: int = Field(description="Primary key. Unique ID for this curriculum rule.")
    CourseID: int = Field(description="Foreign key linking to the Course.")
    Year: int = Field(description="The academic year this rule applies to.")

class InstructorQualification(BaseModel):
    """Represents the rule that an instructor is qualified to teach a specific course."""
    InstructorID: int = Field(description="Foreign key linking to the Instructor.")
    CourseID: int = Field(description="Foreign key linking to the Course.")

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

