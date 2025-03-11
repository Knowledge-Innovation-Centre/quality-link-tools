import argparse
import pathlib
import os
import logging

from rdflib import Graph, Literal, RDF, URIRef, Namespace
from rdflib.namespace import RDF, RDFS, SH, OWL

ELM = Namespace("http://data.europa.eu/snb/model/elm/")
LOQ = Namespace("http://data.europa.eu/snb/model/ap/loq-constraints/")
SCHEMA = Namespace("https://schema.org/")

class ShaclToDesm:
    """
    convert SHACL shapes and info from related ontology into a form suitable for DESM
    """

    def __init__(self, input_files, language='en'):
        """
        initialise class by loading input files
        """
        self.logger = logging.getLogger(__name__)
        # load input graphs
        self.graph = self._new_graph()
        for file in input_files:
            self.load_monolingual(file, language)
        self.logger.info(f"Loaded {len(self.graph)} triples")


    def _new_graph(self):
        """
        create an empty Graph with some defaults
        """
        graph = Graph(bind_namespaces="rdflib")
        graph.bind('elm', ELM)
        graph.bind('loq', LOQ)
        graph.bind('schema', SCHEMA)
        return graph


    def load_monolingual(self, ontology_file, desired_language):
        """
        Extracts a monolingual version of the given RDF ontology.
        
        Args:
            ontology_file (str): Path to the multi-lingual RDF ontology file.
            graph (Graph): Graph to which to add the loaded triples
            desired_language (str): The language code of the desired language (e.g., "en", "fr", "es").
        """
        # Load the multi-lingual RDF ontology
        ontology_graph = Graph()
        ontology_graph.parse(ontology_file)
        
        # Iterate through the triples and filter by language
        for subject, predicate, object in ontology_graph:
            if isinstance(object, Literal):
                if object.language == desired_language:
                    self.graph.add((subject, predicate, object))
            else:
                self.graph.add((subject, predicate, object))


    def shape_to_desm(self, shape):
        """
        convert one single shape for DESM
        """
        self.logger.info(f"Processing {shape}:")
        # create empty graph
        desm_graph = self._new_graph()
        # include all triples about targetClass
        targetClass = self.graph.value(shape, SH.targetClass)
        if targetClass is None:
            self.logger.warning(f" - shape has no targetClass, skipping.")
            return None
        self.logger.info(f" - targetClass: {targetClass}")
        for predicate, object in self.graph.predicate_objects(targetClass):
            desm_graph.add((targetClass, predicate, object))
        # iterate over all properties, include each with appropriate rdfs:domain
        for property in self.graph.objects(shape, SH.property):
            path = self.graph.value(property, SH.path)
            desm_graph.add((path, RDF.type, RDF.Property))
            desm_graph.add((path, RDF.type, OWL.ObjectProperty))
            desm_graph.add((path, RDFS.domain, targetClass))
            desm_graph.add((path, SCHEMA.domainIncludes, targetClass))
            label = self.graph.value(property, SH.name, any=True) or self.graph.value(path, RDFS.label, any=True)
            comment = self.graph.value(property, SH.description, any=True) or self.graph.value(path, RDFS.comment, any=True)
            desm_graph.add((path, RDFS.label, label))
            desm_graph.add((path, RDFS.comment, comment))
            if range := self.graph.value(property, SH.datatype) or self.graph.value(property, SH['class']):
                desm_graph.add((path, RDFS.range, range))
                desm_graph.add((path, SCHEMA.rangeIncludes, range))
        return desm_graph


if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("INPUT",
                        nargs='*',
                        help="SHACL and ontology files to convert for DESM")
    parser.add_argument("-o", "--output",
                        type=pathlib.Path,
                        default='.',
                        help="output path (default: working directory)")
    parser.add_argument("-m", "--merge",
                        help="merge output into one graph",
                        action="store_true")
    parser.add_argument("-v", "--verbose",
                        help="increase output verbosity",
                        action="store_true")
    args = parser.parse_args()

    converter = ShaclToDesm(args.INPUT)

    if args.merge:
        target_graph = converter._new_graph()

    logger.info("Graph contains SHACL shapes for:")
    for shape in converter.graph.subjects(RDF.type, SH.NodeShape):
        filename = os.path.join(args.output, "".join((c if c.isalnum() or c in '-_+' else '_') for c in shape.n3(converter.graph.namespace_manager)) + ".ttl")
        if desm_graph := converter.shape_to_desm(shape):
            if args.merge:
                target_graph += desm_graph
            else:
                desm_graph.serialize(destination=filename)
                logger.info(f' - written to {filename}')
    if args.merge:
        filename = os.path.join(args.output, "ELM-for-DESM.ttl")
        target_graph.serialize(destination=filename)
        logger.info(f' - written to {filename}')

