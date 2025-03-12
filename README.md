QualityLink Tools
=================

Repository for various tools/converters used by the QualityLink project.

Mapping
-------

Resources for using [DESM](https://github.com/t3-innovation-network/desm) see [desm/](desm/).

The file [desm/abstract-classes.ttl](desm/abstract-classes.ttl) is needed to set up abstract base classes for the mapping in DESM.

### ELM

[convert.py](desm/ELM/convert.py) prepares ELM ontology and application profile for use in DESM. Pass both the ontology file and the application profile (e.g. LOQ) to it.

Python script requires [RDFLib](https://rdflib.readthedocs.io/en/stable/). Do:

```sh
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt
```

### OOAPI

See [desm/OOAPI/](desm/OOAPI/).

