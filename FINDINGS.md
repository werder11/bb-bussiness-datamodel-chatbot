# CDM RAG Chatbot — Research Findings & Decision Log

Reference layer for the [reeeliance](https://github.com) "Business Data Model Chatbot" case study. Purpose: capture what we've learned about the task and the source data *before* committing to an architecture, so implementation decisions can be made deliberately and revisited here later.

- Task brief (source of truth): [`Business data model chatbot - task for Senior Data & AI Architect.pdf`](./Business%20data%20model%20chatbot%20-%20task%20for%20Senior%20Data%20%26%20AI%20Architect.pdf)
- Source repo (sparse-cloned locally): [`cdm-source/`](./cdm-source/) ← [microsoft/CDM](https://github.com/microsoft/CDM) on GitHub
- Local clone scope: only `schemaDocuments/` was checked out (`git sparse-checkout set schemaDocuments`). No Python SDK lives in this repo.
- **Architecture base (accepted):** [`docs/README.md`](./docs/README.md) — the full layered documentation system (vision, architecture, domain, design, quality, decisions, API, operations) built on the findings below. This document remains the research reference; the architecture is now recorded separately as the system of record for "why we built it this way."

---

## 1. Task Brief

**Objective:** Build a Python **FastAPI** service implementing a RAG pipeline that lets a user query the Microsoft **Common Data Model (CDM)** in natural language — which entities exist, their attributes, and their relationships.

| # | Requirement | Detail |
|---|---|---|
| 1 | [Data Ingestion](#3-source-repository-map--scope) | Parse CDM definitions from the official repo, scoped to the **Banking Model** + common objects; store in a Vector DB of choice |
| 2 | [RAG Pipeline](#5-the-core-challenge-multi-hop-attribute--relationship-resolution) | Retrieval chain must answer entity/attribute/relationship questions, grounded (non-hallucinated) in retrieved CDM context |
| 3 | Code Quality & DevOps | FastAPI backend, unit tests for retrieval logic, Dockerfile |
| 4 | Self-intro slide | "How do I see myself as a Senior Data & AI Architect at reeeliance?" — strengths, experience, role evolution (separate from the code deliverable) |

**Example questions the system must answer:**
- "What are the core attributes of the 'Account' entity?"
- "How does a 'Contact' relate to an 'Organization'?"

## 2. Deliverables Checklist (for the 3rd interview)

- [ ] GitHub repository link with source code
- [ ] Live demo of the API
- [ ] Technical walkthrough, **max 4 slides**, covering: embedding strategy + how data relationships were handled
- [ ] Self-intro slide (see requirement 4 above)

## 3. Source Repository Map & Scope

Two manifests define the scope named in the brief ("Banking Model and common objects"):

**A. Banking-specific entities** — [`FinancialServices/RetailBankingCoreDataModel/RetailBankingCoreDataModel.manifest.cdm.json`](./cdm-source/schemaDocuments/FinancialServices/RetailBankingCoreDataModel/RetailBankingCoreDataModel.manifest.cdm.json) ([GitHub](https://github.com/microsoft/CDM/blob/master/schemaDocuments/FinancialServices/RetailBankingCoreDataModel/RetailBankingCoreDataModel.manifest.cdm.json)) — 20 entities:

| Entity | File |
|---|---|
| Account | [`Account.cdm.json`](./cdm-source/schemaDocuments/FinancialServices/RetailBankingCoreDataModel/Account.cdm.json) ⚠️ [name collision](#name-collision-account--contact) |
| Contact | [`Contact.cdm.json`](./cdm-source/schemaDocuments/FinancialServices/RetailBankingCoreDataModel/Contact.cdm.json) ⚠️ [name collision](#name-collision-account--contact) |
| Bank | [`Bank.cdm.json`](./cdm-source/schemaDocuments/FinancialServices/RetailBankingCoreDataModel/Bank.cdm.json) |
| Branch | [`Branch.cdm.json`](./cdm-source/schemaDocuments/FinancialServices/RetailBankingCoreDataModel/Branch.cdm.json) |
| Group | [`Group.cdm.json`](./cdm-source/schemaDocuments/FinancialServices/RetailBankingCoreDataModel/Group.cdm.json) |
| GroupMember | [`Groupmember.cdm.json`](./cdm-source/schemaDocuments/FinancialServices/RetailBankingCoreDataModel/Groupmember.cdm.json) |
| CustomerFinancialHolding | [`Customerfinancialholding.cdm.json`](./cdm-source/schemaDocuments/FinancialServices/RetailBankingCoreDataModel/Customerfinancialholding.cdm.json) |
| FHAccount | [`Fh_account.cdm.json`](./cdm-source/schemaDocuments/FinancialServices/RetailBankingCoreDataModel/Fh_account.cdm.json) |
| FHLineOfCredit | [`Fh_creditline.cdm.json`](./cdm-source/schemaDocuments/FinancialServices/RetailBankingCoreDataModel/Fh_creditline.cdm.json) |
| FHInvestment | [`Fh_investment.cdm.json`](./cdm-source/schemaDocuments/FinancialServices/RetailBankingCoreDataModel/Fh_investment.cdm.json) |
| FHLoan | [`Fh_loan.cdm.json`](./cdm-source/schemaDocuments/FinancialServices/RetailBankingCoreDataModel/Fh_loan.cdm.json) |
| FHSaving | [`Fh_saving.cdm.json`](./cdm-source/schemaDocuments/FinancialServices/RetailBankingCoreDataModel/Fh_saving.cdm.json) |
| FICard | [`Fi_card.cdm.json`](./cdm-source/schemaDocuments/FinancialServices/RetailBankingCoreDataModel/Fi_card.cdm.json) |
| FIDirectDebit | [`Fi_directdebit.cdm.json`](./cdm-source/schemaDocuments/FinancialServices/RetailBankingCoreDataModel/Fi_directdebit.cdm.json) |
| FIOverdraft | [`Fi_overdraft.cdm.json`](./cdm-source/schemaDocuments/FinancialServices/RetailBankingCoreDataModel/Fi_overdraft.cdm.json) |
| FIStandingOrder | [`Fi_standingorder.cdm.json`](./cdm-source/schemaDocuments/FinancialServices/RetailBankingCoreDataModel/Fi_standingorder.cdm.json) |
| FinancialHolding | [`Financialholding.cdm.json`](./cdm-source/schemaDocuments/FinancialServices/RetailBankingCoreDataModel/Financialholding.cdm.json) |
| FinancialHoldingInstrument | [`Financialholdinginstrument.cdm.json`](./cdm-source/schemaDocuments/FinancialServices/RetailBankingCoreDataModel/Financialholdinginstrument.cdm.json) |
| GroupFinancialHolding | [`Groupfinancialholding.cdm.json`](./cdm-source/schemaDocuments/FinancialServices/RetailBankingCoreDataModel/Groupfinancialholding.cdm.json) |
| LifeEvent | [`Lifemoment.cdm.json`](./cdm-source/schemaDocuments/FinancialServices/RetailBankingCoreDataModel/Lifemoment.cdm.json) |
| Relationship | [`Relationship.cdm.json`](./cdm-source/schemaDocuments/FinancialServices/RetailBankingCoreDataModel/Relationship.cdm.json) — explicit party-to-party relationship entity, see [§5](#relationship-as-a-first-class-entity) |

**B. Common/supporting entities** — [`manifests/bankingAccelerator.manifest.cdm.json`](./cdm-source/schemaDocuments/manifests/bankingAccelerator.manifest.cdm.json) ([GitHub](https://github.com/microsoft/CDM/blob/master/schemaDocuments/manifests/bankingAccelerator.manifest.cdm.json)) — 23 entities, all under [`core/applicationCommon/`](./cdm-source/schemaDocuments/core/applicationCommon/):

| Entity | Path (relative to `core/applicationCommon/`) |
|---|---|
| Address, BusinessUnit, Currency, SLA, Team, Territory, User | `*.cdm.json` (top level) |
| Organization, PriceList, Product, Unit, UnitGroup | `foundationCommon/*.cdm.json` |
| Account ⚠️, Campaign, CampaignResponse, Contact ⚠️, Lead | `foundationCommon/crmCommon/*.cdm.json` |
| Case, FacilityEquipment, Service | `foundationCommon/crmCommon/service/*.cdm.json` |
| ContentSettings, LinkedInCampaign, Segment | `foundationCommon/crmCommon/solutions/marketing/*.cdm.json` |

Direct links: [Account](./cdm-source/schemaDocuments/core/applicationCommon/foundationCommon/crmCommon/Account.cdm.json) · [Contact](./cdm-source/schemaDocuments/core/applicationCommon/foundationCommon/crmCommon/Contact.cdm.json) · [Organization](./cdm-source/schemaDocuments/core/applicationCommon/foundationCommon/Organization.cdm.json) · [Lead](./cdm-source/schemaDocuments/core/applicationCommon/foundationCommon/crmCommon/Lead.cdm.json)

No Python SDK is present in this repo — only schema JSON. The official `commondatamodel-objectmodel` PyPI package is a separate, heavier SDK originally paired with the now-decommissioned CDM Schema Store (see [repo README notice](./cdm-source/README.md)); it's a candidate for resolution logic (see [§7](#7-open-architecture-decisions)) but not required.

## 4. CDM Document Anatomy

Every `*.cdm.json` file has the same shape:

```
{
  imports: [ { corpusPath } ],           // cross-file references, incl. shared trait/attribute-group libraries
  definitions: [ {
    entityName, description, extendsEntity,   // inheritance — see §5
    exhibitsTraits: [...],                     // entity-level metadata (versioning, localization)
    hasAttributes: [ { attributeGroupReference: { members: [ ... ] } } ]
  } ]
}
```

Each member of `hasAttributes[].attributeGroupReference.members` is one of:

- **typeAttribute** — a scalar field: `name`, `dataType` (`string` / `dateTime` / `currency` / `entityId` / ...), `description`, `isNullable`, `appliedTraits`. Example: [`Account.cdm.json:41` `accountId`](./cdm-source/schemaDocuments/FinancialServices/RetailBankingCoreDataModel/Account.cdm.json).
- **entityAttribute** — a **relationship**: has `entity.entityReference` pointing to the *name* of another entity, plus a `name` for the foreign-key-like attribute. Example: [`core/applicationCommon/foundationCommon/crmCommon/Account.cdm.json:30-41`](./cdm-source/schemaDocuments/core/applicationCommon/foundationCommon/crmCommon/Account.cdm.json) — `originatingLead` → `entityReference: "Lead"`; same file also has `preferredEquipment` → `FacilityEquipment`, `preferredService` → `Service`, `territory` → `Territory`.

Manifests (`*.manifest.cdm.json`) don't contain schema — they just list `{ entityName, entityPath }` pairs that say which entities belong to a given model/scope (see [§3](#3-source-repository-map--scope) tables, extracted from exactly these files).

## 5. The Core Challenge: Multi-Hop Attribute & Relationship Resolution

This is the central design problem for ingestion — **an entity's full attribute/relationship set is rarely in one file.** Three concrete patterns found in the data:

### Inheritance splits attributes across files
[`FinancialServices/RetailBankingCoreDataModel/Account.cdm.json`](./cdm-source/schemaDocuments/FinancialServices/RetailBankingCoreDataModel/Account.cdm.json) declares only **one** attribute (`accountId`) and sets `extendsEntity: "CdmEntity"` (the root type — not the common Account). A naive single-file parse would report Account as having one attribute, which is wrong/misleading for the RAG answer to "what are Account's core attributes."

[`core/applicationCommon/foundationCommon/Organization.cdm.json`](./cdm-source/schemaDocuments/core/applicationCommon/foundationCommon/Organization.cdm.json) is thinner still — it adds one attribute (`schedulingEngine`) and sets `extendsEntity: "base_Organization/Organization"`. The `base_Organization` entity isn't a literal file in this repo; it's a CDS "base" shape resolved by the SDK's resolution machinery from shared definitions (`_allImports.cdm.json` chains). **Full resolution requires either the official SDK's resolver, or accepting partial/approximate resolution and documenting the limitation.**

### Polymorphic relationships ("Customer" = Account or Contact)
[`core/wellKnownCDSAttributeGroups.cdm.json:4129-4166`](./cdm-source/schemaDocuments/core/wellKnownCDSAttributeGroups.cdm.json) defines a reusable `customerIdAttribute` group: an inline polymorphic `Customer` entity shape with two options — `contactOption` (`entityReference: "Contact"`) and `accountOption` (`entityReference: "Account"`), `purpose: "referencesCustomer"`. This is the classic Dynamics CRM pattern where a single logical relationship ("who is the customer on this record") can resolve to *either* entity type. Any entity using this shared group (Case, Opportunity, etc.) inherits this ambiguity — a naive "one entityReference = one target" assumption breaks here.

### `Relationship` as a first-class entity
[`FinancialServices/RetailBankingCoreDataModel/Relationship.cdm.json`](./cdm-source/schemaDocuments/FinancialServices/RetailBankingCoreDataModel/Relationship.cdm.json) (1151 lines) models party-to-party relationships explicitly as *data*, not just schema — e.g. "denotes an association between one contact to another... spouse, lawyer, child, grandparent" (line 59), with an attribute for "the contact who owns the relationship" (~line 832). This is likely the most direct answer path for "how does a Contact relate to an Organization/other party" — worth surfacing prominently in retrieval rather than only relying on inferred entityAttribute links.

### Name collision: Account & Contact
Both manifests define an entity literally named **Account** and **Contact**, in different files, with different (incompatible) definitions:

| | Banking-scoped `Account` | Common CRM `Account` |
|---|---|---|
| File | [`FinancialServices/.../Account.cdm.json`](./cdm-source/schemaDocuments/FinancialServices/RetailBankingCoreDataModel/Account.cdm.json) | [`core/.../crmCommon/Account.cdm.json`](./cdm-source/schemaDocuments/core/applicationCommon/foundationCommon/crmCommon/Account.cdm.json) |
| `extendsEntity` | `CdmEntity` (root) | (CRM inheritance chain) |
| Attributes | 1 (`accountId` only) | dozens, incl. relationships to Lead, Territory, FacilityEquipment, Service |

**Implication:** ingestion needs a disambiguation strategy (namespace by source path, disambiguate by manifest scope, or merge/reconcile) — this alone is a good candidate for the "how did you handle data relationships" slide.

## 6. Repository Layout Notes

- Root [`README.md`](./cdm-source/README.md) confirms: no Python SDK ships in this repo; points to [Entity Reference Index](https://github.com/microsoft/CDM/tree/master/schemaDocuments#directory-of-cdm-entities) and a [Visual Entity Navigator](https://microsoft.github.io/CDM/) for interactive exploration.
- Versioned files exist per entity (e.g. `Account.1.0.cdm.json` alongside `Account.cdm.json`) — the un-suffixed file is the latest/canonical version; ingestion should ignore the numbered historical variants unless versioning is explicitly in scope.
- `schemaDocuments/core/` alone is ~54k lines of JSON across all files — the manifest-driven entity list (§3) is what actually bounds ingestion scope, not the whole `core/` tree.

## 7. Open Architecture Decisions

All rows are now **decided**. The first four (vendor-level picks) were resolved as [ADR-0023](./docs/adr/0023-tech-layer-adapters.md); the last two (architectural shape) were resolved earlier as ADR-0007/0009.

| Decision | Options on the table | Notes |
|---|---|---|
| Vector DB | ~~ChromaDB (embedded, zero-infra) · Qdrant (own container) · FAISS (library only, no metadata filter) · pgvector~~ | **Decided:** ChromaDB, embedded. See [ADR-0023](./docs/adr/0023-tech-layer-adapters.md). |
| LLM provider | ~~Anthropic Claude · OpenAI · local (Ollama)~~ | **Decided:** Anthropic Claude (default), Google Gemini added as a free-tier-testable second provider — swappable via `LLM_PROVIDER`. See [ADR-0023](./docs/adr/0023-tech-layer-adapters.md) and [ADR-0024](./docs/adr/0024-second-llm-provider-gemini.md). |
| Embedding model | ~~Local `sentence-transformers` (free, offline) · OpenAI `text-embedding-3-small` · match LLM vendor~~ | **Decided:** local `sentence-transformers` (`all-MiniLM-L6-v2`). See [ADR-0023](./docs/adr/0023-tech-layer-adapters.md). |
| Chunking granularity | ~~One document per entity (name+desc+all attrs+relations as text) · one per attribute · one per relationship~~ | **Decided:** one chunk per entity. See [ADR-0023](./docs/adr/0023-tech-layer-adapters.md). |
| Relationship resolution | ~~Custom lightweight resolver · full SDK · document as limitation~~ | **Decided:** custom resolver, single-hop `extendsEntity`/`attributeGroupReference`, scope explicitly bounded and documented, official SDK kept as an optional future adapter. See [ADR-0007](./docs/adr/0007-resolver-scope-bounded-anti-corruption-layer.md); relationship *traversal* depth decided in [ADR-0009](./docs/adr/0009-relationship-traversal-bounded-to-depth-2.md). |
| Entity name collisions | ~~Namespace by path · prefer banking scope · surface both~~ | **Decided:** namespace by source-path, handled inside the Resolver. See [ADR-0007](./docs/adr/0007-resolver-scope-bounded-anti-corruption-layer.md). |

## 8. Next Steps

Superseded by the implementation plan — see `.docs/adhoc/cdm-rag-chatbot/cdm-rag-chatbot-tasks.md` for the live, phase-by-phase checklist. All items originally listed here (tech picks, resolver prototyping, scaffolding) are now tracked there instead of duplicated in this file.
4. Draft the 4-slide technical walkthrough and the self-intro slide.
