"""Domain errors raised by tools and operational safety checks."""


class AeroOpsError(Exception):
    """Base error for recoverable AeroOps domain failures."""


class AviationSafetyViolation(AeroOpsError):
    """A proposed operational action violates a hard safety constraint."""


class ToolExecutionError(AeroOpsError):
    """A tool could not safely execute the requested operation."""


class InvalidAirportCodeError(AeroOpsError):
    """An airport code could not be resolved to a known airport."""
