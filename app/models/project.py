"""Project model - a collection of components with their placements and feature toggles."""
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
import json
import uuid


@dataclass
class EnabledFeature:
    """
    A feature that the user has enabled for a component in their project.
    Tracks whether the required hole has been placed.
    """
    feature_id: str                       # References ComponentFeature
    feature_name: str                     # For display
    enabled: bool = True                  # User can toggle on/off
    hole_placed: bool = False             # Has the user placed this hole?
    hole_id: Optional[str] = None         # Reference to placed hole in enclosure

    def to_dict(self) -> dict:
        return {
            'feature_id': self.feature_id,
            'feature_name': self.feature_name,
            'enabled': self.enabled,
            'hole_placed': self.hole_placed,
            'hole_id': self.hole_id
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'EnabledFeature':
        return cls(
            feature_id=data['feature_id'],
            feature_name=data['feature_name'],
            enabled=data.get('enabled', True),
            hole_placed=data.get('hole_placed', False),
            hole_id=data.get('hole_id')
        )


@dataclass
class ProjectComponent:
    """
    A component instance within a project, with position and enabled features.

    Users can:
    - Position the component in the enclosure (x, y, z)
    - Rotate the component
    - Toggle which features need holes (power, USB, etc.)
    - Select from dropdown how many of each hole type
    """
    id: str                               # Unique instance ID
    component_id: str                     # Reference to base Component
    component_name: str                   # For display

    # Position within enclosure (relative to enclosure origin)
    position_x_mm: float = 0
    position_y_mm: float = 0
    position_z_mm: float = 0              # Usually 0 (sitting on bottom)

    # Rotation (degrees, around Z axis)
    rotation_deg: float = 0

    # Features with user toggles
    enabled_features: list[EnabledFeature] = field(default_factory=list)

    # Quantity of each feature type (for components with multiple of same feature)
    feature_quantities: dict = field(default_factory=dict)  # {feature_id: count}

    # Mounting preference for this instance
    use_standoffs: bool = True
    standoff_height_mm: float = 3.0

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'component_id': self.component_id,
            'component_name': self.component_name,
            'position': {
                'x_mm': self.position_x_mm,
                'y_mm': self.position_y_mm,
                'z_mm': self.position_z_mm
            },
            'rotation_deg': self.rotation_deg,
            'enabled_features': [f.to_dict() for f in self.enabled_features],
            'feature_quantities': self.feature_quantities,
            'mounting': {
                'use_standoffs': self.use_standoffs,
                'standoff_height_mm': self.standoff_height_mm
            }
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ProjectComponent':
        pos = data.get('position', {})
        mounting = data.get('mounting', {})

        enabled_features = []
        for f_data in data.get('enabled_features', []):
            enabled_features.append(EnabledFeature.from_dict(f_data))

        return cls(
            id=data['id'],
            component_id=data['component_id'],
            component_name=data.get('component_name', ''),
            position_x_mm=pos.get('x_mm', 0),
            position_y_mm=pos.get('y_mm', 0),
            position_z_mm=pos.get('z_mm', 0),
            rotation_deg=data.get('rotation_deg', 0),
            enabled_features=enabled_features,
            feature_quantities=data.get('feature_quantities', {}),
            use_standoffs=mounting.get('use_standoffs', True),
            standoff_height_mm=mounting.get('standoff_height_mm', 3.0)
        )

    def get_unplaced_required_features(self) -> list[EnabledFeature]:
        """Get list of enabled features that don't have holes placed yet."""
        return [f for f in self.enabled_features if f.enabled and not f.hole_placed]

    def all_required_holes_placed(self) -> bool:
        """Check if all enabled features have their holes placed."""
        return len(self.get_unplaced_required_features()) == 0


@dataclass
class Project:
    """
    A user's enclosure project containing components and configuration.

    The project tracks:
    - All components and their positions
    - Which features are enabled (need holes)
    - Whether all required holes have been placed
    - Enclosure configuration
    """
    id: str
    name: str
    description: str = ""
    user_id: str = ""

    # Components in this project
    components: list[ProjectComponent] = field(default_factory=list)

    # Enclosure configuration (reference to Enclosure model)
    enclosure_config: Optional[dict] = None

    # Metadata
    created_at: str = ""
    updated_at: str = ""

    # Generation state
    ready_to_generate: bool = False       # True when all required holes placed

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()
        self.updated_at = datetime.utcnow().isoformat()

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'user_id': self.user_id,
            'components': [c.to_dict() for c in self.components],
            'enclosure_config': self.enclosure_config,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'ready_to_generate': self.ready_to_generate
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Project':
        components = []
        for c_data in data.get('components', []):
            components.append(ProjectComponent.from_dict(c_data))

        return cls(
            id=data.get('id', ''),
            name=data['name'],
            description=data.get('description', ''),
            user_id=data.get('user_id', ''),
            components=components,
            enclosure_config=data.get('enclosure_config'),
            created_at=data.get('created_at', ''),
            updated_at=data.get('updated_at', ''),
            ready_to_generate=data.get('ready_to_generate', False)
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'Project':
        return cls.from_dict(json.loads(json_str))

    def add_component(self, component_id: str, component_name: str,
                     features: list[dict] = None) -> ProjectComponent:
        """Add a component to the project with default feature states."""
        pc = ProjectComponent(
            id=str(uuid.uuid4()),
            component_id=component_id,
            component_name=component_name
        )

        # Initialize enabled features from component's features
        if features:
            for feat in features:
                ef = EnabledFeature(
                    feature_id=feat.get('feature_type', ''),
                    feature_name=feat.get('name', ''),
                    enabled=feat.get('requires_external_access', True),
                    hole_placed=False
                )
                pc.enabled_features.append(ef)

        self.components.append(pc)
        self._update_ready_state()
        return pc

    def remove_component(self, component_instance_id: str):
        """Remove a component from the project."""
        self.components = [c for c in self.components if c.id != component_instance_id]
        self._update_ready_state()

    def get_all_unplaced_features(self) -> list[tuple[ProjectComponent, EnabledFeature]]:
        """Get all enabled features across all components that need holes placed."""
        unplaced = []
        for comp in self.components:
            for feat in comp.get_unplaced_required_features():
                unplaced.append((comp, feat))
        return unplaced

    def _update_ready_state(self):
        """Update ready_to_generate based on whether all holes are placed."""
        self.ready_to_generate = len(self.get_all_unplaced_features()) == 0
        self.updated_at = datetime.utcnow().isoformat()

    def mark_feature_hole_placed(self, component_id: str, feature_id: str, hole_id: str):
        """Mark a feature's hole as placed."""
        for comp in self.components:
            if comp.id == component_id:
                for feat in comp.enabled_features:
                    if feat.feature_id == feature_id:
                        feat.hole_placed = True
                        feat.hole_id = hole_id
                        break
                break
        self._update_ready_state()

    def validate_for_generation(self) -> tuple[bool, list[str]]:
        """
        Validate the project is ready for OpenSCAD generation.

        Returns:
            (is_valid, list_of_issues)
        """
        issues = []

        # Check all required holes are placed
        unplaced = self.get_all_unplaced_features()
        for comp, feat in unplaced:
            issues.append(
                f"Missing hole for '{feat.feature_name}' on '{comp.component_name}'"
            )

        # Check enclosure is configured
        if not self.enclosure_config:
            issues.append("Enclosure configuration is missing")

        # Check at least one component
        if not self.components:
            issues.append("Project has no components")

        return (len(issues) == 0, issues)
