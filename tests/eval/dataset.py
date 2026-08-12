"""Evaluation dataset — ADR-0017, `docs/quality/evaluation-strategy.md`.

Schema-validated (ADR-0021), ~25-30 questions across the 8 named categories.
Every entity/attribute/relationship named below is real, taken directly
from the actual ingested corpus (verified against `cdm.db` after a real
`task ingest:run`) — not invented or copied from a fixture.

Field semantics (not every question populates every field):
- `expected_entities`: namespaced names the Entity Matcher should resolve to.
- `expected_attributes`: for attribute_retrieval — checked against
  `get_attributes()`'s returned attribute names directly.
- `expected_relationship_targets`: for relationship_retrieval — **bare**
  CDM names, matching what `get_relationships()` actually returns (it does
  not resolve targets to namespaced names; only the traversal adjacency
  does that — see app/adapters/structured_index_sqlite.py).
- `expected_path`: for multi_hop — namespaced names, matching `traverse()`'s
  resolved path. Empty means "no path exists within the depth-2 cap" is
  itself the expected (correct) outcome, not a gap in the dataset.
- `expect_refusal`: ground truth for the refusal-accuracy metric.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict

Category = Literal[
    "entity_discovery",
    "attribute_retrieval",
    "relationship_retrieval",
    "multi_hop",
    "paraphrased",
    "ambiguous_collision",
    "out_of_scope",
    "adversarial",
]


class EvalQuestion(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    category: Category
    question: str
    expected_entities: tuple[str, ...] = ()
    expected_attributes: tuple[str, ...] = ()
    expected_relationship_targets: tuple[str, ...] = ()
    expected_path: tuple[str, ...] = ()
    expect_refusal: bool = False
    notes: str | None = None


EVAL_QUESTIONS: tuple[EvalQuestion, ...] = (
    # -- entity_discovery ---------------------------------------------------
    EvalQuestion(
        id="disc-01",
        category="entity_discovery",
        question="What banking entities are available in this model?",
        expected_entities=("banking:Account", "banking:Bank", "banking:Branch"),
        notes="Open-ended; graded via vector Recall@K, not an exact route.",
    ),
    EvalQuestion(
        id="disc-02",
        category="entity_discovery",
        question="What entities describe a customer's financial holdings?",
        expected_entities=("banking:FinancialHolding", "banking:CustomerFinancialHolding"),
    ),
    EvalQuestion(
        id="disc-03",
        category="entity_discovery",
        question="What CRM-related entities exist in this model?",
        expected_entities=("crmCommon:Contact", "crmCommon:Organization", "crmCommon:Lead"),
    ),
    # -- attribute_retrieval --------------------------------------------------
    EvalQuestion(
        id="attr-01",
        category="attribute_retrieval",
        question="What are the attributes of banking:Account?",
        expected_entities=("banking:Account",),
        expected_attributes=("accountId",),
    ),
    EvalQuestion(
        id="attr-02",
        category="attribute_retrieval",
        question="What are the attributes of crmCommon:Organization?",
        expected_entities=("crmCommon:Organization",),
        expected_attributes=("schedulingEngine",),
    ),
    EvalQuestion(
        id="attr-03",
        category="attribute_retrieval",
        question="What core fields does banking:FinancialHolding have?",
        expected_entities=("banking:FinancialHolding",),
        # Complete set (not a sample) — verified against cdm.db directly —
        # so precision is meaningful, not artificially tanked by a partial list.
        expected_attributes=(
            "financialholdingId",
            "createdOn",
            "modifiedOn",
            "statecode",
            "statuscode",
            "importSequenceNumber",
            "overriddenCreatedOn",
            "timeZoneRuleVersionNumber",
            "UTCConversionTimeZoneCode",
            "name",
            "accountingClassification",
            "financialHoldingCategory",
            "financialHoldingCode",
            "integrationKey",
            "validFrom",
        ),
    ),
    EvalQuestion(
        id="attr-04",
        category="attribute_retrieval",
        question="What attributes does crmCommon:Lead have?",
        expected_entities=("crmCommon:Lead",),
        # Complete set (not a sample) — verified against cdm.db directly.
        expected_attributes=(
            "leadId",
            "fullName",
            "processId",
            "stageId",
            "traversedPath",
            "address1AddressId",
            "address1AddressTypeCode",
            "address1City",
            "address1Composite",
            "address1Country",
            "address1County",
            "address1Fax",
            "address1Latitude",
            "address1Line1",
            "address1Line2",
            "address1Line3",
            "address1Longitude",
            "address1Name",
            "address1PostalCode",
            "address1PostOfficeBox",
            "address1ShippingMethodCode",
            "address1StateOrProvince",
            "address1Telephone1",
            "address1Telephone2",
            "address1Telephone3",
            "address1UPSZone",
            "address1UTCOffset",
            "address2AddressId",
            "address2AddressTypeCode",
            "address2City",
            "address2Composite",
            "address2Country",
            "address2County",
            "address2Fax",
            "address2Latitude",
            "address2Line1",
            "address2Line2",
            "address2Line3",
            "address2Longitude",
            "address2Name",
            "address2PostalCode",
            "address2PostOfficeBox",
            "address2ShippingMethodCode",
            "address2StateOrProvince",
            "address2Telephone1",
            "address2Telephone2",
            "address2Telephone3",
            "address2UPSZone",
            "address2UTCOffset",
            "budgetAmount",
            "exchangeRate",
            "budgetAmountBase",
            "budgetStatus",
            "companyName",
            "confirmInterest",
            "decisionMaker",
            "description",
            "doNotBulkEMail",
            "doNotEMail",
            "doNotFax",
            "doNotPhone",
            "doNotPostalMail",
            "doNotSendMM",
            "EMailAddress1",
            "EMailAddress2",
            "EMailAddress3",
            "estimatedAmount",
            "estimatedAmountBase",
            "estimatedCloseDate",
            "estimatedValue",
            "evaluateFit",
            "fax",
            "firstName",
            "industryCode",
            "initialCommunication",
            "jobTitle",
            "lastName",
            "lastUsedInCampaign",
            "leadQualityCode",
            "leadSourceCode",
            "merged",
            "middleName",
            "mobilePhone",
            "need",
            "numberOfEmployees",
            "pager",
            "participatesInWorkflow",
            "preferredContactMethodCode",
            "priorityCode",
            "purchaseProcess",
            "qualificationComments",
            "revenue",
            "revenueBase",
            "salesStage",
            "salesStageCode",
            "salutation",
            "scheduleFollowupProspect",
            "scheduleFollowUpQualify",
            "SIC",
            "stateCode",
            "statusCode",
            "subject",
            "telephone1",
            "telephone2",
            "telephone3",
            "purchaseTimeFrame",
            "webSiteUrl",
            "onHoldTime",
            "lastOnHoldTime",
            "followEmail",
            "timeSpentByMeOnEmailAndMeetings",
            "entityImageId",
            "accountId",
            "contactId",
            "yomiCompanyName",
            "yomiFirstName",
            "yomiFullName",
            "yomiLastName",
            "yomiMiddleName",
        ),
    ),
    # -- relationship_retrieval (single-hop) ---------------------------------
    EvalQuestion(
        id="rel-01",
        category="relationship_retrieval",
        question="What is crmCommon:Contact connected to?",
        expected_entities=("crmCommon:Contact",),
        expected_relationship_targets=("Lead", "FacilityEquipment", "Service"),
    ),
    EvalQuestion(
        id="rel-02",
        category="relationship_retrieval",
        question="How does crmCommon:FacilityEquipment relate to other entities?",
        expected_entities=("crmCommon:FacilityEquipment",),
        expected_relationship_targets=("Organization", "BusinessUnit", "User", "Currency", "Site"),
    ),
    EvalQuestion(
        id="rel-03",
        category="relationship_retrieval",
        question="What is banking:FICard connected to?",
        expected_entities=("banking:FICard",),
        expected_relationship_targets=("Account", "Contact"),
        notes="Cardholder is a polymorphic party relationship (Account|Contact).",
    ),
    # -- multi_hop ------------------------------------------------------------
    EvalQuestion(
        id="hop-01",
        category="multi_hop",
        question="How does crmCommon:Contact relate to crmCommon:Organization?",
        expected_entities=("crmCommon:Contact", "crmCommon:Organization"),
        expected_path=("crmCommon:Contact", "crmCommon:FacilityEquipment", "crmCommon:Organization"),
        notes="No direct reference; resolves via preferredEquipment -> organization (2 hops).",
    ),
    EvalQuestion(
        id="hop-02",
        category="multi_hop",
        question="How does banking:CustomerFinancialHolding relate to banking:FinancialHolding?",
        expected_entities=("banking:CustomerFinancialHolding", "banking:FinancialHolding"),
        expected_path=("banking:CustomerFinancialHolding", "banking:FinancialHolding"),
        notes="Direct single-hop 'FinancialHolding' party relationship.",
    ),
    EvalQuestion(
        id="hop-03",
        category="multi_hop",
        question="How does crmCommon:Account relate to crmCommon:PriceList?",
        expected_entities=("crmCommon:Account", "crmCommon:PriceList"),
        expected_path=(),
        notes=(
            "Verified (not assumed) via a real depth-2 vs. depth-3 traversal probe: "
            "genuinely reachable only at 3 hops (Account -> Lead -> Campaign -> "
            "PriceList), so it's out of the depth-2 cap (ADR-0009) — correct "
            "behavior here is 'not found', not a fabricated shortcut."
        ),
    ),
    # -- paraphrased ------------------------------------------------------------
    EvalQuestion(
        id="para-01",
        category="paraphrased",
        question="Which fields make up banking:Account?",
        expected_entities=("banking:Account",),
        expected_attributes=("accountId",),
        notes="Paraphrase of attr-01 ('fields' instead of 'attributes').",
    ),
    EvalQuestion(
        id="para-02",
        category="paraphrased",
        question="What is banking:Account linked to?",
        expected_entities=("banking:Account",),
        expected_relationship_targets=(),
        notes="Paraphrase ('linked to'); banking:Account genuinely has no relationships.",
    ),
    EvalQuestion(
        id="para-03",
        category="paraphrased",
        question="What links crmCommon:Contact and crmCommon:Organization together?",
        expected_entities=("crmCommon:Contact", "crmCommon:Organization"),
        expected_path=("crmCommon:Contact", "crmCommon:FacilityEquipment", "crmCommon:Organization"),
        notes="Paraphrase of hop-01 ('links... together' instead of 'relate to').",
    ),
    # -- ambiguous_collision ------------------------------------------------
    EvalQuestion(
        id="amb-01",
        category="ambiguous_collision",
        question="What are the attributes of Account?",
        expected_entities=("banking:Account", "crmCommon:Account"),
        expect_refusal=True,
        notes=(
            "Unqualified 'Account' collides across namespaces (ADR-0007); the "
            "correct behavior is a clarification request, not a guess — surfaces "
            "as grounded=False on the refusal-accuracy metric's binary "
            "answer/decline axis, same as a not-found refusal, even though the "
            "underlying reason (ambiguity, not absence) differs."
        ),
    ),
    EvalQuestion(
        id="amb-02",
        category="ambiguous_collision",
        question="What are the attributes of Contact?",
        expected_entities=("banking:Contact", "crmCommon:Contact"),
        expect_refusal=True,
        notes="Same collision pattern as amb-01, different entity pair.",
    ),
    EvalQuestion(
        id="amb-03",
        category="ambiguous_collision",
        question="Tell me about Account",
        expected_entities=("banking:Account", "crmCommon:Account"),
        expect_refusal=True,
        notes="Collision surfaces even without an attribute/relationship keyword.",
    ),
    # -- out_of_scope ---------------------------------------------------------
    EvalQuestion(
        id="oos-01",
        category="out_of_scope",
        question="What is the capital of France?",
        expect_refusal=True,
        notes="Nothing to do with the CDM at all.",
    ),
    EvalQuestion(
        id="oos-02",
        category="out_of_scope",
        question="What are the attributes of Opportunity?",
        expect_refusal=True,
        notes="Real CDM entity name, referenced by crmCommon:Lead, but not itself ingested — a genuine unresolved reference, confirmed against the Validation Pass output.",
    ),
    EvalQuestion(
        id="oos-03",
        category="out_of_scope",
        question="What are the attributes of Invoice?",
        expect_refusal=True,
        notes="Plausible-sounding entity name that does not exist anywhere in the ingested scope.",
    ),
    EvalQuestion(
        id="oos-04",
        category="out_of_scope",
        question="How do I reset a user's password in this system?",
        expect_refusal=True,
        notes="Operational question, not a data-model question.",
    ),
    # -- adversarial / hallucination-probing ---------------------------------
    EvalQuestion(
        id="adv-01",
        category="adversarial",
        question="What is the socialSecurityNumber attribute on banking:Account?",
        expected_entities=("banking:Account",),
        expected_attributes=("accountId",),
        notes="banking:Account has exactly one real attribute (accountId); the template must not fabricate socialSecurityNumber.",
    ),
    EvalQuestion(
        id="adv-02",
        category="adversarial",
        question="Does banking:Account have a routingNumber field?",
        expected_entities=("banking:Account",),
        expected_attributes=("accountId",),
        notes="Another plausible-sounding but nonexistent attribute on the same real, sparse entity.",
    ),
    EvalQuestion(
        id="adv-03",
        category="adversarial",
        question="What is the direct relationship between banking:Bank and crmCommon:Lead?",
        expected_entities=("banking:Bank", "crmCommon:Lead"),
        expected_path=(),
        expect_refusal=False,
        notes="No relationship exists between these two entities anywhere in scope; must not invent a path.",
    ),
    EvalQuestion(
        id="adv-04",
        category="adversarial",
        question="Summarize the fraud-detection rules embedded in banking:Account.",
        expect_refusal=True,
        notes="Plausible-sounding request for something the ingested schema data simply does not contain.",
    ),
)
