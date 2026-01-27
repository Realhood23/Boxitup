"""Component service for searching, creating, and managing components."""
from typing import Optional
from datetime import datetime
from flask import current_app
from flask_login import current_user
import re
import os
import json

from app.models.component import Component, ComponentFeature, FeatureType, COMMON_FEATURES
from app.services.github_service import GitHubService


class ComponentService:
    """
    Service for managing electronic components.

    Uses GitHub as the primary data store, with local caching.
    """

    def __init__(self):
        self._cache = {}
        self._cache_time = None

    def _get_github_service(self) -> GitHubService:
        """Get GitHub service instance.

        Always uses the bot token to avoid rate limits (60/hr unauthenticated vs 5000/hr authenticated).
        """
        token = current_app.config.get('GITHUB_BOT_TOKEN')
        return GitHubService(token)

    def search_components(
        self,
        search: str = '',
        category: str = '',
        limit: int = 50
    ) -> list[Component]:
        """
        Search components by name, description, or manufacturer.

        Args:
            search: Search query string
            category: Filter by category
            limit: Maximum results to return

        Returns:
            List of matching Component objects
        """
        github = self._get_github_service()

        try:
            # Get all components (with caching in production)
            raw_components = github.list_components(category if category else None)
        except Exception:
            # Fallback to sample data if GitHub not configured
            raw_components = self._get_sample_components()

        components = []
        search_lower = search.lower()

        for data in raw_components:
            # Apply search filter
            if search:
                searchable = ' '.join([
                    data.get('name', ''),
                    data.get('description', ''),
                    data.get('manufacturer', ''),
                    data.get('id', '')
                ]).lower()

                if search_lower not in searchable:
                    continue

            # Apply category filter
            if category and data.get('category') != category:
                continue

            try:
                components.append(Component.from_dict(data))
            except Exception:
                continue

            if len(components) >= limit:
                break

        return components

    def get_component(self, component_id: str) -> Optional[Component]:
        """Get a component by ID."""
        github = self._get_github_service()

        try:
            result = github.get_component(component_id)
            if result:
                return Component.from_dict(result['data'])
        except Exception:
            pass

        # Fallback to sample data
        for data in self._get_sample_components():
            if data.get('id') == component_id:
                return Component.from_dict(data)

        return None

    def get_categories(self) -> list[str]:
        """Get list of available component categories."""
        github = self._get_github_service()

        try:
            return github.get_categories()
        except Exception:
            # Fallback categories
            return [
                'microcontrollers',
                'displays',
                'sensors',
                'connectors',
                'power',
                'audio',
                'wireless',
                'storage',
                'other'
            ]

    def create_component_from_form(self, form_data: dict, user) -> Component:
        """
        Create a new component from form data and save to GitHub.

        Args:
            form_data: Form data dict
            user: Current user (for attribution)

        Returns:
            Created Component object
        """
        # Generate ID from name
        component_id = self._generate_id(form_data.get('name', ''))

        # Parse dimensions
        dimensions = {
            'length_mm': float(form_data.get('length_mm', 0)),
            'width_mm': float(form_data.get('width_mm', 0)),
            'height_mm': float(form_data.get('height_mm', 0)),
            'tolerance_mm': float(form_data.get('tolerance_mm', 0.1))
        }

        # Parse features
        features = []
        feature_indices = set()
        for key in form_data.keys():
            if key.startswith('feature_') and '_type' in key:
                idx = key.split('_')[1]
                feature_indices.add(idx)

        for idx in feature_indices:
            prefix = f'feature_{idx}_'
            feature_type = form_data.get(f'{prefix}type')
            if feature_type:
                feature = ComponentFeature(
                    feature_type=FeatureType(feature_type),
                    name=form_data.get(f'{prefix}name', ''),
                    description=form_data.get(f'{prefix}description', ''),
                    position_x_mm=float(form_data.get(f'{prefix}pos_x', 0)),
                    position_y_mm=float(form_data.get(f'{prefix}pos_y', 0)),
                    position_z_mm=float(form_data.get(f'{prefix}pos_z', 0)),
                    hole_width_mm=float(form_data.get(f'{prefix}hole_width', 10)),
                    hole_height_mm=float(form_data.get(f'{prefix}hole_height', 10)),
                    is_circular=form_data.get(f'{prefix}circular') == 'on',
                    corner_radius_mm=float(form_data.get(f'{prefix}corner_radius', 0)),
                    required_face=form_data.get(f'{prefix}face', 'any'),
                    requires_external_access=form_data.get(f'{prefix}external') != 'off'
                )
                features.append(feature)

        # Parse distributors
        distributors = {}
        if form_data.get('digikey_pn'):
            distributors['digikey'] = form_data['digikey_pn']
        if form_data.get('mouser_pn'):
            distributors['mouser'] = form_data['mouser_pn']

        # Create component
        component = Component(
            id=component_id,
            name=form_data.get('name', ''),
            manufacturer=form_data.get('manufacturer', ''),
            category=form_data.get('category', 'other'),
            description=form_data.get('description', ''),
            length_mm=dimensions['length_mm'],
            width_mm=dimensions['width_mm'],
            height_mm=dimensions['height_mm'],
            tolerance_mm=dimensions['tolerance_mm'],
            distributors=distributors,
            features=features,
            mounting_type=form_data.get('mounting_type', 'standoff'),
            datasheet_url=form_data.get('datasheet_url', ''),
            added_by=user.username,
            added_date=datetime.utcnow().strftime('%Y-%m-%d'),
            verified=False
        )

        # Save to GitHub
        self._save_to_github(component, user)

        return component

    def _save_to_github(self, component: Component, user):
        """Save component to GitHub repository using the bot token."""
        github = self._get_github_service()

        if not current_app.config.get('GITHUB_BOT_TOKEN'):
            raise ValueError("GITHUB_BOT_TOKEN not configured - cannot write components")

        # Check if component already exists
        existing = github.get_component(component.id)
        existing_sha = existing['sha'] if existing else None

        # Use the submitting user's info for the commit attribution
        github.save_component(
            component_data=component.to_dict(),
            user_name=user.name or user.username,
            user_email=user.email or f'{user.username}@users.noreply.github.com',
            existing_sha=existing_sha
        )

    def _generate_id(self, name: str) -> str:
        """Generate a URL-safe ID from a name."""
        # Convert to lowercase, replace spaces/special chars with hyphens
        slug = name.lower()
        slug = re.sub(r'[^a-z0-9]+', '-', slug)
        slug = slug.strip('-')
        return slug

    def _get_sample_components(self) -> list[dict]:
        """Get sample components for development/demo."""
        return [
            {
                'id': 'esp32-wroom-32',
                'name': 'ESP32-WROOM-32',
                'manufacturer': 'Espressif',
                'category': 'microcontrollers',
                'description': 'Wi-Fi & Bluetooth MCU Module',
                'dimensions': {
                    'length_mm': 25.5,
                    'width_mm': 18.0,
                    'height_mm': 3.1,
                    'tolerance_mm': 0.15
                },
                'distributors': {
                    'digikey': '1965-ESP32-WROOM-32-ND',
                    'mouser': '356-ESP32-WROOM-32'
                },
                'features': [
                    {
                        'feature_type': 'usb_port',
                        'name': 'Micro USB',
                        'description': 'Programming and power via Micro USB',
                        'position_x_mm': 0,
                        'position_y_mm': 9.0,
                        'position_z_mm': 0,
                        'hole_width_mm': 8.0,
                        'hole_height_mm': 3.5,
                        'is_circular': False,
                        'corner_radius_mm': 0.5,
                        'required_face': 'front',
                        'requires_external_access': True
                    },
                    {
                        'feature_type': 'button',
                        'name': 'Reset Button',
                        'description': 'Reset the ESP32',
                        'position_x_mm': 5.0,
                        'position_y_mm': 2.0,
                        'position_z_mm': 3.0,
                        'hole_width_mm': 3.0,
                        'hole_height_mm': 3.0,
                        'is_circular': True,
                        'required_face': 'top',
                        'requires_external_access': True
                    },
                    {
                        'feature_type': 'button',
                        'name': 'Boot Button',
                        'description': 'Enter bootloader mode',
                        'position_x_mm': 20.0,
                        'position_y_mm': 2.0,
                        'position_z_mm': 3.0,
                        'hole_width_mm': 3.0,
                        'hole_height_mm': 3.0,
                        'is_circular': True,
                        'required_face': 'top',
                        'requires_external_access': True
                    },
                    {
                        'feature_type': 'led_indicator',
                        'name': 'Power LED',
                        'description': 'Power indicator LED',
                        'position_x_mm': 12.0,
                        'position_y_mm': 16.0,
                        'position_z_mm': 3.0,
                        'hole_width_mm': 3.0,
                        'hole_height_mm': 3.0,
                        'is_circular': True,
                        'required_face': 'top',
                        'requires_external_access': True
                    },
                    {
                        'feature_type': 'antenna',
                        'name': 'PCB Antenna',
                        'description': 'Built-in PCB antenna - keep clear of metal',
                        'position_x_mm': 0,
                        'position_y_mm': 0,
                        'position_z_mm': 0,
                        'hole_width_mm': 6.0,
                        'hole_height_mm': 18.0,
                        'required_face': 'any',
                        'requires_external_access': False
                    }
                ],
                'mounting': {
                    'type': 'standoff',
                    'holes': [
                        {'x': 2.5, 'y': 2.5, 'diameter': 2.5},
                        {'x': 23.0, 'y': 2.5, 'diameter': 2.5},
                        {'x': 2.5, 'y': 15.5, 'diameter': 2.5},
                        {'x': 23.0, 'y': 15.5, 'diameter': 2.5}
                    ]
                },
                'keepouts': [
                    {
                        'type': 'antenna',
                        'position': {'x': 0, 'y': 0},
                        'size': {'length': 6.0, 'width': 18.0},
                        'description': 'Keep metal away from antenna area'
                    }
                ],
                'datasheet_url': 'https://www.espressif.com/sites/default/files/documentation/esp32-wroom-32_datasheet_en.pdf',
                'added_by': 'system',
                'added_date': '2026-01-25',
                'verified': True
            },
            {
                'id': 'raspberry-pi-4b',
                'name': 'Raspberry Pi 4 Model B',
                'manufacturer': 'Raspberry Pi Foundation',
                'category': 'microcontrollers',
                'description': 'Quad-core ARM Cortex-A72 single-board computer',
                'dimensions': {
                    'length_mm': 85.0,
                    'width_mm': 56.0,
                    'height_mm': 17.0,
                    'tolerance_mm': 0.5
                },
                'distributors': {
                    'digikey': '1690-RASPBERRY-PI-4B-4GB-ND',
                    'mouser': '358-RPI4-MODBP-4GB'
                },
                'features': [
                    {
                        'feature_type': 'usb_port',
                        'name': 'USB-C Power',
                        'description': 'USB-C power input (5V 3A)',
                        'position_x_mm': 10.6,
                        'position_y_mm': 0,
                        'position_z_mm': 3.5,
                        'hole_width_mm': 9.5,
                        'hole_height_mm': 3.5,
                        'corner_radius_mm': 1.0,
                        'required_face': 'front',
                        'requires_external_access': True
                    },
                    {
                        'feature_type': 'hdmi_port',
                        'name': 'Micro HDMI 0',
                        'description': 'Primary display output',
                        'position_x_mm': 26.0,
                        'position_y_mm': 0,
                        'position_z_mm': 3.5,
                        'hole_width_mm': 7.5,
                        'hole_height_mm': 3.5,
                        'corner_radius_mm': 0.5,
                        'required_face': 'front',
                        'requires_external_access': True
                    },
                    {
                        'feature_type': 'hdmi_port',
                        'name': 'Micro HDMI 1',
                        'description': 'Secondary display output',
                        'position_x_mm': 39.5,
                        'position_y_mm': 0,
                        'position_z_mm': 3.5,
                        'hole_width_mm': 7.5,
                        'hole_height_mm': 3.5,
                        'corner_radius_mm': 0.5,
                        'required_face': 'front',
                        'requires_external_access': True
                    },
                    {
                        'feature_type': 'audio_jack',
                        'name': '3.5mm Audio/Video',
                        'description': 'Composite video and stereo audio',
                        'position_x_mm': 53.5,
                        'position_y_mm': 0,
                        'position_z_mm': 6.0,
                        'hole_width_mm': 7.0,
                        'hole_height_mm': 7.0,
                        'is_circular': True,
                        'required_face': 'front',
                        'requires_external_access': True
                    },
                    {
                        'feature_type': 'usb_port',
                        'name': 'USB 2.0 Ports',
                        'description': 'Dual USB 2.0 ports',
                        'position_x_mm': 85.0,
                        'position_y_mm': 18.0,
                        'position_z_mm': 6.0,
                        'hole_width_mm': 14.0,
                        'hole_height_mm': 16.0,
                        'corner_radius_mm': 1.0,
                        'required_face': 'right',
                        'requires_external_access': True
                    },
                    {
                        'feature_type': 'usb_port',
                        'name': 'USB 3.0 Ports',
                        'description': 'Dual USB 3.0 ports (blue)',
                        'position_x_mm': 85.0,
                        'position_y_mm': 36.0,
                        'position_z_mm': 6.0,
                        'hole_width_mm': 14.0,
                        'hole_height_mm': 16.0,
                        'corner_radius_mm': 1.0,
                        'required_face': 'right',
                        'requires_external_access': True
                    },
                    {
                        'feature_type': 'ethernet_port',
                        'name': 'Gigabit Ethernet',
                        'description': 'RJ45 Gigabit Ethernet',
                        'position_x_mm': 85.0,
                        'position_y_mm': 50.0,
                        'position_z_mm': 6.0,
                        'hole_width_mm': 16.0,
                        'hole_height_mm': 13.5,
                        'corner_radius_mm': 1.0,
                        'required_face': 'right',
                        'requires_external_access': True
                    },
                    {
                        'feature_type': 'gpio_header',
                        'name': '40-pin GPIO',
                        'description': '40-pin GPIO header',
                        'position_x_mm': 7.0,
                        'position_y_mm': 32.5,
                        'position_z_mm': 17.0,
                        'hole_width_mm': 52.0,
                        'hole_height_mm': 6.0,
                        'corner_radius_mm': 1.0,
                        'required_face': 'top',
                        'requires_external_access': True
                    },
                    {
                        'feature_type': 'sd_card_slot',
                        'name': 'MicroSD Slot',
                        'description': 'MicroSD card for boot/storage',
                        'position_x_mm': 0,
                        'position_y_mm': 24.0,
                        'position_z_mm': 1.0,
                        'hole_width_mm': 13.0,
                        'hole_height_mm': 2.5,
                        'corner_radius_mm': 0.5,
                        'required_face': 'left',
                        'requires_external_access': True
                    },
                    {
                        'feature_type': 'led_indicator',
                        'name': 'Activity LED',
                        'description': 'Green activity LED',
                        'position_x_mm': 0,
                        'position_y_mm': 8.0,
                        'position_z_mm': 3.0,
                        'hole_width_mm': 3.0,
                        'hole_height_mm': 3.0,
                        'is_circular': True,
                        'required_face': 'left',
                        'requires_external_access': True
                    },
                    {
                        'feature_type': 'led_indicator',
                        'name': 'Power LED',
                        'description': 'Red power LED',
                        'position_x_mm': 0,
                        'position_y_mm': 4.0,
                        'position_z_mm': 3.0,
                        'hole_width_mm': 3.0,
                        'hole_height_mm': 3.0,
                        'is_circular': True,
                        'required_face': 'left',
                        'requires_external_access': True
                    }
                ],
                'mounting': {
                    'type': 'standoff',
                    'holes': [
                        {'x': 3.5, 'y': 3.5, 'diameter': 2.75},
                        {'x': 61.5, 'y': 3.5, 'diameter': 2.75},
                        {'x': 3.5, 'y': 52.5, 'diameter': 2.75},
                        {'x': 61.5, 'y': 52.5, 'diameter': 2.75}
                    ]
                },
                'datasheet_url': 'https://datasheets.raspberrypi.com/rpi4/raspberry-pi-4-datasheet.pdf',
                'added_by': 'system',
                'added_date': '2026-01-25',
                'verified': True
            },
            {
                'id': 'ssd1306-oled-128x64',
                'name': 'SSD1306 OLED Display 128x64',
                'manufacturer': 'Generic',
                'category': 'displays',
                'description': '0.96" I2C OLED display module',
                'dimensions': {
                    'length_mm': 27.0,
                    'width_mm': 27.0,
                    'height_mm': 4.0,
                    'tolerance_mm': 0.3
                },
                'features': [
                    {
                        'feature_type': 'display',
                        'name': 'OLED Screen',
                        'description': '0.96" 128x64 OLED display',
                        'position_x_mm': 1.5,
                        'position_y_mm': 5.0,
                        'position_z_mm': 1.5,
                        'hole_width_mm': 24.0,
                        'hole_height_mm': 14.0,
                        'corner_radius_mm': 0.5,
                        'required_face': 'top',
                        'requires_external_access': True
                    }
                ],
                'mounting': {
                    'type': 'standoff',
                    'holes': [
                        {'x': 2.0, 'y': 2.0, 'diameter': 2.0},
                        {'x': 25.0, 'y': 2.0, 'diameter': 2.0},
                        {'x': 2.0, 'y': 25.0, 'diameter': 2.0},
                        {'x': 25.0, 'y': 25.0, 'diameter': 2.0}
                    ]
                },
                'added_by': 'system',
                'added_date': '2026-01-25',
                'verified': True
            }
        ]
