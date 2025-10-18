import streamlit as st
from schemas import SolverMode, Solution
from data_loader import load_timetable_data_from_excel
from csp_solver import CSPSolver
from display_utils import format_solution_for_display

st.set_page_config(
    page_title="Automated Timetable Generator",
    page_icon="📅",
    layout="wide"
)

st.title("📅 Automated Timetable Generator")
st.markdown("""
<style>
/* This targets all <label> elements to make them larger */
label {
    font-size: 1.1rem !important;
}
/* This targets the <h2> header specifically inside the sidebar */
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
                    st.session_state['timetable_data'] = timetable_data
                    st.session_state['solution'] = solution
                else:
                    st.error("No solution could be found that satisfies all constraints.")
                    if 'solution' in st.session_state: del st.session_state['solution']
                    if 'timetable_data' in st.session_state: del st.session_state['timetable_data']
            except Exception as e:
                st.error(f"An error occurred while running the solver: {e}")
    else:
        st.warning("Please upload your Excel data file first.")

if 'solution' in st.session_state:
    solution = st.session_state['solution']
    timetable_data = st.session_state['timetable_data']

    st.header("🔍 Filter and View Timetables")
    st.info(f"Displaying solution with score: **{solution.score:.2f}**")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        instructor_names = ["All"] + sorted(list(set(inst.name for inst in timetable_data.instructors)))
        selected_instructor = st.selectbox("Filter by Instructor", options=instructor_names)
    with col2:
        years = ["All"] + sorted(list(set(sec.year for sec in timetable_data.sections)))
        selected_year = st.selectbox("Filter by Year", options=years)
    with col3:
        section_ids = ["All"] + sorted(list(set(sec.section_id for sec in timetable_data.sections)))
        selected_section = st.selectbox("Filter by Section", options=section_ids)
    with col4:
        rooms = ["All"] + (list(set(room.room_id for room in timetable_data.rooms)))
        selected_room = st.selectbox("Filter by Room", options=rooms)

    filtered_schedule = solution.schedule
    if selected_instructor != "All":
        filtered_schedule = [
            cls for cls in filtered_schedule 
            if cls.instructor and cls.instructor.name == selected_instructor
        ]
    if selected_year != "All":
        filtered_schedule = [
            cls for cls in filtered_schedule 
            if any(sec.year == selected_year for sec in cls.sections)
        ]
    if selected_section != "All":
        filtered_schedule = [
            cls for cls in filtered_schedule
            if any(sec.section_id == selected_section for sec in cls.sections)
        ]
    if selected_room != "All":
        filtered_schedule = [
            cls for cls in filtered_schedule
            if cls.room and cls.room.room_id == selected_room 
        ]
    
    filtered_schedule_data = [cls.model_dump() for cls in filtered_schedule]
    filtered_solution = Solution(schedule=filtered_schedule_data, score=solution.score)
    
    group_timetables = format_solution_for_display(filtered_solution)

    if not group_timetables:
        st.warning("No classes match the current filter criteria.")
    else:
        for (year, group), timetable_df in sorted(group_timetables.items()):
            if (selected_year == "All" or year == selected_year):
                st.subheader(f"Year {year}, Group {group}")
                st.markdown(timetable_df.to_html(escape=False), unsafe_allow_html=True)
                st.write("---")
    
    st.download_button(
        label="Download Full Timetable as JSON",
        data=solution.model_dump_json(indent=2),
        file_name="timetable_full.json",
        mime="application/json"
    )

