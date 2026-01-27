# Enclosure Generator Component Database

This repository contains electronic component definitions for the [Enclosure Generator](https://github.com/your-username/enclosure-generator) web application.

## Structure

```
components-db/
├── components/
│   ├── microcontrollers/    # ESP32, Arduino, Raspberry Pi, etc.
│   ├── displays/            # OLED, LCD, TFT screens
│   ├── sensors/             # Temperature, motion, light sensors
│   ├── connectors/          # USB hubs, terminal blocks
│   ├── power/               # Buck converters, battery holders
│   ├── audio/               # Speakers, amplifiers
│   ├── wireless/            # LoRa, Zigbee, Bluetooth modules
│   ├── storage/             # SD card modules
│   └── other/               # Miscellaneous
├── packages/                # Standard package definitions (SOIC, QFP, etc.)
└── schema/
    └── component-schema.json
```

## Component JSON Format

Each component is a JSON file with the following structure:

```json
{
  "id": "component-slug",
  "name": "Component Display Name",
  "manufacturer": "Manufacturer Name",
  "category": "microcontrollers",
  "description": "Brief description",
  "dimensions": {
    "length_mm": 25.5,
    "width_mm": 18.0,
    "height_mm": 3.1,
    "tolerance_mm": 0.15
  },
  "features": [
    {
      "feature_type": "usb_port",
      "name": "Micro USB",
      "description": "Programming and power",
      "position_x_mm": 0,
      "position_y_mm": 9.0,
      "position_z_mm": 0,
      "hole_width_mm": 8.0,
      "hole_height_mm": 3.5,
      "required_face": "front"
    }
  ],
  "mounting": {
    "type": "standoff",
    "holes": [
      {"x": 2.5, "y": 2.5, "diameter": 2.5}
    ]
  }
}
```

## Contributing

1. Fork this repository
2. Create a new JSON file in the appropriate category folder
3. Ensure your component follows the schema in `schema/component-schema.json`
4. Submit a pull request

### Measurement Guidelines

- Use **millimeters** for all dimensions
- Measure with digital calipers when possible
- Include tolerance based on manufacturing specs (typically 0.1-0.5mm)
- Position (0,0) is the bottom-left corner when viewing the component from above
- Z position is measured from the bottom of the component

### Feature Types

| Type | Description |
|------|-------------|
| `power_input` | DC barrel jack, screw terminals |
| `usb_port` | USB-A, USB-B, Micro, Mini, Type-C |
| `hdmi_port` | HDMI, Mini HDMI, Micro HDMI |
| `ethernet_port` | RJ45 connectors |
| `audio_jack` | 3.5mm, 2.5mm audio |
| `sd_card_slot` | SD, MicroSD |
| `antenna` | External antenna connectors, PCB antennas |
| `gpio_header` | Pin headers for GPIO |
| `button` | Reset, boot, user buttons |
| `led_indicator` | Status LEDs |
| `display` | Screen/display window |
| `sensor_window` | Light/IR sensor openings |
| `ventilation` | Heat dissipation areas |
| `cable_entry` | Wire passthrough |

## License

This component database is released under CC0 (Public Domain). Use freely.
