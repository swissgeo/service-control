from http import HTTPStatus

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import DCTERMS, RDF, SKOS
from requests import get

from thesaurus.models import ROOT_CONCEPT_ID, Thesaurus
from utils.language import LanguageCode

TIMEOUT = 30


class ThesaurusLookup:
    """Stores thesaurus concepts and their translations and allows lookup of concepts by any
    translation.

    Keywords in geocat and geodienste are defined using a thesaurus but are stored as freetext
    property, i.e. a text with optional translations but without the identifier of the underlying
    concept. Since the text usually is equal to one of the translations, it should be possible to
    make a reverse lookup using the thesaurus to fill in the identifier and the missing
    translations.

    Note: This is the same code as used in geoadmin/service-control
    """

    def __init__(self, url: str) -> None:
        self.url = url
        self.concepts: dict[str, dict[str, str]] = {}
        self.index: dict[str, dict[str, str]] = {}

    @classmethod
    def build(cls, url: str) -> ThesaurusLookup | None:
        """Build the thesaurus lookup instance by creating a list of concepts with its translations
        and a lookup table for each translation.

        The thesaurus is defined as RDF (Resource Description Framework), a directed graph of
        triples (subject, predicate, object). Each concept is represented by two kinds of triples:
        a type triple (concept URI, rdf:type, skos:Concept) and one label triple per language
        (concept URI, skos:prefLabel, translation).

        We first collect all known concept URIs from the type triples, then iterate over all
        triples to find prefLabel entries for all the concepts and supported languages.
        """
        if not url:
            return None

        response = get(url, timeout=TIMEOUT, headers={"Accept": "text/xml"})
        if response.status_code != HTTPStatus.OK:
            return None

        graph = Graph()
        graph.parse(data=response.content, format="xml")

        concepts = list(graph.subjects(RDF.type, SKOS.Concept))

        result = cls(url)
        for subject, predicate, label in graph:
            if (
                subject in concepts
                and predicate == SKOS.prefLabel
                and isinstance(label, Literal)
                and label.language in ("de", "fr", "en", "it", "rm")
            ):
                result.concepts.setdefault(str(subject), {})[label.language] = str(label)
                result.index.setdefault(label.language, {})[str(label)] = str(subject)

        return result

    def find_concept(self, term: str) -> tuple[str | None, dict[str, str]]:
        """Find a concept by translation.

        Try to find a concept by searching all translations for the given term.
        """

        for lang in ("de", "fr", "en", "it", "rm"):
            if concept := self.index.get(lang, {}).get(term):
                return concept, self.concepts[concept]
        return None, {}

    def __str__(self) -> str:
        return f"ThesaurusLookup {self.url}"


def thesaurus_to_skos_jsonld(thesaurus: Thesaurus) -> str:
    """Build a SKOS JSON-LD graph for a single Thesaurus and its Concepts."""

    graph = Graph()
    graph.bind("skos", SKOS)
    graph.bind("dcterms", DCTERMS)

    scheme_uri = URIRef(f"https://swissgeo.ch/thesaurus/{thesaurus.thesaurus_id}")
    graph.add((scheme_uri, RDF.type, SKOS.ConceptScheme))
    graph.add((scheme_uri, DCTERMS.identifier, Literal(thesaurus.thesaurus_id)))

    concepts = thesaurus.concept_set.select_related("parent").exclude(concept_id=ROOT_CONCEPT_ID)  # ty: ignore[unresolved-attribute]

    for concept in concepts:
        uri = URIRef(
            f"https://swissgeo.ch/thesaurus/{thesaurus.thesaurus_id}/concept/{concept.concept_id}"
        )
        graph.add((uri, RDF.type, SKOS.Concept))
        graph.add((uri, DCTERMS.identifier, Literal(concept.concept_id)))
        graph.add((uri, SKOS.inScheme, scheme_uri))

        for lang in LanguageCode:
            value = getattr(concept, f"label_{lang}", None)
            if value:
                graph.add((uri, SKOS.prefLabel, Literal(value, lang=lang)))

        is_top = concept.parent is None or concept.parent.concept_id == ROOT_CONCEPT_ID
        if is_top:
            graph.add((scheme_uri, SKOS.hasTopConcept, uri))
            graph.add((uri, SKOS.topConceptOf, scheme_uri))
        else:
            parent_uri = URIRef(
                f"https://swissgeo.ch/thesaurus/{thesaurus.thesaurus_id}/concept/{concept.parent.concept_id}"
            )
            graph.add((uri, SKOS.broader, parent_uri))
            graph.add((parent_uri, SKOS.narrower, uri))

    return graph.serialize(format="json-ld", indent=2)
