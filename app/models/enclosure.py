"""Enclosure configuration model with holes, ventilation, and customization options."""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import json
import uuid


class EnclosureShape(Enum):
    """Available enclosure shapes."""
    BOX = "box"                           # Standard rectangular box
    ROUNDED_BOX = "rounded_box"           # Box with rounded corners
    CYLINDER = "cylinder"                 # Cylindrical enclosure
    HEXAGON = "hexagon"                   # Hexagonal prism


class LidType(Enum):
    """Lid attachment methods."""
    NONE = "none"                         # No lid (open top)
    SNAP_FIT = "snap_fit"                 # Snap-on lid with clips
    SCREW_MOUNT = "screw_mount"           # Screws in corners
    SLIDING = "sliding"                   # Slides on from side
    HINGED = "hinged"                     # Hinged lid (one side attached)
    PRESS_FIT = "press_fit"               # Friction fit lid


class HoleType(Enum):
    """Types of holes/cutouts in the enclosure."""
    COMPONENT_ACCESS = "component_access"  # For USB, power, etc.
    VENTILATION = "ventilation"           # Heat dissipation
    CABLE_ENTRY = "cable_entry"           # Wire passthrough
    MOUNTING = "mounting"                 # Screw holes for mounting enclosure
    DISPLAY_WINDOW = "display_window"     # LCD/OLED cutout
    BUTTON_ACCESS = "button_access"       # For pressing buttons
    LED_WINDOW = "led_window"             # For status LEDs
    CUSTOM = "custom"                     # User-defined


class VentPattern(Enum):
    """Ventilation hole patterns."""
    GRID = "grid"                         # Grid of circular holes
    SLOTS = "slots"                       # Parallel slots
    HONEYCOMB = "honeycomb"               # Hexagonal pattern
    LOUVERS = "louvers"                   # Angled louvers
    CUSTOM = "custom"                     # User-defined pattern


@dataclass
class Hole:
    """
    A hole or cutout in the enclosure.

    Holes are placed by the user in the visualization editor.
    They can be linked to component features or added independently.
    """
    id: str
    hole_type: HoleType
    name: str                             # User-friendly name

    # Position on enclosure face
    face: str                             # "top", "bottom", "front", "back", "left", "right"
    position_x_mm: float                  # Position on face (from left)
    position_y_mm: float                  # Position on face (from bottom)

    # Dimensions
    width_mm: float
    height_mm: float
    depth_mm: Optional[float] = None      # For partial-depth cutouts

    # Shape
    is_circular: bool = False
    corner_radius_mm: float = 0

    # Optional link to component feature
    linked_component_id: Optional[str] = None
    linked_feature_id: Optional[str] = None

    # For countersunk/counterbored holes
    countersink_diameter_mm: Optional[float] = None
    countersink_depth_mm: Optional[float] = None

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'hole_type': self.hole_type.value,
            'name': self.name,
            'face': self.face,
            'position_x_mm': self.position_x_mm,
            'position_y_mm': self.position_y_mm,
            'width_mm': self.width_mm,
            'height_mm': self.height_mm,
            'depth_mm': self.depth_mm,
            'is_circular': self.is_circular,
            'corner_radius_mm': self.corner_radius_mm,
            'linked_component_id': self.linked_component_id,
            'linked_feature_id': self.linked_feature_id,
            'countersink_diameter_mm': self.countersink_diameter_mm,
            'countersink_depth_mm': self.countersink_depth_mm
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Hole':
        return cls(
            id=data.get('id', ''),
            hole_type=HoleType(data['hole_type']),
            name=data['name'],
            face=data['face'],
            position_x_mm=data['position_x_mm'],
            position_y_mm=data['position_y_mm'],
            width_mm=data['width_mm'],
            height_mm=data['height_mm'],
            depth_mm=data.get('depth_mm'),
            is_circular=data.get('is_circular', False),
            corner_radius_mm=data.get('corner_radius_mm', 0),
            linked_component_id=data.get('linked_component_id'),
            linked_feature_id=data.get('linked_feature_id'),
            countersink_diameter_mm=data.get('countersink_diameter_mm'),
            countersink_depth_mm=data.get('countersink_depth_mm')
        )


@dataclass
class VentilationZone:
    """A ventilation area with pattern of holes."""
    id: str
    name: str
    face: str                             # Which face of enclosure

    # Position and size of vent zone
    position_x_mm: float
    position_y_mm: float
    width_mm: float
    height_mm: float

    # Pattern configuration
    pattern: VentPattern = VentPattern.GRID
    hole_diameter_mm: float = 3.0         # For grid/honeycomb
    hole_spacing_mm: float = 5.0          # Center-to-center
    slot_width_mm: float = 2.0            # For slots
    slot_length_mm: float = 15.0
    louver_angle_deg: float = 45.0        # For louvers

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'face': self.face,
            'position_x_mm': self.position_x_mm,
            'position_y_mm': self.position_y_mm,
            'width_mm': self.width_mm,
            'height_mm': self.height_mm,
            'pattern': self.pattern.value,
            'hole_diameter_mm': self.hole_diameter_mm,
            'hole_spacing_mm': self.hole_spacing_mm,
            'slot_width_mm': self.slot_width_mm,
            'slot_length_mm': self.slot_length_mm,
            'louver_angle_deg': self.louver_angle_deg
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'VentilationZone':
        return cls(
            id=data.get('id', ''),
            name=data['name'],
            face=data['face'],
            position_x_mm=data['position_x_mm'],
            position_y_mm=data['position_y_mm'],
            width_mm=data['width_mm'],
            height_mm=data['height_mm'],
            pattern=VentPattern(data.get('pattern', 'grid')),
            hole_diameter_mm=data.get('hole_diameter_mm', 3.0),
            hole_spacing_mm=data.get('hole_spacing_mm', 5.0),
            slot_width_mm=data.get('slot_width_mm', 2.0),
            slot_length_mm=data.get('slot_length_mm', 15.0),
            louver_angle_deg=data.get('louver_angle_deg', 45.0)
        )


@dataclass
class TextLabel:
    """Embossed or engraved text on enclosure."""
    id: str
    text: str
    face: str
    position_x_mm: float
    position_y_mm: float
    font_size_mm: float = 5.0
    depth_mm: float = 0.5                 # Positive = embossed, negative = engraved
    font: str = "Liberation Sans"
    rotation_deg: float = 0

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'text': self.text,
            'face': self.face,
            'position_x_mm': self.position_x_mm,
            'position_y_mm': self.position_y_mm,
            'font_size_mm': self.font_size_mm,
            'depth_mm': self.depth_mm,
            'font': self.font,
            'rotation_deg': self.rotation_deg
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'TextLabel':
        return cls(
            id=data.get('id', ''),
            text=data['text'],
            face=data['face'],
            position_x_mm=data['position_x_mm'],
            position_y_mm=data['position_y_mm'],
            font_size_mm=data.get('font_size_mm', 5.0),
            depth_mm=data.get('depth_mm', 0.5),
            font=data.get('font', 'Liberation Sans'),
            rotation_deg=data.get('rotation_deg', 0)
        )


@dataclass
class MountingEar:
    """Mounting ears/flanges for attaching enclosure to surfaces."""
    id: str
    position: str                         # "corner_tl", "corner_tr", "corner_bl", "corner_br", "side_*"
    width_mm: float = 10.0
    length_mm: float = 15.0
    hole_diameter_mm: float = 4.0         # Mounting hole
    thickness_mm: Optional[float] = None  # If different from wall

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'position': self.position,
            'width_mm': self.width_mm,
            'length_mm': self.length_mm,
            'hole_diameter_mm': self.hole_diameter_mm,
            'thickness_mm': self.thickness_mm
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'MountingEar':
        return cls(
            id=data.get('id', ''),
            position=data['position'],
            width_mm=data.get('width_mm', 10.0),
            length_mm=data.get('length_mm', 15.0),
            hole_diameter_mm=data.get('hole_diameter_mm', 4.0),
            thickness_mm=data.get('thickness_mm')
        )


@dataclass
class Enclosure:
    """
    Complete enclosure configuration.

    This defines the box shape, dimensions, holes, ventilation,
    and all customization options.
    """
    # Basic dimensions
    inner_length_mm: float                # X dimension (interior)
    inner_width_mm: float                 # Y dimension (interior)
    inner_height_mm: float                # Z dimension (interior)

    # Shape and style
    shape: EnclosureShape = EnclosureShape.BOX
    corner_radius_mm: float = 0           # For rounded shapes
    wall_thickness_mm: float = 2.0
    bottom_thickness_mm: float = 2.0

    # Lid configuration
    lid_type: LidType = LidType.SNAP_FIT
    lid_thickness_mm: float = 2.0
    lid_clearance_mm: float = 0.2         # Gap for fit
    lid_overlap_mm: float = 2.0           # How much lid overlaps walls

    # For screw-mount lids
    lid_screw_diameter_mm: float = 3.0
    lid_screw_positions: list[dict] = field(default_factory=list)  # [{x, y}]

    # Holes and cutouts (user-placed)
    holes: list[Hole] = field(default_factory=list)

    # Ventilation zones
    ventilation_zones: list[VentilationZone] = field(default_factory=list)

    # Text labels
    labels: list[TextLabel] = field(default_factory=list)

    # Mounting
    mounting_ears: list[MountingEar] = field(default_factory=list)

    # Internal features
    standoff_positions: list[dict] = field(default_factory=list)  # [{x, y, height, diameter}]
    cable_channels: list[dict] = field(default_factory=list)      # Internal cable routing

    # Print settings hints
    suggested_layer_height_mm: float = 0.2
    suggested_infill_percent: int = 20
    needs_supports: bool = False

    def to_dict(self) -> dict:
        return {
            'dimensions': {
                'inner_length_mm': self.inner_length_mm,
                'inner_width_mm': self.inner_width_mm,
                'inner_height_mm': self.inner_height_mm
            },
            'shape': self.shape.value,
            'corner_radius_mm': self.corner_radius_mm,
            'wall_thickness_mm': self.wall_thickness_mm,
            'bottom_thickness_mm': self.bottom_thickness_mm,
            'lid': {
                'type': self.lid_type.value,
                'thickness_mm': self.lid_thickness_mm,
                'clearance_mm': self.lid_clearance_mm,
                'overlap_mm': self.lid_overlap_mm,
                'screw_diameter_mm': self.lid_screw_diameter_mm,
                'screw_positions': self.lid_screw_positions
            },
            'holes': [h.to_dict() for h in self.holes],
            'ventilation_zones': [v.to_dict() for v in self.ventilation_zones],
            'labels': [l.to_dict() for l in self.labels],
            'mounting_ears': [m.to_dict() for m in self.mounting_ears],
            'standoff_positions': self.standoff_positions,
            'cable_channels': self.cable_channels,
            'print_hints': {
                'suggested_layer_height_mm': self.suggested_layer_height_mm,
                'suggested_infill_percent': self.suggested_infill_percent,
                'needs_supports': self.needs_supports
            }
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Enclosure':
        dims = data.get('dimensions', {})
        lid = data.get('lid', {})
        hints = data.get('print_hints', {})

        holes = [Hole.from_dict(h) for h in data.get('holes', [])]
        vents = [VentilationZone.from_dict(v) for v in data.get('ventilation_zones', [])]
        labels = [TextLabel.from_dict(l) for l in data.get('labels', [])]
        ears = [MountingEar.from_dict(m) for m in data.get('mounting_ears', [])]

        return cls(
            inner_length_mm=dims.get('inner_length_mm', 100),
            inner_width_mm=dims.get('inner_width_mm', 60),
            inner_height_mm=dims.get('inner_height_mm', 30),
            shape=EnclosureShape(data.get('shape', 'box')),
            corner_radius_mm=data.get('corner_radius_mm', 0),
            wall_thickness_mm=data.get('wall_thickness_mm', 2.0),
            bottom_thickness_mm=data.get('bottom_thickness_mm', 2.0),
            lid_type=LidType(lid.get('type', 'snap_fit')),
            lid_thickness_mm=lid.get('thickness_mm', 2.0),
            lid_clearance_mm=lid.get('clearance_mm', 0.2),
            lid_overlap_mm=lid.get('overlap_mm', 2.0),
            lid_screw_diameter_mm=lid.get('screw_diameter_mm', 3.0),
            lid_screw_positions=lid.get('screw_positions', []),
            holes=holes,
            ventilation_zones=vents,
            labels=labels,
            mounting_ears=ears,
            standoff_positions=data.get('standoff_positions', []),
            cable_channels=data.get('cable_channels', []),
            suggested_layer_height_mm=hints.get('suggested_layer_height_mm', 0.2),
            suggested_infill_percent=hints.get('suggested_infill_percent', 20),
            needs_supports=hints.get('needs_supports', False)
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'Enclosure':
        return cls.from_dict(json.loads(json_str))

    def get_outer_dimensions(self) -> tuple[float, float, float]:
        """Calculate outer dimensions including walls."""
        return (
            self.inner_length_mm + 2 * self.wall_thickness_mm,
            self.inner_width_mm + 2 * self.wall_thickness_mm,
            self.inner_height_mm + self.bottom_thickness_mm + self.lid_thickness_mm
        )

    def add_hole(self, hole: Hole):
        """Add a hole to the enclosure."""
        self.holes.append(hole)

    def remove_hole(self, hole_id: str):
        """Remove a hole by ID."""
        self.holes = [h for h in self.holes if h.id != hole_id]

    def get_holes_by_face(self, face: str) -> list[Hole]:
        """Get all holes on a specific face."""
        return [h for h in self.holes if h.face == face]

    def auto_size_for_components(self, components: list, padding_mm: float = 5.0):
        """
        Automatically calculate enclosure size based on component dimensions.

        Args:
            components: List of (component, position_x, position_y) tuples
            padding_mm: Extra space around components
        """
        if not components:
            return

        max_x = 0
        max_y = 0
        max_z = 0

        for comp, pos_x, pos_y in components:
            max_x = max(max_x, pos_x + comp.length_mm)
            max_y = max(max_y, pos_y + comp.width_mm)
            max_z = max(max_z, comp.height_mm)

        self.inner_length_mm = max_x + 2 * padding_mm
        self.inner_width_mm = max_y + 2 * padding_mm
        self.inner_height_mm = max_z + padding_mm

    def suggest_hole_placements(self, project_components: list) -> list[dict]:
        """
        Suggest optimal hole placements based on component features.

        Returns list of suggested holes that user can accept or modify.
        """
        suggestions = []

        for pc in project_components:
            for feat in pc.enabled_features:
                if feat.enabled and not feat.hole_placed:
                    # Calculate suggested position based on component position
                    # and feature's relative position
                    suggestion = {
                        'component_id': pc.id,
                        'feature_id': feat.feature_id,
                        'feature_name': feat.feature_name,
                        'suggested_face': 'front',  # Would calculate based on feature
                        'suggested_x': pc.position_x_mm,
                        'suggested_y': pc.position_y_mm,
                        'reason': f"Auto-suggested for {feat.feature_name}"
                    }
                    suggestions.append(suggestion)

        return suggestions
