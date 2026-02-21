"""
Pydantic models for P&ID equipment and instrument data.

These models define the structure of data extracted from P&ID images
using vision-based extraction.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ============================================================
# Base Equipment and Instrument Models
# ============================================================

class Equipment(BaseModel):
    """Major process equipment (vessels, pumps, compressors, etc.)"""

    tag: str = Field(..., description="Equipment tag number (e.g., V-101)")
    equipment_type: str = Field(default="", description="Type (Separator, Pump, Compressor, etc.)")
    name: str = Field(default="", description="Equipment name/description")
    service: Optional[str] = Field(default=None, description="Service description")

    # Design conditions
    design_pressure: Optional[str] = Field(default=None, description="Design pressure with units")
    design_temperature: Optional[str] = Field(default=None, description="Design temperature with units")

    # Operating conditions
    operating_pressure: Optional[str] = Field(default=None, description="Operating pressure with units")
    operating_temperature: Optional[str] = Field(default=None, description="Operating temperature with units")

    # Physical characteristics
    size: Optional[str] = Field(default=None, description="Size/dimensions")
    capacity: Optional[str] = Field(default=None, description="Capacity with units")
    material: Optional[str] = Field(default=None, description="Material of construction")

    # Additional specs as flexible dict
    additional_specs: Dict[str, Any] = Field(default_factory=dict)


class Instrument(BaseModel):
    """Process instrumentation (transmitters, controllers, valves, etc.)"""

    tag: str = Field(..., description="Instrument tag (e.g., PSV-101, PT-101A)")
    instrument_type: str = Field(default="", description="Type (Pressure Transmitter, Level Controller, etc.)")
    function: str = Field(default="", description="Function (measurement, control, protection)")
    parent_equipment: Optional[str] = Field(default=None, description="Tag of equipment this instrument belongs to")

    # Setpoint and range
    setpoint: Optional[str] = Field(default=None, description="Setpoint value with units")
    range_min: Optional[str] = Field(default=None, description="Minimum range")
    range_max: Optional[str] = Field(default=None, description="Maximum range")

    # Relationship type to parent equipment
    relationship_type: str = Field(
        default="monitors",
        description="Relationship: monitors, controls, protects, indicates"
    )


class Connection(BaseModel):
    """Piping connection between equipment"""

    source_tag: str = Field(..., description="Source equipment tag")
    destination_tag: str = Field(..., description="Destination equipment tag")
    line_number: Optional[str] = Field(default=None, description="Line number (e.g., 4-P-101-A1A)")
    pipe_size: Optional[str] = Field(default=None, description="Pipe size (e.g., 4 inch, 6\"-D)")
    pipe_class: Optional[str] = Field(default=None, description="Piping class (e.g., A, B, D)")
    service: Optional[str] = Field(default=None, description="Service (Oil, Gas, Water)")


class ControlLoop(BaseModel):
    """Control loop information"""

    loop_id: str = Field(..., description="Loop identifier (e.g., LIC-101)")
    controlled_variable: str = Field(default="", description="What is being controlled")
    sensor_tag: Optional[str] = Field(default=None, description="Sensor/transmitter tag")
    controller_tag: Optional[str] = Field(default=None, description="Controller tag")
    final_element_tag: Optional[str] = Field(default=None, description="Final control element tag")
    setpoint: Optional[str] = Field(default=None, description="Control setpoint")


# ============================================================
# Process Flow Diagram (PFD) Extraction Models
# ============================================================

class ProcessStream(BaseModel):
    """Process stream data from PFD"""

    stream_number: str = Field(..., description="Stream number/identifier")
    description: Optional[str] = Field(default=None)
    from_equipment: Optional[str] = Field(default=None)
    to_equipment: Optional[str] = Field(default=None)

    # Stream properties
    flow_rate: Optional[str] = Field(default=None)
    pressure: Optional[str] = Field(default=None)
    temperature: Optional[str] = Field(default=None)
    phase: Optional[str] = Field(default=None, description="gas, liquid, two-phase")

    # Additional properties
    molecular_weight: Optional[str] = Field(default=None)
    density: Optional[str] = Field(default=None)


class PFDExtraction(BaseModel):
    """Extraction result for Process Flow Diagram page"""

    page_type: str = Field(default="PFD")
    facility_name: Optional[str] = Field(default=None)
    drawing_number: Optional[str] = Field(default=None)

    major_equipment: List[Equipment] = Field(default_factory=list)
    process_streams: List[ProcessStream] = Field(default_factory=list)

    # Stream data table (if present)
    stream_table_headers: List[str] = Field(default_factory=list)
    stream_table_data: List[Dict[str, str]] = Field(default_factory=list)

    notes: List[str] = Field(default_factory=list)


# ============================================================
# Legend Sheet Extraction Models
# ============================================================

class InstrumentSymbol(BaseModel):
    """Instrument symbol definition from legend"""

    symbol_code: str = Field(..., description="Symbol code (e.g., PT, LT, PSV)")
    description: str = Field(default="")
    category: Optional[str] = Field(default=None, description="Category: Pressure, Level, Flow, etc.")


class PipingClass(BaseModel):
    """Piping class specification from legend"""

    class_code: str = Field(..., description="Class code (e.g., A, B, D)")
    description: Optional[str] = Field(default=None)
    material: Optional[str] = Field(default=None)
    pressure_rating: Optional[str] = Field(default=None)
    temperature_rating: Optional[str] = Field(default=None)


class LegendExtraction(BaseModel):
    """Extraction result for Legend Sheet page"""

    page_type: str = Field(default="Legend")

    instrument_symbols: List[InstrumentSymbol] = Field(default_factory=list)
    piping_classes: List[PipingClass] = Field(default_factory=list)
    valve_symbols: List[Dict[str, str]] = Field(default_factory=list)
    line_types: List[Dict[str, str]] = Field(default_factory=list)

    general_notes: List[str] = Field(default_factory=list)


# ============================================================
# Detailed P&ID Extraction Models
# ============================================================

class PIDExtraction(BaseModel):
    """Extraction result for detailed P&ID page"""

    page_type: str = Field(default="Detail_PID")
    page_title: Optional[str] = Field(default=None)
    page_number: Optional[int] = Field(default=None)
    drawing_number: Optional[str] = Field(default=None)

    # Primary equipment on this page
    primary_equipment: List[Equipment] = Field(default_factory=list)

    # All instruments visible on this page
    instruments: List[Instrument] = Field(default_factory=list)

    # Piping connections
    piping_connections: List[Connection] = Field(default_factory=list)

    # Control loops
    control_loops: List[ControlLoop] = Field(default_factory=list)

    # References to other sheets
    sheet_references: List[str] = Field(default_factory=list)

    # Extraction metadata
    extraction_status: str = Field(default="success")
    extraction_notes: List[str] = Field(default_factory=list)


# ============================================================
# Document-Level Extraction Result
# ============================================================

class DocumentExtraction(BaseModel):
    """Complete extraction result for an entire P&ID document"""

    document_id: Optional[int] = Field(default=None)
    file_name: str
    total_pages: int

    # Page-level extractions
    pfd_pages: List[PFDExtraction] = Field(default_factory=list)
    legend_pages: List[LegendExtraction] = Field(default_factory=list)
    pid_pages: List[PIDExtraction] = Field(default_factory=list)

    # Consolidated data across all pages
    all_equipment: List[Equipment] = Field(default_factory=list)
    all_instruments: List[Instrument] = Field(default_factory=list)
    all_connections: List[Connection] = Field(default_factory=list)

    # Equipment-instrument relationships
    equipment_instrument_map: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Map of equipment tag to list of instrument tags"
    )
