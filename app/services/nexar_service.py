"""Nexar/Octopart API service for fetching component data from distributors."""
import re
import requests
from typing import Optional
from flask import current_app
from datetime import datetime


class NexarService:
    """
    Service for fetching electronic component data from Nexar/Octopart API.

    Nexar provides a GraphQL API that aggregates component data from
    DigiKey, Mouser, and other distributors.
    """

    def __init__(self):
        self._token = None
        self._token_expiry = None

    def _get_access_token(self) -> str:
        """Get Nexar OAuth access token."""
        # Check if we have a valid cached token
        if self._token and self._token_expiry:
            if datetime.utcnow() < self._token_expiry:
                return self._token

        client_id = current_app.config.get('NEXAR_CLIENT_ID')
        client_secret = current_app.config.get('NEXAR_CLIENT_SECRET')

        if not client_id or not client_secret:
            raise ValueError("Nexar API credentials not configured")

        # Get token from Nexar identity service
        response = requests.post(
            current_app.config.get('NEXAR_TOKEN_URL'),
            data={
                'grant_type': 'client_credentials',
                'client_id': client_id,
                'client_secret': client_secret
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )

        if response.status_code != 200:
            raise Exception(f"Failed to get Nexar token: {response.text}")

        token_data = response.json()
        self._token = token_data['access_token']

        # Token typically valid for 1 day, cache for slightly less
        from datetime import timedelta
        self._token_expiry = datetime.utcnow() + timedelta(hours=23)

        return self._token

    def _graphql_query(self, query: str, variables: dict = None) -> dict:
        """Execute a GraphQL query against Nexar API."""
        token = self._get_access_token()

        response = requests.post(
            current_app.config.get('NEXAR_API_URL'),
            json={
                'query': query,
                'variables': variables or {}
            },
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
        )

        if response.status_code != 200:
            raise Exception(f"Nexar API error: {response.text}")

        result = response.json()

        if 'errors' in result:
            raise Exception(f"GraphQL errors: {result['errors']}")

        return result.get('data', {})

    def search_components(self, query: str, limit: int = 10) -> list[dict]:
        """
        Search for components by part number or keyword.

        Args:
            query: Search query (part number, description, etc.)
            limit: Maximum results to return

        Returns:
            List of component data dicts
        """
        graphql_query = """
        query SearchParts($q: String!, $limit: Int!) {
            supSearchMpn(q: $q, limit: $limit) {
                hits
                results {
                    part {
                        mpn
                        manufacturer {
                            name
                        }
                        shortDescription
                        descriptions {
                            text
                        }
                        specs {
                            attribute {
                                name
                                shortname
                            }
                            displayValue
                        }
                        bestDatasheet {
                            url
                        }
                        bestImage {
                            url
                        }
                        sellers {
                            company {
                                name
                            }
                            offers {
                                sku
                                inventoryLevel
                                prices {
                                    quantity
                                    price
                                    currency
                                }
                            }
                        }
                    }
                }
            }
        }
        """

        try:
            data = self._graphql_query(graphql_query, {'q': query, 'limit': limit})
            results = data.get('supSearchMpn', {}).get('results', [])
            return [self._parse_part_data(r['part']) for r in results]
        except Exception as e:
            # Log error but don't crash - return empty results
            print(f"Nexar search error: {e}")
            return []

    def get_component_by_mpn(self, mpn: str) -> Optional[dict]:
        """
        Get detailed component data by manufacturer part number.

        Args:
            mpn: Manufacturer part number

        Returns:
            Component data dict or None
        """
        results = self.search_components(mpn, limit=1)
        if results:
            return results[0]
        return None

    def fetch_component_from_url(self, url: str) -> dict:
        """
        Extract component data from a distributor URL.

        Supports DigiKey and Mouser URLs.

        Args:
            url: Distributor product page URL

        Returns:
            Component data dict with extracted information
        """
        # Extract part number from URL
        part_number = self._extract_part_number_from_url(url)

        if not part_number:
            raise ValueError("Could not extract part number from URL")

        # Fetch data from Nexar
        component_data = self.get_component_by_mpn(part_number)

        if not component_data:
            # Return minimal data with just the part number
            return {
                'name': part_number,
                'manufacturer': '',
                'description': '',
                'source_url': url
            }

        component_data['source_url'] = url
        return component_data

    def _extract_part_number_from_url(self, url: str) -> Optional[str]:
        """Extract part number from DigiKey or Mouser URL."""
        # DigiKey URL patterns:
        # https://www.digikey.com/en/products/detail/espressif-systems/ESP32-WROOM-32/8544301
        # https://www.digikey.com/product-detail/en/espressif-systems/ESP32-WROOM-32/1965-1000-ND/8544301

        digikey_patterns = [
            r'digikey\.com/[^/]+/products/detail/[^/]+/([^/]+)/',
            r'digikey\.com/product-detail/[^/]+/[^/]+/([^/]+)/',
            r'digikey\.com/[^/]+/products/detail/([^/]+)',
        ]

        for pattern in digikey_patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        # Mouser URL patterns:
        # https://www.mouser.com/ProductDetail/Espressif-Systems/ESP32-WROOM-32?qs=...

        mouser_patterns = [
            r'mouser\.com/ProductDetail/[^/]+/([^?]+)',
            r'mouser\.com/[^/]+/ProductDetail/([^?]+)',
        ]

        for pattern in mouser_patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        # Try to extract any part number-like string from the URL
        # Part numbers typically have letters, numbers, and dashes
        pn_match = re.search(r'/([A-Z0-9][-A-Z0-9]{4,}[A-Z0-9])', url, re.IGNORECASE)
        if pn_match:
            return pn_match.group(1)

        return None

    def _parse_part_data(self, part: dict) -> dict:
        """Parse Nexar part data into our component format."""
        specs = {}
        for spec in part.get('specs', []):
            attr = spec.get('attribute', {})
            name = attr.get('shortname') or attr.get('name', '')
            value = spec.get('displayValue', '')
            if name and value:
                specs[name.lower().replace(' ', '_')] = value

        # Extract dimensions from specs
        dimensions = self._extract_dimensions(specs)

        # Get distributor info
        distributors = {}
        for seller in part.get('sellers', []):
            company = seller.get('company', {}).get('name', '').lower()
            offers = seller.get('offers', [])
            if offers:
                sku = offers[0].get('sku', '')
                if 'digikey' in company and sku:
                    distributors['digikey'] = sku
                elif 'mouser' in company and sku:
                    distributors['mouser'] = sku

        return {
            'name': part.get('mpn', ''),
            'manufacturer': part.get('manufacturer', {}).get('name', ''),
            'description': part.get('shortDescription', '') or self._get_description(part),
            'dimensions': dimensions,
            'specs': specs,
            'distributors': distributors,
            'datasheet_url': part.get('bestDatasheet', {}).get('url', ''),
            'image_url': part.get('bestImage', {}).get('url', '')
        }

    def _get_description(self, part: dict) -> str:
        """Get best description from part data."""
        descriptions = part.get('descriptions', [])
        if descriptions:
            # Prefer shorter descriptions
            sorted_desc = sorted(descriptions, key=lambda d: len(d.get('text', '')))
            return sorted_desc[0].get('text', '')
        return ''

    def _extract_dimensions(self, specs: dict) -> dict:
        """Extract physical dimensions from component specs."""
        dimensions = {
            'length_mm': 0,
            'width_mm': 0,
            'height_mm': 0,
            'tolerance_mm': 0.1
        }

        # Common spec names for dimensions
        length_keys = ['length', 'package_length', 'body_length', 'l']
        width_keys = ['width', 'package_width', 'body_width', 'w']
        height_keys = ['height', 'thickness', 'package_height', 'h']

        for key in length_keys:
            if key in specs:
                dimensions['length_mm'] = self._parse_dimension(specs[key])
                break

        for key in width_keys:
            if key in specs:
                dimensions['width_mm'] = self._parse_dimension(specs[key])
                break

        for key in height_keys:
            if key in specs:
                dimensions['height_mm'] = self._parse_dimension(specs[key])
                break

        return dimensions

    def _parse_dimension(self, value: str) -> float:
        """Parse a dimension string to float (assuming mm)."""
        if not value:
            return 0

        # Remove units and extract number
        value = value.lower().replace('mm', '').replace('in', '').strip()

        # Handle ranges like "25.5 ~ 26.0"
        if '~' in value:
            parts = value.split('~')
            values = [self._safe_float(p.strip()) for p in parts]
            return sum(values) / len(values) if values else 0

        return self._safe_float(value)

    def _safe_float(self, value: str) -> float:
        """Safely convert string to float."""
        try:
            # Remove any non-numeric characters except . and -
            clean = re.sub(r'[^\d.\-]', '', value)
            return float(clean) if clean else 0
        except (ValueError, TypeError):
            return 0
