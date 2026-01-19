#!/usr/bin/env python

import json
import argparse
from rdflib import Graph

parser = argparse.ArgumentParser(description="Injects JSON-LD context into ECIU Learning Opportunities data.")
parser.add_argument('SOURCE', help="source file")
parser.add_argument('-c', '--context', help='JSON-LD @context file', default='eciu-context.json')
parser.add_argument('-o', '--output', help='Output JSON-LD file', default='eciu-parsed-ld.json')
parser.add_argument('-t', '--turtle', help='Output Turtle file', default='eciu-parsed.ttl')
args = parser.parse_args()

with open(args.context) as context_file:
    jsonld_context = json.load(context_file)

with open(args.SOURCE) as data_file:
    eciu_data = json.load(data_file)

if not isinstance(eciu_data, list):
    raise Exception("ECIU data should be an array but it's not")

jsonld = {
    '@context': jsonld_context['@context'],
    '@graph': []
}

i = 0
for line in eciu_data:
    jsonld['@graph'].append(json.loads(line))
    i += 1
print(f'parsed {i} lines')

with open(args.output, "w") as output_file:
    json.dump(jsonld, output_file)

g = Graph()
g.parse(data=json.dumps(jsonld), format="json-ld")
g.serialize(destination=args.turtle, format="turtle")

