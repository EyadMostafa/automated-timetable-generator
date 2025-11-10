# **Project Documentation: Automated Timetable Generator**

This document outlines the complete design, architecture, and logic for the Automated University Timetable Generator. The system is designed to take raw university data from an Excel file and produce a valid, conflict-free, and optimized weekly schedule.

## **Phase 1: Data Model (Database Schema)**

The system is built on a set of normalized data tables, which are expected to be provided as sheets in a single Tables.xlsx file.

### **1\. Courses**

Lists all individual course sessions. The type column uses comma-separation for subjects with multiple session types (e.g., "Lecture,Lab"), which the data loader parses into separate objects.

| Column Name | Data Type | Description |
| :---- | :---- | :---- |
| course\_id | Text | **Primary Key.** The unique ID for the course subject (e.g., "CSC 111"). |
| course\_name | Text | The name of the course (e.g., "Fundamentals of Programming"). |
| type | Text | The session types, comma-separated (e.g., "Lecture,Lab,Tutorial"). |

### **2\. Instructors**

Lists all instructors and their qualifications. The qualifications column uses comma-separation.

| Column Name | Data Type | Description |
| :---- | :---- | :---- |
| instructor\_id | Integer | **Primary Key.** Unique identifier for the instructor. |
| name | Text | The instructor's full name. |
| role | Text | The instructor's role (e.g., "Doctor", "Professor", "Teaching Assistant"). |
| qualifications | Text | A comma-separated list of course\_ids the instructor can teach. |

### **3\. Rooms**

Lists all available rooms. The types column uses comma-separation for rooms compatible with multiple session types.

| Column Name | Data Type | Description |
| :---- | :---- | :---- |
| room\_id | Text | **Primary Key.** Unique identifier for the room (e.g., "B07 F1.04"). |
| types | Text | Comma-separated list of session types the room can host (e.g., "Lab,Tutorial"). |
| capacity | Integer | The maximum number of "planning slots" the room has (e.g., 45). |

### **4\. TimeSlots**

Defines the discrete 1.5-hour time blocks for the week.

| Column Name | Data Type | Description |
| :---- | :---- | :---- |
| time\_slot\_id | Text | **Primary Key.** Unique identifier (e.g., "sun\_9:00\_10:30"). |
| day | Text | The day of the week (e.g., "Sunday"). |
| start\_time | Time | The start time (24-hour format, e.g., "14:15"). |
| end\_time | Time | The end time (24-hour format, e.g., "15:45"). |

### **5\. Sections**

Defines the student groups. This is the core table for modeling the student body and their academic programs.

| Column Name | Data Type | Description |
| :---- | :---- | :---- |
| section\_id | Integer | **Composite PK.** The section identifier within its year (e.g., 1-9). |
| group\_number | Integer | The parent group this section belongs to. |
| year | Integer | **Composite PK.** The academic year (1-4). |
| major | Text | The section's major (e.g., "general", "AID", "CNC"). |
| student\_count | Integer | The number of students enrolled in the section. |

### **6\. Curriculum**

Defines the "contract" for the solver. It specifies which courses are required for which student populations.

| Column Name | Data Type | Description |
| :---- | :---- | :---- |
| year | Integer | **Composite PK.** The academic year. |
| major | Text | **Composite PK.** The major this rule applies to. "general" is used for courses shared by all majors in that year. |
| course\_id | Text | **Composite PK.** The course\_id of the required course. |

## **Phase 2: Core Solver Design (Dynamic State-Space Search)**

The project is **not** a classic Constraint Satisfaction Problem (CSP). It is a more advanced **Dynamic Constraint Satisfaction Problem (DCSP)**, as the variables (the student groups) are not fixed and must be determined on the fly based on resource availability (the rooms).

### **1\. State Representation**

The solver's "to-do list" is not a static list of variables. It is a dictionary:

* unscheduled\_sections\_map: Dict\[Course, FrozenSet\[Section\]\]  
  This map holds the current state of the problem, mapping each Course object to the set of Sections that still need to be scheduled for it. The solver's goal is to make all sets in this map empty.

### **2\. Solver Algorithm**

The solver uses a **recursive backtracking algorithm** that performs a state-space search. At each step, the solver:

1. **Selects a Course:** Uses the **Minimum Remaining Values (MRV)** heuristic to select the most constrained Course to schedule from the to-do list.  
2. **Generates Offerings:** Generates a list of valid (TimeSlot, Room, Instructor) tuples for that course by applying all unary constraints (room type, instructor qualifications, instructor role).  
3. **Forms Dynamic Groups:** For each valid offering, it intelligently forms potential student groups from the unscheduled sections. This logic is constrained by:  
   * **Room Capacity:** It respects the room.capacity by dividing it by the STANDARD\_SECTION\_PLANNING\_SIZE (15) to find the max number of sections that can fit.  
   * **Parent Group:** It only forms groups from sections that share the same group\_number.  
4. **Checks Consistency:** For each potential class (Course \+ Offering \+ Student Group), it calls is\_consistent to check for all hard constraint conflicts (instructor, room, or section clashes).  
5. **Recurses:** If consistent, it creates a new state (a new to-do list) and recurses. If it finds a solution, it either returns it (in "Find First" mode) or saves it and continues searching (in "Optimize" mode).  
6. **Backtracks:** If a path leads to a dead end, it returns, and the loop continues to the next option.

## **Phase 3: Constraints (The Rules Engine)**

### **Hard Constraints (Must Not Be Violated)**

1. **Instructor Uniqueness:** An instructor cannot be in two places at once.  
2. **Room Uniqueness:** A room cannot be used for two classes at once.  
3. **Section Uniqueness:** A section cannot attend two classes at once.  
4. **Resource Match:** A class must be assigned a valid room type and a qualified instructor (by role and qualification).  
5. **Project Day (Major-Aware):** A Project course blocks off an entire day for all students *of that specific major* (or all majors if "general"). It cannot conflict with any other class for those same students on that day.

### **Soft Constraints (Optimization & Scoring)**

The solver finds the "best" solution by minimizing a penalty score.

1. **Student Gaps:** \+10 points for every 1.5-hour gap found in any section's daily schedule.  
2. **Undesirable Slots:** \+3 points for any class scheduled in the first (9:00 AM) or last (2:15 PM) slot of the day.  
3. **Uneven Distribution:** The **standard deviation** of classes per day is calculated for each section. The sum of all sections' standard deviations is added to the total score.

## **Phase 4: Application & UI (Streamlit)**

A user-friendly web interface built with Streamlit.

* **File Upload:** A sidebar widget allows the user to upload their Tables.xlsx file.  
* **Solver Modes:**  
  * **Find First:** The solver stops and returns the first valid solution it finds.  
  * **Optimize:** The solver continues searching for the entire duration of the timeout, returning the solution with the lowest penalty score found in that time.  
* **Dynamic Filtering:** The final solution is displayed in a series of clear timetable grids (one for each group). The user can filter this view in real-time by:  
  * Instructor  
  * Year  
  * Section (e.g., "Y3-S1-AID")  
  * Room  
* **Download:** The user can download the complete, unfiltered timetable as a timetable.json file.