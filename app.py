import streamlit as st

from src.adapters.scenario_catalog import list_scenario_summaries
from src.app_view_model import InitialViewModel, build_initial_view_model
from src.ui.layout import (
    render_input_view,
    render_scenario_selector,
    render_schedule_output,
)


@st.cache_data
def _get_cached_view_model(selected_scenario_id: str | None) -> InitialViewModel:
    return build_initial_view_model(selected_scenario_id)


def main() -> None:
    st.set_page_config(page_title="ExpoNow")
    st.title("ExpoNow Bus Charging Scheduler")

    scenarios = list_scenario_summaries()
    selected_scenario_id = render_scenario_selector(scenarios)
    view_model = _get_cached_view_model(selected_scenario_id)

    render_input_view(view_model)

    if not view_model.validation_errors:
        render_schedule_output(view_model.schedule_result)


if __name__ == "__main__":
    main()
