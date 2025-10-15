from csp_solver import CSPSolver
from data_loader import load_timetable_data_from_excel
from schemas import SolverMode, Solution, DayOfWeek, Aliases, InstructorRole
import streamlit as st
import pandas as pd
from typing import Dict, Tuple
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

            alias = ROLE_TO_ALIAS[cls.instructor.role].value if cls.instructor else ""
            
            cell_content = (
                f"<b>{cls.course.course_name} ({cls.course.course_id}) ({cls.course.type.value})</b><br>"
                f"{alias} {cls.instructor.name if cls.instructor else 'N/A'}<br>"
                f"{cls.room.room_id if cls.room else 'N/A'}<br>"
                f"Sec: {', '.join(map(str, section_ids))}"
            )

            record = {
                "year": section.year,
                "group_number": section.group_number,
                "day": cls.timeslot.day.value,
                "time": f"{cls.timeslot.start_time.strftime('%I:%M %p')} - {cls.timeslot.end_time.strftime('%I:%M %p')}",
                "sort_key": SLOT_ORDER.get(cls.timeslot.start_time, 99),
                "content": cell_content
            }
            processed_data.append(record)

    if not processed_data:
        return {}

    df = pd.DataFrame(processed_data).drop_duplicates()

    time_order_df = df[['sort_key', 'time']].drop_duplicates().sort_values('sort_key')
    time_order = time_order_df['time'].tolist()

    df['time'] = pd.Categorical(df['time'], categories=time_order, ordered=True)
    
    day_order = [day.value for day in DayOfWeek]

    group_timetables = {}
    for (year, group), group_df in df.groupby(['year', 'group_number']):
        
        pivot_table = group_df.pivot_table(
            index='time', 
            columns='day',
            values='content',
            aggfunc='first',
            observed=False 
        ).fillna('')

        pivot_table = pivot_table.reindex(columns=day_order).fillna('')
        
        group_timetables[(year, group)] = pivot_table

    return group_timetables



st.set_page_config(
    page_title="Automated Timetable Generator",
    page_icon="📅",
    layout="wide"
)

st.title("📅 Automated Timetable Generator")

st.markdown("""
<style>
/* This targets all <label> elements */
label {
    font-size: 1.1rem !important;
}
/* This targets the <h2> header inside the sidebar */
section[data-testid="stSidebar"] h2 {
    font-size: 1.5rem !important;
}
/* This makes all tables expand to the full width of their container */
table {
    width: 100% !important;
}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Configuration")

    uploaded_file = st.file_uploader(
        "Upload your Excel data file",
        type=["xlsx"],
        help="Upload the 'Tables.xlsx' file containing all the required data sheets."
        )
    
    solver_mode = st.radio(
        label="Select Solver Mode",
        options=[SolverMode.FIND_FIRST, SolverMode.OPTIMIZE],
        format_func=lambda x: x.value,
        help="**Find First:** Stops after the first valid solution is found (fastest). **Optimize:** Searches for the best solution within a time limit."
    )

    timeout = 0
    if solver_mode == SolverMode.OPTIMIZE:
        timeout = st.number_input(
            label="Optimization Timeout (seconds)",
            min_value=10,
            max_value=1000,
            value=60,
            step=10,
            help="The maximum time the solver will search for a better solution."
        )

    generate_button = st.button("Generate Timetable", type="primary")
    
if generate_button:
    if uploaded_file:
        with st.spinner(f"Running solver in '{solver_mode.value}' mode... This may take a moment."):
            try:
                timetable_data = load_timetable_data_from_excel(uploaded_file)
                
                solver = CSPSolver(timetable_data, mode=solver_mode)
                
                solution = solver.solve(timeout_seconds=timeout)

                if solution:
                    st.success("🎉 Timetable Generated Successfully!")
                    st.session_state['solution'] = solution
                else:
                    st.error("No solution could be found that satisfies all constraints.")
                    if 'solution' in st.session_state:
                        del st.session_state['solution']
            except Exception as e:
                st.error(f"An error occurred while running the solver: {e}")
    else:
        st.warning("Please upload your Excel data file first.")

if 'solution' in st.session_state:
    solution = st.session_state['solution']

    st.header("Generated Timetables")
    st.info(f"Displaying solution with score: **{solution.score:.2f}**")
    
    group_timetables = format_solution_for_display(solution)

    for (year, group), timetable_df in sorted(group_timetables.items()):
        st.subheader(f"Year {year}, Group {group}")
        st.markdown(timetable_df.to_html(escape=False), unsafe_allow_html=True)
        st.write("---")
    
    st.download_button(
        label="Download Timetable as JSON",
        data=solution.model_dump_json(indent=2),
        file_name="timetable.json",
        mime="application/json"
    )


