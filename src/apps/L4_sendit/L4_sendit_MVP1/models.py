# Simple data structures for the L4 sendit MVP1 declaration pipeline.

from dataclasses import dataclass


@dataclass(frozen=True)
# Represent shipment fields parsed from the operational command.
class ShipmentCommand:
    sender_identifier: str
    origin_point: str
    destination_point: str
    weight_kg: int
    budget_pp: int
    contents: str
    special_notes: str


@dataclass(frozen=True)
# Represent manually confirmed facts used by the deterministic Stage 1.
class StaticFacts:
    route_code: str
    route_status: str
    disabled_route_exception: str
    category: str
    category_reason: str
    amount_due_pp: int
    amount_due_reason: str
    standard_capacity_kg: int
    additional_wagon_capacity_kg: int
    wdp_meaning: str
    wdp_uncertainty: str
    evidence: dict[str, str]


@dataclass(frozen=True)
# Represent the values rendered into the SPK declaration template.
class DeclarationData:
    declaration_date: str
    sender_identifier: str
    origin_point: str
    destination_point: str
    route_code: str
    category: str
    contents: str
    declared_weight_kg: int
    wdp: int
    special_notes: str
    amount_due_pp: int


@dataclass(frozen=True)
# Represent additional wagon calculation values for learning reports.
class WagonCalculation:
    shipment_weight_kg: int
    standard_capacity_kg: int
    remaining_weight_kg: int
    additional_wagon_capacity_kg: int
    physical_additional_wagons: int
    total_physical_wagons: int


@dataclass(frozen=True)
# Represent one local validation result shown in the run report.
class ValidationResult:
    status: str
    message: str
