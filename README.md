QualityLink Ontology
====================

Repository for the RDF ontology and SHACL profile proposed by the QualityLink project.

Main file
---------

See [ontology.ttl](ontology.ttl).

Generate HTML documentation using the [SHACL documentation](https://shacl-play.sparna.fr/play/doc) tool.

Mapping
-------

Resources for using [DESM](https://github.com/t3-innovation-network/desm) see [desm/](desm/).

Python script requires [RDFLib](https://rdflib.readthedocs.io/en/stable/). Do:

```sh
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt
```

### ELM

[convert.py](desm/ELM/convert.py) prepares ELM ontology and application profile for use in DESM. Pass both the ontology file and the application profile (e.g. LOQ) to it.

### OOAPI

See [desm/OOAPI/](desm/OOAPI/).

