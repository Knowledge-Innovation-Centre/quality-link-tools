#
# create RDF ontologies based on JSON Schema in OpenAPI definition
#
# useful for importing data standards to DESM
#
# by Colin Tück <colin@knowledgeinnovation.eu> and Ronald Ham <ronald.ham@surf.nl>
#

import argparse
import json
import uuid

import yaml
import jsonref

from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, SKOS, OWL, XSD
from pathlib import Path

# Define namespaces
OAS = Namespace("https://spec.openapis.org/oas#")
SCHEMA = Namespace('https://schema.org/')

def type2rdf(prop_details):
    """
    Convert schema types to value for RDFS.range
    """
    if 'type' in prop_details:
        if 'string' in prop_details['type']:
            return XSD.string
        elif 'integer' in prop_details['type']:
            return XSD.integer
        elif 'object' in prop_details['type']:
            return RDFS.Class
        elif 'array' in prop_details['type']:
            if 'items' in prop_details:
                return type2rdf(prop_details['items'])
            else:
                return RDFS.Literal
        else:
            return RDFS.Literal
    elif 'oneOf' in prop_details:
        return type2rdf(prop_details['oneOf'][0])
    else:
        return RDFS.Literal

def schema2rdf(schema_name, schema_details, g):
    """
    Convert OpenAPI-style JSON schema to RDF
    """

    # represent schema as class
    schema_uri = EX[schema_name]
    g.add((schema_uri, RDF.type, RDFS.Class))
    g.add((schema_uri, RDFS.label, Literal(schema_name)))

    if 'description' in schema_details:
        g.add((schema_uri, RDFS.comment, Literal(schema_details['description'])))
    elif 'allOf' in schema_details:
        for sub in reversed(schema_details['allOf']):
            if 'description' in sub:
                g.add((schema_uri, RDFS.comment, Literal(sub['description'])))
                break

    if 'properties' in schema_details:
        properties = schema_details['properties'].copy()
    else:
        properties = {}

    if 'allOf' in schema_details:
        for sub in schema_details['allOf']:
            properties.update(sub.get('properties', {}))

    # Convert properties inside schema
    for prop_name, prop_details in properties.items():
        prop_uri = EX[prop_name]
        g.add((prop_uri, RDF.type, RDF.Property))
        g.add((prop_uri, RDFS.label, Literal(prop_name)))
        g.add((prop_uri, SCHEMA.domainIncludes, schema_uri))
        if 'description' in prop_details:
            g.add((prop_uri, RDFS.comment, Literal(prop_details['description'])))
        elif 'oneOf' in prop_details:
            for sub in prop_details['oneOf']:
                if 'description' in sub:
                    g.add((prop_uri, RDFS.comment, Literal(sub['description'])))
                    break
        g.add((prop_uri, RDFS.range, type2rdf(prop_details)))



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Represent OpenAPI spec schema as RDF for DESM')
    parser.add_argument('SPEC', help='specification in OpenAPI format')
    parser.add_argument('SCHEMA', nargs='*', help='which schema to extrat')
    parser.add_argument('-b', '--base', help='Base URI for generated RDF')
    parser.add_argument('-p', '--prefix', help='Prefix mapped to base URI (default: "api")', default="api")
    parser.add_argument('-o', '--output', help='RDF output file name')
    args = parser.parse_args()

    if not args.base:
        args.base = f'urn:uuid:{uuid.uuid4()}#'

    EX = Namespace(args.base)

    print(f"Loading OpenAPI spec from {args.SPEC}...")
    with open(args.SPEC, 'r') as f:
        spec = yaml.safe_load(f)
        #openapi_data = yaml.safe_load(f)

    # Resolve all $ref references
    openapi_data = jsonref.JsonRef.replace_refs(spec)

    # Create RDF graph
    g = Graph()
    g.bind(args.prefix, EX)
    g.bind("oas", OAS)
    g.bind("skos", SKOS)
    g.bind("schema", SCHEMA)

    # Convert OpenAPI info to RDF
    api_uri = EX.api
    g.add((api_uri, RDF.type, OAS.API))
    g.add((api_uri, RDFS.label, Literal(openapi_data["info"]["title"])))
    g.add((api_uri, SKOS.definition, Literal(openapi_data["info"].get("description", "No description"))))

    if len(args.SCHEMA) == 0:
        args.SCHEMA = list(openapi_data['components']['schemas'].keys())

    # Convert schemas to RDF
    for schema_name in args.SCHEMA:
        schema_details = openapi_data['components']['schemas'][schema_name]
        schema2rdf(schema_name, schema_details, g)

    # Save as Turtle
    if args.output:
        g.serialize(destination=args.output)
        print(f"✅ OpenAPI converted to RDF: {args.output}")
    else:
        print(g.serialize(format='turtle'))

