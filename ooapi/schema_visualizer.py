#!/usr/bin/env python3
"""
JSON Schema Visualizer
Converts YAML JSON Schema to a table format showing structure, types, and properties.
Supports recursive parsing, references ($ref), and imports.

Drafted by Claude and ajusted by Colin Tück
"""

import yaml
import json
import csv
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
import urllib.parse
import argparse
from dataclasses import dataclass


@dataclass
class SchemaProperty:
    """Represents a property in the JSON Schema"""
    path: str
    name: str
    data_type: str
    cardinality: str
    description: str


class JSONSchemaVisualizer:
    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = base_path or Path.cwd()
        self.resolved_refs: Set[str] = set()
        self.schema_cache: Dict[str, Dict] = {}
        self.properties: List[SchemaProperty] = []

    def load_schema(self, file_path: str) -> Dict[str, Any]:
        """Load schema from YAML or JSON file"""
        path = Path(file_path)
        if not path.is_absolute():
            path = self.base_path / path

        # Cache check
        cache_key = str(path.resolve())
        if cache_key in self.schema_cache:
            return self.schema_cache[cache_key]

        try:
            with open(path, 'r', encoding='utf-8') as f:
                if path.suffix.lower() in ['.yaml', '.yml']:
                    schema = yaml.safe_load(f)
                else:
                    schema = json.load(f)

            self.schema_cache[cache_key] = schema
            return schema

        except FileNotFoundError:
            print(f"Warning: Could not find file: {path}")
            return {}
        except Exception as e:
            print(f"Warning: Error loading {path}: {e}")
            return {}

    def resolve_reference(self, ref: str, current_schema: Dict[str, Any], current_path: Path) -> Dict[str, Any]:
        """Resolve $ref references"""
        if ref in self.resolved_refs:
            return {"type": "object", "description": f"Circular reference to {ref}"}

        self.resolved_refs.add(ref)

        try:
            if ref.startswith('#/'):
                # Internal reference
                parts = ref[2:].split('/')
                result = current_schema
                for part in parts:
                    if isinstance(result, dict) and part in result:
                        result = result[part]
                    else:
                        return {"type": "unknown", "description": f"Unresolved reference: {ref}"}
                return result

            elif ref.startswith('http'):
                # HTTP reference - not implemented for security
                return {"type": "external", "description": f"External reference: {ref}"}

            else:
                # File reference
                if '#/' in ref:
                    file_part, fragment = ref.split('#/', 1)
                    schema = self.load_schema(str(current_path.parent / file_part))
                    parts = fragment.split('/')
                    result = schema
                    for part in parts:
                        if isinstance(result, dict) and part in result:
                            result = result[part]
                        else:
                            return {"type": "unknown", "description": f"Unresolved reference: {ref}"}
                    return result
                else:
                    # Whole file reference
                    return self.load_schema(str(current_path.parent / ref))

        finally:
            self.resolved_refs.discard(ref)

        return {"type": "unknown", "description": f"Unresolved reference: {ref}"}

    def get_cardinality(self, schema: Dict[str, Any], parent_required: List[str], prop_name: str) -> str:
        """Determine cardinality based on schema constraints"""
        is_required = prop_name in parent_required

        if schema.get('type') == 'array':
            min_items = schema.get('minItems', 0)
            max_items = schema.get('maxItems')

            if is_required:
                if min_items > 0:
                    if max_items is not None:
                        return f"{min_items}..{max_items}"
                    else:
                        return f"{min_items}..*"
                else:
                    if max_items is not None:
                        return f"0..{max_items}"
                    else:
                        return "0..*"
            else:
                return "0..1 (array)"

        else:
            return "1..1" if is_required else "0..1"

    def get_type_string(self, schema: Dict[str, Any]) -> str:
        """Extract type information from schema"""
        if 'type' in schema:
            schema_type = schema['type']
            if isinstance(schema_type, list):
                return ' | '.join(schema_type)
            elif schema_type == 'array':
                items = schema.get('items', {})
                item_type = self.get_type_string(items) if items else 'any'
                return f"array<{item_type}>"
            elif schema_type == 'object':
                return "object"
            else:
                return schema_type

        elif 'enum' in schema:
            enum_values = schema['enum']
            if len(enum_values) <= 3:
                return f"enum({', '.join(map(str, enum_values))})"
            else:
                return f"enum({len(enum_values)} values)"

        elif 'oneOf' in schema:
            return "oneOf"
        elif 'anyOf' in schema:
            return "anyOf"
        elif 'allOf' in schema:
            return "allOf"

        elif '$ref' in schema:
            return f"ref({schema['$ref']})"

        else:
            return "unknown"

    def parse_schema(self, schema: Dict[str, Any], path: str = "", parent_required: List[str] = None, 
                    current_file: Path = None) -> None:
        """Recursively parse schema and extract properties"""
        if parent_required is None:
            parent_required = []

        if current_file is None:
            current_file = self.base_path

        # Handle $ref
        if '$ref' in schema:
            resolved = self.resolve_reference(schema['$ref'], schema, current_file)
            self.parse_schema(resolved, path, parent_required, current_file)
            return

        # Handle allOf, anyOf, oneOf
        for combine_key in ['allOf', 'anyOf', 'oneOf']:
            if combine_key in schema:
                for i, sub_schema in enumerate(schema[combine_key]):
                    if combine_key == 'allOf':
                        sub_path = path
                    elif combine_key == 'anyOf':
                        sub_path = f'{path}[or]/'
                    elif combine_key == 'oneOf':
                        sub_path = f'{path}[xor]/'
                    self.parse_schema(sub_schema, sub_path, parent_required, current_file)
                return

        # Handle object properties
        if schema.get('type') == 'object' or 'properties' in schema:
            properties = schema.get('properties', {})
            required = schema.get('required', [])

            for prop_name, prop_schema in properties.items():
                prop_path = f"{path}/{prop_name}"

                # Add this property to the list
                self.properties.append(SchemaProperty(
                    path=path or '/',
                    name=prop_name,
                    data_type=self.get_type_string(prop_schema),
                    cardinality=self.get_cardinality(prop_schema, required, prop_name),
                    description=prop_schema.get('description', '')
                ))

                # Recursively parse nested objects and arrays
                if prop_schema.get('type') == 'object' or 'properties' in prop_schema:
                    self.parse_schema(prop_schema, prop_path, [], current_file)
                elif prop_schema.get('type') == 'array' and 'items' in prop_schema:
                    items_schema = prop_schema['items']
                    if items_schema.get('type') == 'object' or 'properties' in items_schema:
                        self.parse_schema(items_schema, f'{prop_path}[]', [], current_file)
                    elif '$ref' in items_schema:
                        resolved = self.resolve_reference(items_schema['$ref'], items_schema, current_file)
                        self.parse_schema(resolved, f'{prop_path}[]', [], current_file)
                elif '$ref' in prop_schema:
                    resolved = self.resolve_reference(prop_schema['$ref'], prop_schema, current_file)
                    self.parse_schema(resolved, prop_path, [], current_file)

        # Handle array items
        elif schema.get('type') == 'array' and 'items' in schema:
            items_schema = schema['items']
            if items_schema.get('type') == 'object' or 'properties' in items_schema:
                array_path = f"{path}[]" if path else "[]"
                self.parse_schema(items_schema, array_path, [], current_file)

    def visualize_schema(self, schema_file: str) -> pd.DataFrame:
        """Main method to visualize schema as a table"""
        self.properties = []
        self.resolved_refs = set()
        self.schema_cache = {}

        schema = self.load_schema(schema_file)
        schema_path = Path(schema_file)

        self.parse_schema(schema, current_file=schema_path)

        # Convert to DataFrame
        data = []
        for prop in self.properties:
            data.append({
                'Path': prop.path,
                'Property Name': prop.name,
                'Expected Data Type': prop.data_type,
                'Cardinality': prop.cardinality,
                'Description': prop.description
            })

        df = pd.DataFrame(data)
        return df

    def save_as_csv(self, df: pd.DataFrame, output_file: str) -> None:
        """Save DataFrame as CSV"""
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"Schema visualization saved as CSV: {output_file}")

    def save_as_ods(self, df: pd.DataFrame, output_file: str) -> None:
        """Save DataFrame as ODS"""
        try:
            df.to_excel(output_file, index=False, engine='odf')
            print(f"Schema visualization saved as ODS: {output_file}")
        except ImportError:
            print("Warning: odfpy not installed. Installing...")
            import subprocess
            subprocess.check_call(['pip', 'install', 'odfpy'])
            df.to_excel(output_file, index=False, engine='odf')
            print(f"Schema visualization saved as ODS: {output_file}")


def main():
    parser = argparse.ArgumentParser(description='Visualize JSON Schema as a table')
    parser.add_argument('schema_file', help='Path to the YAML/JSON schema file')
    parser.add_argument('-o', '--output', help='Output file path')
    parser.add_argument('-f', '--format', choices=['csv', 'ods'], default='csv',
                       help='Output format (default: csv)')

    args = parser.parse_args()

    base_path = Path(args.schema_file).parent

    # Create visualizer
    visualizer = JSONSchemaVisualizer(base_path)

    try:
        # Generate table
        df = visualizer.visualize_schema(Path(args.schema_file).name)

        if df.empty:
            print("No properties found in the schema.")
            return

        # Determine output file
        if args.output:
            output_file = args.output
        else:
            schema_path = Path(args.schema_file)
            output_file = schema_path.with_suffix(f'.{args.format}')

        # Save file
        if args.format == 'csv':
            visualizer.save_as_csv(df, output_file)
        else:
            visualizer.save_as_ods(df, output_file)

        # Print preview
        print(f"\nPreview of generated table ({len(df)} properties):")
        print("=" * 80)
        print(df.head(10).to_string(index=False))
        if len(df) > 10:
            print(f"... and {len(df) - 10} more properties")

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0

if __name__ == '__main__':
    exit(main())
