from src.domain.models import Scenario
from src.domain.route import total_distance
from src.domain.time import format_minutes
from src.scheduler.contract import ScheduleResult, StationReservation, BusPlan


def build_route_diagram_dot(scenario: Scenario) -> str:
    station_chargers = {s.id: s.charger_count for s in scenario.stations}
    lines = ["digraph Route {"]
    lines.append("  rankdir=LR;")
    lines.append("  node [shape=box, style=filled, fillcolor=lightyellow];")
    lines.append(
        '  "Bengaluru" [fillcolor=lightgreen, shape=ellipse, fontcolor=darkgreen];'
    )
    lines.append(
        '  "Kochi" [fillcolor=lightgreen, shape=ellipse, fontcolor=darkgreen];'
    )

    def dot_escape(v: str) -> str:
        return v.replace('"', '\\"')

    for stop in scenario.route.stops:
        if stop in station_chargers:
            count = station_chargers[stop]
            safe_stop = dot_escape(stop)
            label = f"{safe_stop}\\n{count} charger{'s' if count != 1 else ''}"
            lines.append(f'  "{safe_stop}" [label="{label}"];')

    for seg in scenario.route.segments:
        safe_from = dot_escape(seg.from_stop)
        safe_to = dot_escape(seg.to_stop)
        lines.append(
            f'  "{safe_from}" -> "{safe_to}" [label="{seg.distance_km} km"];'
        )

    lines.append("}")
    return "\n".join(lines)


def build_summary_rows(scenario: Scenario) -> list[dict]:
    return [
        {"Field": "ID", "Value": str(scenario.id)},
        {"Field": "Name", "Value": scenario.name},
        {"Field": "Description", "Value": scenario.description},
        {"Field": "Total Distance (km)", "Value": str(total_distance(scenario.route))},
        {"Field": "Bus Count", "Value": str(len(scenario.buses))},
    ]


def build_route_table(scenario: Scenario) -> list[dict]:
    return [
        {"From": seg.from_stop, "To": seg.to_stop, "Distance (km)": seg.distance_km}
        for seg in scenario.route.segments
    ]


def build_station_table(scenario: Scenario) -> list[dict]:
    return [
        {"Station": station.id, "Chargers": station.charger_count}
        for station in scenario.stations
    ]


def build_policy_rows(scenario: Scenario) -> list[dict]:
    cp = scenario.charging_policy
    tp = scenario.travel_policy
    return [
        {"Policy": "Charging Range", "Value": f"{cp.range_km} km"},
        {"Policy": "Full Charge Duration", "Value": f"{cp.full_charge_minutes} min"},
        {"Policy": "Travel Speed", "Value": f"{tp.speed_kmph} km/h"},
    ]


def build_weight_rows(scenario: Scenario) -> list[dict]:
    w = scenario.weights
    return [
        {"Weight": "Individual", "Value": w.individual},
        {"Weight": "Operator", "Value": w.operator},
        {"Weight": "Overall", "Value": w.overall},
    ]


def build_bus_departure_table(scenario: Scenario) -> list[dict]:
    return [
        {
            "Bus ID": bus.id,
            "Operator": bus.operator,
            "Direction": bus.direction,
            "Departure": format_minutes(bus.departure_minutes),
        }
        for bus in scenario.buses
    ]


def _find_arrival_minutes(plan: BusPlan, station_id: str) -> int | None:
    for event in plan.events:
        if event.event_type == "arrival" and event.location == station_id:
            return event.minutes
    return None


def _find_charge_end_minutes(plan: BusPlan, station_id: str) -> int | None:
    for event in plan.events:
        if event.event_type == "charge_end" and event.location == station_id:
            return event.minutes
    return None


def build_bus_timetable_rows(result: ScheduleResult) -> list[dict]:
    reservation_lookup: dict[tuple[str, str], StationReservation] = {}
    for res in result.station_reservations:
        reservation_lookup[(res.bus_id, res.station)] = res

    rows: list[dict] = []
    for plan in result.bus_plans:
        if not plan.events:
            continue

        departure_minutes = plan.events[0].minutes
        station_arrivals: dict[str, int] = {}

        for event in plan.events:
            if event.event_type == "arrival":
                station_arrivals[event.location] = event.minutes
            elif event.event_type == "charge_start":
                station = event.location
                arrival = station_arrivals.get(station)
                wait = event.minutes - arrival if arrival is not None else 0
                charge_end = _find_charge_end_minutes(plan, station)
                res = reservation_lookup.get((plan.bus_id, station))

                rows.append({
                    "Bus ID": plan.bus_id,
                    "Operator": plan.operator,
                    "Direction": plan.direction,
                    "Departure": format_minutes(departure_minutes),
                    "Station": station,
                    "Arrival": format_minutes(arrival) if arrival is not None else "",
                    "Wait (min)": wait,
                    "Charge Start": format_minutes(event.minutes),
                    "Charge End": format_minutes(charge_end) if charge_end is not None else "",
                    "Charger Lane": res.charger_lane if res else "",
                    "Final Arrival": format_minutes(plan.final_arrival_minutes) if plan.final_arrival_minutes is not None else "",
                })

    return sorted(rows, key=lambda r: (r["Departure"], r["Bus ID"]))


def build_station_queue_rows(result: ScheduleResult) -> dict[str, list[dict]]:
    bus_plan_lookup: dict[str, BusPlan] = {plan.bus_id: plan for plan in result.bus_plans}

    station_rows: dict[str, list[dict]] = {}
    for res in result.station_reservations:
        plan = bus_plan_lookup.get(res.bus_id)
        arrival_minutes = _find_arrival_minutes(plan, res.station) if plan else None
        wait = res.start_minutes - arrival_minutes if arrival_minutes is not None else 0

        if res.station not in station_rows:
            station_rows[res.station] = []

        station_rows[res.station].append({
            "Bus ID": res.bus_id,
            "Operator": plan.operator if plan else "",
            "Direction": plan.direction if plan else "",
            "Arrival": format_minutes(arrival_minutes) if arrival_minutes is not None else "",
            "Charge Start": format_minutes(res.start_minutes),
            "Charge End": format_minutes(res.end_minutes),
            "Wait (min)": wait,
            "Charger Lane": res.charger_lane,
        })

    for station_id in station_rows:
        station_rows[station_id].sort(
            key=lambda r: (r["Charge Start"], r["Charger Lane"], r["Bus ID"])
        )

    return station_rows
