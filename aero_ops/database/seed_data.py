"""Generate a deterministic hub-and-spoke operating day with disruption examples."""
from datetime import datetime, timedelta, timezone
from typing import Any

from .db_manager import DatabaseManager

AIRPORTS: tuple[tuple[str, str, str, str, str, str, str | None, str | None], ...] = (
    ("OMDB", "DXB", "Dubai International", "Dubai", "United Arab Emirates", "Asia/Dubai", "22:00", "02:00"),
    ("EGLL", "LHR", "London Heathrow", "London", "United Kingdom", "Europe/London", "23:30", "04:30"),
    ("KJFK", "JFK", "John F. Kennedy International", "New York", "United States", "America/New_York", None, None),
    ("WSSS", "SIN", "Singapore Changi", "Singapore", "Singapore", "Asia/Singapore", None, None),
)
AIRCRAFT = (
    ("A6-EKA", "B777-300ER", 354, "IN_FLIGHT", 60), ("A6-EKB", "A380-800", 489, "IN_FLIGHT", 90),
    ("A6-EKC", "A350-900", 300, "AVAILABLE", 60), ("A6-EKD", "B777-300ER", 354, "AVAILABLE", 60),
    ("A6-EKE", "A380-800", 489, "IN_FLIGHT", 90), ("A6-EKF", "A350-900", 300, "AVAILABLE", 60),
)


def seed_database(db: DatabaseManager, flight_count: int = 36) -> None:
    """Populate operational tables; safe to call repeatedly."""
    with db.transaction() as conn:
        conn.executemany("INSERT OR IGNORE INTO airports VALUES (?,?,?,?,?,?,?,?)", AIRPORTS)
        conn.executemany("INSERT OR IGNORE INTO aircraft VALUES (?,?,?,?,?)", AIRCRAFT)
        base = datetime(2026, 11, 19, 4, tzinfo=timezone.utc)
        flights: list[tuple[Any, ...]] = []
        routes = (("OMDB", "EGLL"), ("EGLL", "OMDB"), ("OMDB", "KJFK"), ("KJFK", "OMDB"),
                  ("OMDB", "WSSS"), ("WSSS", "OMDB"), ("EGLL", "KJFK"), ("KJFK", "EGLL"))
        for index in range(max(32, flight_count)):
            number = "EK001" if index == 0 else f"EK{100 + index:03d}"
            origin, destination = routes[index % len(routes)]
            departure = base + timedelta(minutes=25 * index)
            arrival = departure + timedelta(hours=7 if destination in ("EGLL", "KJFK") else 8)
            tail = AIRCRAFT[index % len(AIRCRAFT)][0]
            delay = 240 if index == 0 else (35 if index == 1 else 0)
            status = "DELAYED" if delay else "ON_TIME"
            flights.append((number, tail, origin, destination, departure.isoformat(), arrival.isoformat(),
                            None, None, status, f"{(index % 30) + 1:02d}A", delay))
        conn.executemany("INSERT OR IGNORE INTO flights VALUES (?,?,?,?,?,?,?,?,?,?,?)", flights)
        crew = []
        passenger_rows = []
        for index in range(max(32, flight_count)):
            flight_number = "EK001" if index == 0 else f"EK{100 + index:03d}"
            duty_start = (base - timedelta(hours=10 if index == 0 else 1)).isoformat()
            for role_index, role in enumerate(("CAPTAIN", "FIRST_OFFICER", "CABIN_LEAD")):
                crew.append((f"C{index:03d}{role_index}", flight_number, f"Crew {index + 1}-{role_index + 1}", role, duty_start, 14.0))
            for passenger_index in range(5):
                tier = ("PLATINUM", "GOLD", "ECONOMY")[passenger_index % 3]
                connection = "EK001" if index % 4 == 0 else None
                passenger_rows.append((f"P{index:03d}{passenger_index}", flight_number, f"Passenger {index + 1}-{passenger_index + 1}", tier, connection, 45 if connection else None))
        conn.executemany("INSERT OR IGNORE INTO crew_rosters VALUES (?,?,?,?,?,?)", crew)
        conn.executemany("INSERT OR IGNORE INTO passengers VALUES (?,?,?,?,?,?)", passenger_rows)


if __name__ == "__main__":
    database = DatabaseManager()
    seed_database(database)
    print(f"Seeded {len(database.query('SELECT flight_number FROM flights'))} flights")
