import argparse
import pathlib
import os
import logging

from rdflib import Graph, Literal, RDF, URIRef, Namespace
from rdflib.namespace import RDF, RDFS, SH, OWL, SKOS

from rich.console import Console
from rich.table import Table

ELM = Namespace("http://data.europa.eu/snb/model/elm/")
LOQ = Namespace("http://data.europa.eu/snb/model/ap/loq-constraints/")
SCHEMA = Namespace("https://schema.org/")

def get_property_lang(graph, subject, predicate, language):
    """
    get a property in a specific language
    """
    for label in graph.objects(subject, predicate):
        if isinstance(label, Literal):
            if label.language == language:
                return label
    return f'[no label: {subject}]'

def get_label(graph, subject, language):
    """
    get label in specific language
    """
    return get_property_lang(graph, subject, SKOS.prefLabel, language)

if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("INPUT",
                        help="Controlled vocabulary")
    parser.add_argument("-l", "--language",
                        help="Language to use",
                        default="en")
    parser.add_argument("-v", "--verbose",
                        help="increase output verbosity",
                        action="store_true")
    args = parser.parse_args()

    # create an empty Graph with some defaults
    graph = Graph(bind_namespaces="rdflib")
    graph.bind('elm', ELM)
    graph.bind('loq', LOQ)
    graph.bind('schema', SCHEMA)

    # Load the file
    graph.parse(args.INPUT)

    console = Console()

    for scheme in graph.subjects(RDF.type, SKOS.ConceptScheme):
        table = Table(title=f"{get_label(graph, scheme, args.language)} ({scheme})")
        table.add_column("URI", style="cyan", no_wrap=True)
        table.add_column("Label", style="magenta")
        table.add_column("Definition")

        for concept in graph.subjects(SKOS.inScheme, scheme):
            table.add_row(concept, get_label(graph, concept, args.language), get_property_lang(graph, concept, SKOS.definition, args.language))
            if not graph.triples((concept, RDF.type, SKOS.Concept)):
                logger.warn("! {concept} is not of type skos:Concept")

        console.print(table)

