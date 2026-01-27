"""Component data model with feature toggles for holes and access points."""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import json


class FeatureType(Enum):
    """Types of features that may require holes or access points."""
    POWER_INPUT = "power_input"           # DC barrel jack, USB power, etc.
    USB_PORT = "usb_port"                 # USB data/programming port
    HDMI_PORT = "hdmi_port"               # HDMI output
    ETHERNET_PORT = "ethernet_port"       # RJ45 ethernet
    AUDIO_JACK = "audio_jack"             # 3.5mm audio
    SD_CARD_SLOT = "sd_card_slot"         # SD/microSD access
    ANTENNA = "antenna"                   # External antenna connector
    GPIO_HEADER = "gpio_header"           # Pin header access
    BUTTON = "button"                     # Reset/boot buttons
    LED_INDICATOR = "led_indicator"       # Status LEDs
    DISPLAY = "display"                   # LCD/OLED screen
    SENSOR_WINDOW = "sensor_window"       # Light/IR sensor window
    VENTILATION = "ventilation"           # Heat dissipation
    CABLE_ENTRY = "cable_entry"           # Generic wire passthrough
    MOUNTING_HOLE = "mounting_hole"       # Screw holes on the component
    DEBUG_PORT = "debug_port"             # JTAG/SWD debug access
    SWITCH = "switch"                     # On/off or mode switches
    POTENTIOMETER = "potentiometer"       # Adjustment knobs
    SPEAKER_GRILLE = "speaker_grille"     # Speaker/buzzer output


@dataclass
class ComponentFeature:
    """
    A feature on a component that may require an access hole in the enclosure.

    Users can toggle these on/off when adding components to a project.
    If toggled on, the feature's hole must be placed before generating the script.
    """
    feature_type: FeatureType
    name: str                             # Human-readable name
    description: str                      # What this feature is for

    # Position relative to component origin (bottom-left when viewed from top)
    position_x_mm: float                  # X offset from component origin
    position_y_mm: float                  # Y offset from component origin
    position_z_mm: float                  # Z offset (0 = bottom of component)

    # Dimensions of the required hole/cutout
    hole_width_mm: float                  # Width of required opening
    hole_height_mm: float                 # Height of required opening
    hole_depth_mm: Optional[float] = None  # For recessed features

    # Hole shape
    is_circular: bool = False             # True = circular hole, False = rectangular
    corner_radius_mm: float = 0           # For rounded rectangular holes

    # Placement constraints
    required_face: str = "any"            # "top", "bottom", "front", "back", "left", "right", "any"
    min_clearance_mm: float = 1.0         # Minimum clearance around the hole

    # Whether this feature requires external access (must have hole)
    requires_external_access: bool = True

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'feature_type': self.feature_type.value,
            'name': self.name,
            'description': self.description,
            'position_x_mm': self.position_x_mm,
            'position_y_mm': self.position_y_mm,
            'position_z_mm': self.position_z_mm,
            'hole_width_mm': self.hole_width_mm,
            'hole_height_mm': self.hole_height_mm,
            'hole_depth_mm': self.hole_depth_mm,
            'is_circular': self.is_circular,
            'corner_radius_mm': self.corner_radius_mm,
            'required_face': self.required_face,
            'min_clearance_mm': self.min_clearance_mm,
            'requires_external_access': self.requires_external_access
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ComponentFeature':
        """Create from dictionary."""
        return cls(
            feature_type=FeatureType(data['feature_type']),
            name=data['name'],
            description=data['description'],
            position_x_mm=data['position_x_mm'],
            position_y_mm=data['position_y_mm'],
            position_z_mm=data['position_z_mm'],
            hole_width_mm=data['hole_width_mm'],
            hole_height_mm=data['hole_height_mm'],
            hole_depth_mm=data.get('hole_depth_mm'),
            is_circular=data.get('is_circular', False),
            corner_radius_mm=data.get('corner_radius_mm', 0),
            required_face=data.get('required_face', 'any'),
            min_clearance_mm=data.get('min_clearance_mm', 1.0),
            requires_external_access=data.get('requires_external_access', True)
        )


@dataclass
class Component:
    """
    Electronic component with dimensions and features.

    Components are stored in the GitHub database and include all possible
    features that might need holes. Users enable/disable features per-project.
    """
    id: str                               # Unique identifier (slug)
    name: str                             # Display name
    manufacturer: str
    category: str                         # microcontrollers, displays, sensors, etc.
    description: str

    # Physical dimensions
    length_mm: float                      # X dimension
    width_mm: float                       # Y dimension
    height_mm: float                      # Z dimension
    tolerance_mm: float = 0.1

    # Distributor part numbers for lookup
    distributors: dict = field(default_factory=dict)  # {"digikey": "...", "mouser": "..."}

    # All possible features that might need access holes
    features: list[ComponentFeature] = field(default_factory=list)

    # Mounting information
    mounting_type: str = "standoff"       # standoff, adhesive, snap-in, none
    mounting_holes: list[dict] = field(default_factory=list)  # [{x, y, diameter}]

    # Keep-out zones (areas that need clearance)
    keepouts: list[dict] = field(default_factory=list)

    # Metadata
    datasheet_url: str = ""
    image_url: str = ""
    added_by: str = ""
    added_date: str = ""
    verified: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'manufacturer': self.manufacturer,
            'category': self.category,
            'description': self.description,
            'dimensions': {
                'length_mm': self.length_mm,
                'width_mm': self.width_mm,
                'height_mm': self.height_mm,
                'tolerance_mm': self.tolerance_mm
            },
            'distributors': self.distributors,
            'features': [f.to_dict() for f in self.features],
            'mounting': {
                'type': self.mounting_type,
                'holes': self.mounting_holes
            },
            'keepouts': self.keepouts,
            'datasheet_url': self.datasheet_url,
            'image_url': self.image_url,
            'added_by': self.added_by,
            'added_date': self.added_date,
            'verified': self.verified
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Component':
        """Create from dictionary."""
        dims = data.get('dimensions', {})
        mounting = data.get('mounting', {})

        features = []
        for f_data in data.get('features', []):
            features.append(ComponentFeature.from_dict(f_data))

        return cls(
            id=data['id'],
            name=data['name'],
            manufacturer=data.get('manufacturer', ''),
            category=data.get('category', 'other'),
            description=data.get('description', ''),
            length_mm=dims.get('length_mm', 0),
            width_mm=dims.get('width_mm', 0),
            height_mm=dims.get('height_mm', 0),
            tolerance_mm=dims.get('tolerance_mm', 0.1),
            distributors=data.get('distributors', {}),
            features=features,
            mounting_type=mounting.get('type', 'standoff'),
            mounting_holes=mounting.get('holes', []),
            keepouts=data.get('keepouts', []),
            datasheet_url=data.get('datasheet_url', ''),
            image_url=data.get('image_url', ''),
            added_by=data.get('added_by', ''),
            added_date=data.get('added_date', ''),
            verified=data.get('verified', False)
        )

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'Component':
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))


# Pre-defined common features for quick component creation
COMMON_FEATURES = {
    'usb_micro': ComponentFeature(
        feature_type=FeatureType.USB_PORT,
        name="Micro USB Port",
        description="Micro USB connector for power/data",
        position_x_mm=0, position_y_mm=0, position_z_mm=0,
        hole_width_mm=8.0, hole_height_mm=3.5,
        corner_radius_mm=0.5, required_face="any"
    ),
    'usb_c': ComponentFeature(
        feature_type=FeatureType.USB_PORT,
        name="USB-C Port",
        description="USB Type-C connector",
        position_x_mm=0, position_y_mm=0, position_z_mm=0,
        hole_width_mm=9.5, hole_height_mm=3.5,
        corner_radius_mm=1.0, required_face="any"
    ),
    'dc_barrel_5521': ComponentFeature(
        feature_type=FeatureType.POWER_INPUT,
        name="DC Barrel Jack (5.5x2.1mm)",
        description="Standard DC power input",
        position_x_mm=0, position_y_mm=0, position_z_mm=0,
        hole_width_mm=8.0, hole_height_mm=8.0,
        is_circular=True, required_face="any"
    ),
    'reset_button': ComponentFeature(
        feature_type=FeatureType.BUTTON,
        name="Reset Button",
        description="Tactile reset button",
        position_x_mm=0, position_y_mm=0, position_z_mm=0,
        hole_width_mm=3.0, hole_height_mm=3.0,
        is_circular=True, required_face="top"
    ),
    'status_led': ComponentFeature(
        feature_type=FeatureType.LED_INDICATOR,
        name="Status LED",
        description="Power/status indicator LED",
        position_x_mm=0, position_y_mm=0, position_z_mm=0,
        hole_width_mm=3.0, hole_height_mm=3.0,
        is_circular=True, required_face="top"
    ),
    'sd_card': ComponentFeature(
        feature_type=FeatureType.SD_CARD_SLOT,
        name="MicroSD Card Slot",
        description="MicroSD card access",
        position_x_mm=0, position_y_mm=0, position_z_mm=0,
        hole_width_mm=13.0, hole_height_mm=2.5,
        corner_radius_mm=0.5, required_face="any"
    ),
    'ethernet_rj45': ComponentFeature(
        feature_type=FeatureType.ETHERNET_PORT,
        name="Ethernet (RJ45)",
        description="RJ45 Ethernet connector",
        position_x_mm=0, position_y_mm=0, position_z_mm=0,
        hole_width_mm=16.0, hole_height_mm=13.5,
        corner_radius_mm=1.0, required_face="any"
    ),
    'hdmi_full': ComponentFeature(
        feature_type=FeatureType.HDMI_PORT,
        name="HDMI Port",
        description="Full-size HDMI connector",
        position_x_mm=0, position_y_mm=0, position_z_mm=0,
        hole_width_mm=15.0, hole_height_mm=6.0,
        corner_radius_mm=0.5, required_face="any"
    ),
    'audio_35mm': ComponentFeature(
        feature_type=FeatureType.AUDIO_JACK,
        name="3.5mm Audio Jack",
        description="3.5mm stereo audio connector",
        position_x_mm=0, position_y_mm=0, position_z_mm=0,
        hole_width_mm=6.0, hole_height_mm=6.0,
        is_circular=True, required_face="any"
    ),
    'gpio_header_40': ComponentFeature(
        feature_type=FeatureType.GPIO_HEADER,
        name="40-pin GPIO Header",
        description="2x20 pin header access",
        position_x_mm=0, position_y_mm=0, position_z_mm=0,
        hole_width_mm=52.0, hole_height_mm=6.0,
        corner_radius_mm=1.0, required_face="top"
    ),
    'sma_antenna': ComponentFeature(
        feature_type=FeatureType.ANTENNA,
        name="SMA Antenna Connector",
        description="External antenna SMA connector",
        position_x_mm=0, position_y_mm=0, position_z_mm=0,
        hole_width_mm=8.0, hole_height_mm=8.0,
        is_circular=True, required_face="any"
    ),
}
