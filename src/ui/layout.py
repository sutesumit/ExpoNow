from typing import Any

from src.app_view_model import InitialViewModel
from src.domain.scenario import ScenarioSummary
from src.reporting import metrics as reporting_metrics
from src.reporting import tables as reporting
from src.scheduler.contract import ScheduleResult
from src.ui import components as ui


def render_scenario_selector(scenarios: list[ScenarioSummary]) -> str:
    import streamlit as st

    scenario_ids = [scenario.id for scenario in scenarios]
    scenario_names = {scenario.id: scenario.name for scenario in scenarios}

    return st.selectbox(
        "Scenario",
        scenario_ids,
        format_func=lambda scenario_id: scenario_names[scenario_id],
    )


def render_input_view(view_model: InitialViewModel) -> None:
    import streamlit as st

    if view_model.validation_errors:
        ui.render_validation_errors(view_model.validation_errors)
        return

    scenario = view_model.scenario

    ui.render_scenario_summary_table(reporting.build_summary_rows(scenario))

    ui.render_schedule_metrics(reporting_metrics.build_summary_metrics(view_model.schedule_result))

    with st.expander("Scenario Details", expanded=False):
        ui.render_route_diagram(reporting.build_route_diagram_dot(scenario))
        ui.render_policy_legend(reporting.build_policy_rows(scenario))

        col_a, col_b = st.columns(2)
        with col_a:
            ui.render_route_table(reporting.build_route_table(scenario))
            ui.render_policy_table(reporting.build_policy_rows(scenario))
        with col_b:
            ui.render_station_table(reporting.build_station_table(scenario))
            ui.render_weight_table(reporting.build_weight_rows(scenario))

    ui.render_bus_departure_table(reporting.build_bus_departure_table(scenario))


def render_schedule_output(result: ScheduleResult) -> None:
    import streamlit as st

    if not result.feasible:
        ui.render_infeasible_message(result)
        return

    if result.bus_plans:
        ui.render_bus_timetable(reporting.build_bus_timetable_rows(result))
        ui.render_station_queues(reporting.build_station_queue_rows(result))

    if result.score_breakdown and result.score_breakdown.components:
        ui.render_score_breakdown(
            reporting_metrics.build_score_rows(result.score_breakdown)
        )

    if result.warnings:
        st.warning("Schedule Warnings:")
        for warning in result.warnings:
            st.write(f"- {warning}")


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

    if schedule_result.score_breakdown:
        weights = schedule_result.score_breakdown.components.get("weights", {})
        if weights:
            st.subheader("Scenario Weights")
            st.write(f"Individual: {weights.get('individual', 'N/A')}")
            st.write(f"Operator: {weights.get('operator', 'N/A')}")
            st.write(f"Overall: {weights.get('overall', 'N/A')}")

    st.subheader("Bus Timelines")
    st.write("No bus plans yet.")

    st.subheader("Station Queues")
    st.write("No station reservations yet.")
