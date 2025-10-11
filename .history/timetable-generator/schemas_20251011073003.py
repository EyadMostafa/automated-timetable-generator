from pydantic import BaseModel, Field
from enum import Enum
from typing import List, Tuple
from datetime import time

# Using Python's standard Enum for controlled vocabularies
class SessionType(str, Enum):
    LECTURE = "Lecture"
    LAB = "Lab"

class DayOfWeek(str, Enum):
    SUNDAY = "Sunday"
    MONDAY = "Monday"
    TUESDAY = "Tuesday"
    WEDNESDAY = "Wednesday"
    THURSDAY = "Thursday"

# --- Base Models Reflecting Database Tables ---

class Course(BaseModel):
    CourseID: int
    CourseName: str
    Type: SessionType

class Instructor(BaseModel):
    InstructorID: int
    Name: str

class Room(BaseModel):
    RoomID: int
    Type: SessionType
    Capacity: int

class TimeSlot(BaseModel):
    TimeSlotID: int
    Day: DayOfWeek
    StartTime: time
    EndTime: time

class Section(BaseModel):
    # The primary key is a composite of SectionID and Year
    SectionID: int
    Year: int
    StudentCount: int

    class Config:
        # Pydantic v2 feature for making the model hashable for use in sets/dicts
        frozen = True

class Curriculum(BaseModel):
    CurriculumID: int
    CourseID: int
    Year: int

class InstructorQualification(BaseModel):
    InstructorID: int
    CourseID: int

# --- A model to hold all the loaded data ---

class TimetableData(BaseModel):
    courses: List[Course]
    instructors: List[Instructor]
    rooms: List[Room]
    timeslots: List[TimeSlot]
    sections: List[Section]
    curriculum: List[Curriculum]
    qualifications: List[InstructorQualification]
