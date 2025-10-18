import pandas as pd
from schemas import Solution, DayOfWeek, InstructorRole, Aliases
from typing import Dict, Tuple
from datetime import time
from constraints import SLOT_ORDER

ROLE_TO_ALIAS = {
    InstructorRole.PROFESSOR: Aliases.PROFESSOR,
    InstructorRole.DOCTOR: Aliases.DOCTOR,
    InstructorRole.TEACHING_ASSISTANT: Aliases.TEACHING_ASSISTANT,
}

def format_solution_for_display(solution: Solution) -> Dict[Tuple[int, int], pd.DataFrame]:
    """
    Transforms the flat schedule from the solver into a dictionary of pivot tables
    (grids), one for each student group, ready for display in Streamlit.
    """
    
    processed_data = []
    for cls in solution.schedule:
        for section in cls.sections:
            
            section_ids = sorted(list(set(s.section_id for s in cls.sections)))

            alias = ROLE_TO_ALIAS[cls.instructor.role] if cls.instructor else ""
            
            cell_content = (
                f"<b>{cls.course.course_name}({cls.course.course_id}) ({cls.course.type.value})</b><br>"
                f"{alias} {cls.instructor.name if cls.instructor else 'N/A'}<br>"
                f"{cls.room.room_id if cls.room else 'N/A'}<br>"
                f"Sec: {', '.join(map(str, section_ids))}"
            )

            record = {
                "year": section.year,
                "group_number": section.group_number,
                "day": cls.timeslot.day.value,
                "time_str": f"{cls.timeslot.start_time.strftime('%I:%M %p')} - {cls.timeslot.end_time.strftime('%I:%M %p')}",
                "sort_key": SLOT_ORDER.get(cls.timeslot.start_time, 99),
                "content": cell_content
            }
            processed_data.append(record)

    if not processed_data:
        return {}

    df = pd.DataFrame(processed_data).drop_duplicates()

    time_order_df = df[['sort_key', 'time_str']].drop_duplicates().sort_values('sort_key')
    time_order = time_order_df['time_str'].tolist()

    df['time_str'] = pd.Categorical(df['time_str'], categories=time_order, ordered=True)
    
    day_order = [day.value for day in DayOfWeek]

    group_timetables = {}
    for (year, group), group_df in df.groupby(['year', 'group_number']):
        
        pivot_table = group_df.pivot_table(
            index='time_str', 
            columns='day',
            values='content',
            aggfunc='first',
            observed=False 
        ).fillna('')

        pivot_table = pivot_table.reindex(columns=day_order).fillna('')
        
        group_timetables[(year, group)] = pivot_table

    return group_timetables

