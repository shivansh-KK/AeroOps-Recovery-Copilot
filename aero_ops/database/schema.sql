PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS airports (
  icao_code TEXT PRIMARY KEY, iata_code TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
  city TEXT NOT NULL, country TEXT NOT NULL, timezone TEXT NOT NULL,
  curfew_start_utc TEXT, curfew_end_utc TEXT
);
CREATE TABLE IF NOT EXISTS aircraft (
  tail_number TEXT PRIMARY KEY, model TEXT NOT NULL, seating_capacity INTEGER NOT NULL CHECK(seating_capacity > 0),
  status TEXT NOT NULL CHECK(status IN ('AVAILABLE','IN_FLIGHT','MAINTENANCE')),
  min_turnaround_minutes INTEGER NOT NULL CHECK(min_turnaround_minutes > 0)
);
CREATE TABLE IF NOT EXISTS flights (
  flight_number TEXT PRIMARY KEY, tail_number TEXT NOT NULL REFERENCES aircraft(tail_number),
  origin_icao TEXT NOT NULL REFERENCES airports(icao_code), destination_icao TEXT NOT NULL REFERENCES airports(icao_code),
  scheduled_departure_utc TEXT NOT NULL, scheduled_arrival_utc TEXT NOT NULL,
  actual_departure_utc TEXT, actual_arrival_utc TEXT,
  status TEXT NOT NULL CHECK(status IN ('ON_TIME','DELAYED','CANCELLED')),
  gate TEXT, delay_minutes INTEGER NOT NULL DEFAULT 0 CHECK(delay_minutes >= 0)
);
CREATE TABLE IF NOT EXISTS crew_rosters (
  crew_id TEXT PRIMARY KEY, flight_number TEXT NOT NULL REFERENCES flights(flight_number),
  crew_name TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('CAPTAIN','FIRST_OFFICER','CABIN_LEAD')),
  duty_start_utc TEXT NOT NULL, max_duty_hours REAL NOT NULL DEFAULT 14.0 CHECK(max_duty_hours > 0)
);
CREATE TABLE IF NOT EXISTS passengers (
  pnr TEXT PRIMARY KEY, flight_number TEXT NOT NULL REFERENCES flights(flight_number),
  passenger_name TEXT NOT NULL, tier TEXT NOT NULL CHECK(tier IN ('PLATINUM','GOLD','ECONOMY')),
  connecting_flight_number TEXT, connection_time_mins INTEGER
);
CREATE INDEX IF NOT EXISTS idx_flights_route_time ON flights(origin_icao, scheduled_departure_utc);
CREATE INDEX IF NOT EXISTS idx_passengers_flight ON passengers(flight_number);
