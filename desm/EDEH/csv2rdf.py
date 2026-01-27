#!/usr/bin/env python3

import csv
import argparse
import uuid
from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import RDF, RDFS, OWL, XSD

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert CSV file to RDF ontology')
    parser.add_argument('CSV', help='data schema as CSV file')
    parser.add_argument('-o', '--output', help='Output file name')
    parser.add_argument('-b', '--base', help='Base URI')
    args = parser.parse_args()

    if not args.base:
        args.base = f'urn:uuid:{uuid.uuid4()}#'

    SCHEMA = Namespace('https://schema.org/')

    g = Graph()
    g.add((URIRef(args.base), RDF.type, OWL.Ontology))

    with open(args.CSV) as csvfile:
        reader = csv.DictReader(csvfile)

        for line in reader:
            uri = URIRef(f'{args.base}{line["Property slug"]}')
            g.add((uri, RDF.type, RDF.Property))
            g.add((uri, RDF.type, OWL.DatatypeProperty))
            g.add((uri, RDFS.label, Literal(line["Property title"])))
            g.add((uri, RDFS.comment, Literal(line["Property definition"])))
            g.add((uri, SCHEMA.domainIncludes, URIRef(f'{args.base}{line["Class"]}')))

    if args.output:
        g.serialize(destination=args.output)
    else:
        print(g.serialize(format='turtle'))

