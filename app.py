import streamlit as st

from src.app_view_model import build_initial_view_model
from src.ui.layout import render_initial_view, render_scenario_selector


def main() -> None:
    st.set_page_config(page_title="ExpoNow")
    st.title("ExpoNow Bus Charging Scheduler")

    initial_view_model = build_initial_view_model(None)
    selected_scenario_id = render_scenario_selector(initial_view_model.scenarios)
    view_model = build_initial_view_model(selected_scenario_id)
    render_initial_view(view_model.selected_scenario, view_model.schedule_result)


if __name__ == "__main__":
    main()
