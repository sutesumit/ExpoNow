def render_scenario_summary_table(rows: list[dict]) -> None:
    import streamlit as st

    st.subheader("Scenario Summary")
    st.table(rows)


def render_policy_legend(rows: list[dict]) -> None:
    import streamlit as st

    st.subheader("Policies")
    cols = st.columns(len(rows))
    for col, row in zip(cols, rows):
        col.metric(label=row["Policy"], value=row["Value"])


def render_route_table(rows: list[dict]) -> None:
    import streamlit as st

    st.subheader("Route Segments")
    st.table(rows)


def render_station_table(rows: list[dict]) -> None:
    import streamlit as st

    st.subheader("Stations")
    st.table(rows)


def render_policy_table(rows: list[dict]) -> None:
    import streamlit as st

    st.subheader("Policies")
    st.table(rows)


def render_weight_table(rows: list[dict]) -> None:
    import streamlit as st

    st.subheader("Weights")
    st.table(rows)


def render_bus_departure_table(rows: list[dict]) -> None:
    import streamlit as st

    st.subheader("Bus Departures")
    st.table(rows)


def render_validation_errors(errors: list[str]) -> None:
    import streamlit as st

    st.error("Validation Errors")
    for error in errors:
        st.write(f"- {error}")


def render_bus_timetable(rows: list[dict]) -> None:
    import streamlit as st

    st.subheader("Bus Timetables")
    if not rows:
        st.caption("No bus plans to display.")
    else:
        st.dataframe(rows, width="stretch")


def render_station_queues(station_rows: dict[str, list[dict]]) -> None:
    import streamlit as st

    st.subheader("Station Queues")
    for station_id in sorted(station_rows.keys()):
        rows = station_rows[station_id]
        with st.expander(f"Station {station_id}", expanded=True):
            if not rows:
                st.caption("No charging events at this station.")
            else:
                st.dataframe(rows, width="stretch")


def render_schedule_metrics(rows: list[dict]) -> None:
    import streamlit as st

    if not rows:
        return
    st.subheader("Schedule Metrics")
    COLS_PER_ROW = 4
    for i in range(0, len(rows), COLS_PER_ROW):
        chunk = rows[i : i + COLS_PER_ROW]
        cols = st.columns(len(chunk))
        for col, row in zip(cols, chunk):
            col.metric(label=row["Metric"], value=str(row["Value"]))


def render_score_breakdown(rows: list[dict]) -> None:
    import streamlit as st

    st.subheader("Score Breakdown")
    st.table(rows)


def render_solver_diagnostics(rows: list[dict]) -> None:
    import streamlit as st

    if not rows:
        return
    st.subheader("Solver Diagnostics")
    _STATUS_COLORS = {"good": "green", "warning": "orange", "bad": "red", "info": "gray"}
    COLS_PER_ROW = 4
    for i in range(0, len(rows), COLS_PER_ROW):
        chunk = rows[i : i + COLS_PER_ROW]
        cols = st.columns(len(chunk))
        for col, row in zip(cols, chunk):
            color = _STATUS_COLORS.get(row.get("Status", "info"), "gray")
            col.metric(
                label=f":{color}[●] {row['Metric']}",
                value=row["Value"],
                help=row.get("Note", ""),
            )


def render_infeasible_message(result) -> None:
    import streamlit as st

    st.error("Schedule is not feasible")
    for warning in result.warnings:
        st.caption(f"- {warning}")
