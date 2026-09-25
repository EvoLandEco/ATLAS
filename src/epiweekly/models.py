"""Evidence extraction contract; JSON Schema is generated from these models."""
from __future__ import annotations
import math
from datetime import date
from enum import StrEnum
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Status(StrEnum):
    REPORTED = "reported"
    NOT_REPORTED = "not_reported"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"
    PENDING = "pending_verification"
    CONFLICTING = "conflicting"
    NOT_EXTRACTED = "not_extracted"
    NOT_COMPARABLE = "not_comparable"
    ACCESS_RESTRICTED = "access_restricted"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TextValue(StrictModel):
    value: str | None = None
    status: Status = Status.NOT_REPORTED

    @model_validator(mode="after")
    def consistency(self):
        if (self.value is not None) != (self.status == Status.REPORTED):
            raise ValueError("A reported value is present; a missing value has an explicit missingness status")
        if self.value is not None and not self.value.strip():
            raise ValueError("Use null and a missingness status for empty text")
        return self


class DateValue(TextValue):
    @model_validator(mode="after")
    def iso_date(self):
        if self.value is not None:
            if date.fromisoformat(self.value).isoformat()!=self.value:
                raise ValueError("Dates use YYYY-MM-DD")
        return self


class Evidence(StrictModel):
    field: str = Field(min_length=1, max_length=120)
    quote: str = Field(min_length=3, max_length=400)
    locator: str = Field(default="text", max_length=120)


class Resource(StrictModel):
    kind: Literal["dataset", "sequences", "software", "paper", "data_call", "other"]
    title: str = Field(min_length=1, max_length=250)
    url: str = Field(min_length=8, max_length=2048)
    access: Literal["public", "registration", "controlled", "unknown"] = "unknown"
    evidence: Evidence


class Observation(StrictModel):
    metric: Literal["cases", "deaths", "hospitalizations", "affected_holdings", "affected_animals",
                    "samples_tested", "positive_samples", "test_positivity", "other"]
    value: float | None = None
    value_status: Status = Status.NOT_REPORTED
    unit: Literal["people", "holdings", "animals", "samples", "percent", "proportion", "other", "unknown"]
    count_kind: Literal["cumulative", "interval", "point", "unknown"]
    case_class: Literal["confirmed", "probable", "suspected", "confirmed_and_probable", "all_reported", "unknown"]
    date_basis: Literal["onset", "notification", "specimen", "death", "report", "unknown"]
    period_start: DateValue = Field(default_factory=DateValue)
    period_end: DateValue = Field(default_factory=DateValue)
    case_definition: TextValue = Field(default_factory=TextValue)
    population: TextValue = Field(default_factory=TextValue)
    stratum: TextValue = Field(default_factory=TextValue)
    denominator: float | None = None
    denominator_status: Status = Status.NOT_REPORTED
    qualifier: Literal["exact", "approximately", "at_least", "at_most", "unknown"] = "unknown"
    origin_authority: TextValue = Field(default_factory=TextValue)
    evidence: Evidence

    @model_validator(mode="after")
    def numerical_contract(self):
        for field, status in [("value",self.value_status),("denominator",self.denominator_status)]:
            n = getattr(self,field)
            if (n is not None) != (status == Status.REPORTED):
                raise ValueError(f"{field} and {field}_status disagree")
            if n is not None and (not math.isfinite(n) or n < 0):
                raise ValueError(f"{field} must be finite and nonnegative")
        if self.value is not None:
            if self.unit in {"people","holdings","animals","samples"} and self.value != int(self.value):
                raise ValueError("Counts use integers")
            if self.unit == "percent" and self.value > 100:
                raise ValueError("A percent is in [0,100]")
            if self.unit == "proportion" and self.value > 1:
                raise ValueError("A proportion is in [0,1]")
        if self.period_start.value and self.period_end.value and self.period_start.value > self.period_end.value:
            raise ValueError("The observation period must be ordered")
        return self


class Mention(StrictModel):
    local_key: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=3, max_length=240)
    kind: Literal["outbreak", "cluster", "single_case", "surveillance_aggregate", "signal", "context"]
    disease: TextValue = Field(default_factory=TextValue)
    pathogen: TextValue = Field(default_factory=TextValue)
    host: TextValue = Field(default_factory=TextValue)
    country_code: TextValue = Field(default_factory=TextValue)
    location: TextValue = Field(default_factory=TextValue)
    geographic_scope: Literal["subnational", "national", "multinational", "global", "unknown"] = "unknown"
    # A stable outbreak identifier explicitly assigned by the reporting authority.
    authority_event_id: TextValue = Field(default_factory=TextValue)
    authority_namespace: TextValue = Field(default_factory=TextValue)
    reported_status: Literal["active", "resolved", "monitoring", "unknown"] = "unknown"
    event_start: DateValue = Field(default_factory=DateValue)
    as_of: DateValue = Field(default_factory=DateValue)
    summary: str = Field(min_length=3, max_length=650)
    tags: list[Literal["cross_border", "one_health_interface", "transmission_uncertain", "genomic_data",
                       "public_data", "reporting_revision", "data_call", "network_question"]] = Field(default_factory=list)
    observations: list[Observation] = Field(default_factory=list, max_length=30)
    resources: list[Resource] = Field(default_factory=list, max_length=10)
    evidence: list[Evidence] = Field(min_length=1, max_length=20)
    ambiguity_reasons: list[str] = Field(default_factory=list, max_length=15)

    @model_validator(mode="after")
    def identifier_pair(self):
        if bool(self.authority_event_id.value) != bool(self.authority_namespace.value):
            raise ValueError("Authority event ID and namespace travel together")
        if self.country_code.value:
            import pycountry
            if pycountry.countries.get(alpha_2=self.country_code.value.upper()) is None:
                raise ValueError("country_code must be an ISO 3166-1 alpha-2 code")
        return self


class Extraction(StrictModel):
    outcome: Literal["extracted", "no_relevant_content", "needs_review"]
    mentions: list[Mention] = Field(default_factory=list, max_length=40)
    notes: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def outcome_consistency(self):
        if self.outcome == "extracted" and not self.mentions:
            raise ValueError("extracted requires at least one mention")
        if self.outcome == "no_relevant_content" and self.mentions:
            raise ValueError("no_relevant_content has an empty mention list")
        return self


class Review(StrictModel):
    candidate_id: str
    action: Literal["accept", "reject", "defer"]
    event_key: str | None = None
    reviewer: str = Field(min_length=2, max_length=100)
    rationale: str = Field(min_length=3, max_length=800)
    public_rationale: str = Field(default="Editorial review", min_length=3, max_length=300)
    supersedes_candidate_ids: list[str] = Field(default_factory=list)
    allow_disease_reclassification: bool = False

    @model_validator(mode="after")
    def target(self):
        if self.action == "accept" and not self.event_key:
            raise ValueError("An accepted candidate requires a stable event_key")
        if self.action != "accept" and (self.event_key or self.supersedes_candidate_ids):
            raise ValueError("Only acceptance assigns an event and supersedes claims")
        return self


class Relation(StrictModel):
    from_event_key: str
    to_event_key: str
    relation: Literal["part_of", "possible_link", "reported_link", "shared_exposure", "cross_host_link", "merged_into", "split_from"]
    evidence_candidate_id: str
    basis: Literal["source_reported", "analyst_hypothesis", "editorial_identity"]
    reviewer: str = Field(min_length=2, max_length=100)
    rationale: str = Field(min_length=3, max_length=500)


class OpportunityDecision(StrictModel):
    opportunity_id: str
    status: Literal["suggested", "triaged", "investigating", "completed", "declined"]
    owner: TextValue = Field(default_factory=TextValue)
    next_action: str = Field(min_length=3,max_length=500)
    reviewer: str = Field(min_length=2,max_length=100)


def reported(value: str) -> dict:
    return {"value": value, "status":"reported"}
