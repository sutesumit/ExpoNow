from typing import Any

from src.domain.scenario import ScenarioSummary


def render_scenario_selector(scenarios: list[ScenarioSummary]) -> str:
    import streamlit as st

    scenario_ids = [scenario.id for scenario in scenarios]
    scenario_names = {scenario.id: scenario.name for scenario in scenarios}

    return st.selectbox(
        "Scenario",
        scenario_ids,
        format_func=lambda scenario_id: scenario_names[scenario_id],
    )


def render_initial_view(
    selected_scenario: ScenarioSummary, schedule_result: Any
) -> None:
    import streamlit as st

    st.subheader(selected_scenario.name)
    st.caption(selected_scenario.description)

    st.info("Placeholder schedule result. Real scheduling begins in a later increment.")
    st.write("Feasible:", schedule_result.feasible)

    if schedule_result.warnings:
        for warning in schedule_result.warnings:
            st.warning(warning)

    st.subheader("Bus Timelines")
    st.write("No bus plans yet.")

    st.subheader("Station Queues")
    st.write("No station reservations yet.")
