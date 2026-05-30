# Architecture Overview

## Framework / Approach for the Scheduler

### Chosen Approach: Constraint-Based Optimization with Weighted Scoring

**Framework:** Custom constraint satisfaction engine with weighted objective function

**Why this approach fits:**
1. **Multi-objective optimization:** The problem requires balancing three competing soft rules (individual, operator, overall) with tunable weights
2. **Hard constraints are absolute:** Range limits, single charger, ordering must always be satisfied
3. **Scalability:** Constraint-based systems decouple rules from the solver, allowing new rules to be added without engine rewrites
4. **Deterministic scheduling:** Unlike ML approaches, constraint solvers produce reproducible, explainable schedules

**Alternative considered but rejected:**
- Pure simulation: Would require complex rollback/retry logic for contention
- Genetic algorithms: Overkill for this scale; less interpretable
- Linear programming: Hard to model discrete ordering decisions cleanly

### Core Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Streamlit UI Layer                       │
│  - Scenario selector                                        │
│  - Input display                                            │
│  - Bus timetables                                           │
│  - Station views                                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Scheduler Engine                           │
│  - Constraint Validator (hard rules)                         │
│  - Objective Function (soft rules with weights)              │
│  - Search Strategy (greedy with backtracking for feasibility)│
│  - Timeline Builder                                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Data Layer                                 │
│  - Scenario definitions (JSON)                               │
│  - Route configuration                                       │
│  - Station configuration                                     │
│  - Weights configuration                                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Structure Design

### Core Entities

```python
@dataclass
class Route:
    segments: List[Segment]  # Ordered list: BK, KA, AB, BC, CD, DA, AK
    stations: List[str]       # ['A', 'B', 'C', 'D'] - only scheduling stations

@dataclass
class Segment:
    start: str   # Station code
    end: str     # Station code  
    distance_km: float
    travel_minutes: int  # Derived at 60 km/h

@dataclass
class Bus:
    id: str
    operator: str
    direction: Direction  # Enum: BENGALURU_TO_KOCHI, KOCHI_TO_BENGALURU
    departure_time: datetime
    departure_station: str  # Always origin for direction

@dataclass
class Scenario:
    name: str
    buses: List[Bus]
    weights: Weights
    description: str

@dataclass
class Weights:
    individual: float = 1.0
    operator: float = 1.0
    overall: float = 1.0

@dataclass
class ChargingPlan:
    bus_id: str
    stations_used: List[ChargingStop]  # Ordered by route
    timeline: List[TimelineEvent]

@dataclass
class ChargingStop:
    station: str
    arrival_time: datetime
    departure_time: datetime
    wait_time: int  # Minutes waiting for charger

@dataclass
class TimelineEvent:
    type: EventType  # DEPART, CHARGE, ARRIVE
    station: str
    start_time: datetime
    end_time: datetime
```

### Design Principles

1. **Separation of concerns:** Route/stations are separate from scenarios, allowing reuse
2. **Extensibility:** All lists and enums can grow without breaking existing code
3. **Immutability where possible:** Use dataclasses with frozen=True for configuration
4. **Clear ownership:** Each entity has a single source of truth

---

## Anticipated Future Changes & Handling

### 1. Multiple Chargers Per Station
**Change:** Add `chargers: int` to Station entity  
**Handling:**  
- `Station.chargers` defaults to 1  
- Constraint validator checks `len(queue) <= chargers`  
- No code changes needed, data-only update

### 2. Priority Buses
**Change:** Add `priority: int` field to Bus  
**Handling:**  
- New soft rule: higher priority = lower wait time penalty  
- Objective function includes priority weighting  
- Rule defined in `objective.py`, not in core engine

### 3. Time-of-Day Electricity Costs
**Change:** Add cost per station per time period  
**Handling:**  
- New soft rule: prefer cheaper charging times  
- Load cost matrix from scenario data  
- No engine changes required

### 4. Driver Shifts
**Change:** Add driver availability windows  
**Handling:**  
- New hard constraint: bus must finish before driver shift ends  
- Validator checks shift constraints  
- Data-only configuration

### 5. Multiple Routes
**Change:** Route becomes a named configuration  
**Handling:**  
- `Scenario.route_id` references named route  
- Route library loaded from data  
- No code changes for new routes

### 6. New Operators
**Change:** Add operator to system  
**Handling:**  
- Operator is just a string in `Bus.operator`  
- No code changes needed

### 7. Variable Charging Times
**Change:** Charging time varies by bus type or station  
**Handling:**  
- Add `charging_time: int` to Bus or Station  
- Use in calculations  
- Backward compatible (default to 25 min)

### 8. Dynamic Departures
**Change:** Real-time bus departures  
**Handling:**  
- Replace static scenario file with API endpoint  
- Same data structure, different source

### 9. Multiple Segments Between Stations
**Change:** Route has variable segment distances  
**Handling:**  
- Segment distances are data-driven  
- Already supported in current design

### 10. Route Variants
**Change:** Different route patterns (loop, branch)  
**Handling:**  
- Route definition is flexible list of segments  
- Station ordering derived from route

---

## Changing a Weight

Weights are defined in the `Weights` dataclass within each scenario file:

```python
# In scenario JSON file
{
  "name": "Scenario 4 - Operator-heavy",
  "weights": {
    "individual": 1.0,
    "operator": 2.0,
    "overall": 1.0
  },
  "buses": [...]
}
```

To change weights programmatically:
```python
from scheduler import Weights, Scenario

# Create new weights
new_weights = Weights(individual=0.5, operator=3.0, overall=1.5)

# Apply to scenario
scenario = Scenario(name="custom", buses=buses, weights=new_weights)
```

The weight values are read directly by the objective function in `scheduler/objective.py`.

---

## Adding a New Rule

### Adding a New Soft Rule (Example: Prefer Earlier Charging)

1. **Add the rule in `scheduler/objective.py`:**
```python
def time_of_day_penalty(plan: ChargingPlan, weights: Weights) -> float:
    """Penalty for charging during expensive hours (e.g., 18:00-22:00)."""
    penalty = 0.0
    for stop in plan.stations_used:
        hour = stop.arrival_time.hour
        if 18 <= hour <= 22:
            penalty += 10.0  # Additional cost
    return penalty * weights.time_of_day
```

2. **Update the Weights dataclass:**
```python
@dataclass
class Weights:
    individual: float = 1.0
    operator: float = 1.0
    overall: float = 1.0
    time_of_day: float = 1.0  # New weight
```

3. **Include in total objective:**
```python
def compute_objective(plan: ChargingPlan, weights: Weights) -> float:
    return (
        weights.individual * individual_penalty(plan) +
        weights.operator * operator_penalty(plan) +
        weights.overall * total_time(plan) +
        weights.time_of_day * time_of_day_penalty(plan)
    )
```

No changes to core engine, constraint validator, or UI needed.

---

## Assumptions Made

1. **Speed is constant:** 60 km/h for all buses (derived from 100 km / 100 min segment)
2. **Charging is instantaneous for range calculation:** Bus can start next segment immediately after departure from charger
3. **No boarding/alighting time:** Buses only stop for charging
4. **Deterministic arrival times:** No variability in travel time
5. **Full charge only:** Cannot charge partially; always charges to 240 km range
6. **No charging at endpoints:** Bengaluru and Kochi are not scheduling stations
7. **Wait time includes queueing:** Bus waits from arrival until charger is free
8. **Greedy feasibility first:** Find any valid schedule before optimizing
9. **Minimize sum of wait times:** Individual penalty = sum of bus wait times
10. **Operator grouping:** Buses from same operator should have correlated timelines