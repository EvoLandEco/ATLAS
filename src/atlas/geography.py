"""Evidence references and completion checks for geographic assessment."""
from __future__ import annotations

import re
from typing import Literal
import pycountry
from pydantic import Field
from .models import StrictModel
from .util import digest

REVIEW_VERSION = '1.0.0'


def review_fingerprint(record, source, prompt=None):
    from .config import assets
    return digest([REVIEW_VERSION, assets('geography.md') if prompt is None else prompt, digest(Reviews.model_json_schema()),
                   record, digest(source.encode()), 'codex-default'])


class Reference(StrictModel):
    claim_index: int = Field(ge=0)
    quote_index: int = Field(ge=0)


class Location(Reference):
    area_code: str
    role: Literal['occurrence', 'travel_origin', 'travel_destination', 'exposure', 'context', 'reporting_scope']
    reason: str


class Link(Reference):
    type: Literal['movement', 'shared_event', 'hypothesis']
    from_code: str
    to_code: str
    label: str
    basis: str
    limit: str
    directed: bool


class Assessment(Reference):
    type: Literal['transmission', 'exposure', 'unresolved']
    label: str
    from_label: str
    to_label: str
    basis: str
    limit: str


class Review(StrictModel):
    record_id: str
    status: Literal['assessed', 'no_specific_location', 'unresolved']
    reason: str
    primary_area_code: str | None
    locations: list[Location]
    links: list[Link]
    assessments: list[Assessment]


class Reviews(StrictModel):
    records: list[Review]


def validate_review(review, record, source):
    """Check references without treating quotation matching as semantic review."""
    review = Review.model_validate(review)
    if review.record_id != record['id']:
        raise ValueError('Geographic review record differs')
    claims = {c['claim_index']: c for c in record['claims']}
    for entry in [*review.locations, *review.links, *review.assessments]:
        claim = claims.get(entry.claim_index)
        if claim is None or entry.quote_index >= len(claim['quotes']):
            raise ValueError('Geographic evidence reference is missing')
        quote = claim['quotes'][entry.quote_index]
        if not quote.strip() or not re.search(r'\s+'.join(re.escape(w) for w in quote.split()), source):
            raise ValueError('Geographic quotation differs from captured text')
    codes = {loc.area_code for loc in review.locations}
    if any(pycountry.countries.get(alpha_2=code) is None for code in codes):
        raise ValueError('Unknown geographic code')
    keys = [(l.area_code, l.role, l.claim_index) for l in review.locations]
    if len(set(keys)) != len(keys):
        raise ValueError('Duplicate geographic membership')
    if review.primary_area_code is not None and not any(
        loc.area_code == review.primary_area_code and loc.role in {'occurrence', 'exposure', 'reporting_scope', 'travel_destination', 'travel_origin'}
        for loc in review.locations
    ):
        raise ValueError('Primary location lacks a reporting or event role')
    for link in review.links:
        if not {link.from_code, link.to_code} <= codes or link.from_code == link.to_code:
            raise ValueError('Geographic endpoints require distinct reviewed locations')
        if link.directed and link.type != 'movement':
            raise ValueError('Only reported movement supplies direction')
    if review.status == 'no_specific_location' and (review.locations or review.links or review.primary_area_code):
        raise ValueError('No-location assessment contains locations')
    if not review.reason.strip():
        raise ValueError('Geographic assessment needs a reason')
    return review


def validate_coverage(snapshot):
    """Require one current geographic assessment for every displayed record."""
    coverage = snapshot['geographic_review']
    if coverage['version'] != REVIEW_VERSION or coverage['records_sha256'] != digest(snapshot['records']):
        raise ValueError('Geographic coverage differs from snapshot')
    reviews = coverage['records']
    if len(reviews) != len({r['record_id'] for r in reviews}):
        raise ValueError('Duplicate geographic coverage record')
    if {r['record_id'] for r in reviews} != {r['id'] for r in snapshot['records']}:
        raise ValueError('Geographic assessment coverage is incomplete')
    for r in reviews:
        if r['status'] not in {'assessed', 'no_specific_location', 'unresolved', 'retained_review'} or not r['reason'].strip():
            raise ValueError('Invalid geographic assessment outcome')
    return coverage
