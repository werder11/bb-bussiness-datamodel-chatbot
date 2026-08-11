# Domain Model: The Microsoft Common Data Model (CDM)

Cleaned-up reference for the business domain concepts this system operates on. Full research trail: [`FINDINGS.md`](../../FINDINGS.md).

## Scope

Two manifests from the [official Microsoft CDM repository](https://github.com/microsoft/CDM) define the ingested scope — see [`FINDINGS.md §3`](../../FINDINGS.md#3-source-repository-map--scope) for the exact file paths:

- **Banking-specific entities** (20) — `RetailBankingCoreDataModel`: Account, Contact, Bank, Branch, Group, GroupMember, CustomerFinancialHolding, FHAccount, FHLineOfCredit, FHInvestment, FHLoan, FHSaving, FICard, FIDirectDebit, FIOverdraft, FIStandingOrder, FinancialHolding, FinancialHoldingInstrument, GroupFinancialHolding, LifeEvent, Relationship.
- **Common/supporting entities** (23) — `core/applicationCommon/...`: Address, BusinessUnit, Currency, SLA, Team, Territory, User, Organization, PriceList, Product, Unit, UnitGroup, Account, Campaign, CampaignResponse, Contact, Lead, Case, FacilityEquipment, Service, ContentSettings, LinkedInCampaign, Segment.

43 entities total. This is the closed vocabulary the [Entity Matcher](../adr/0011-entity-name-matching-closed-vocabulary.md) matches against.

## Document Anatomy

Every `.cdm.json` file shares one shape (full detail: [`FINDINGS.md §4`](../../FINDINGS.md#4-cdm-document-anatomy)):

- `definitions[].entityName`, `.description`, `.extendsEntity` (inheritance), `.exhibitsTraits` (entity-level metadata).
- `hasAttributes[]` — each member is either a **typeAttribute** (scalar field: name, dataType, description) or an **entityAttribute** (a relationship: `entity.entityReference` names the target entity).
- Manifests (`*.manifest.cdm.json`) don't contain schema — just `{entityName, entityPath}` pairs listing which entities belong to a scope.

## Structural Quirks (why the Resolver and Traversal are shaped the way they are)

Three patterns found in the actual data drive several architecture decisions — full detail in [`FINDINGS.md §5`](../../FINDINGS.md#5-the-core-challenge-multi-hop-attribute--relationship-resolution):

### Inheritance splits attributes across files
An entity's full attribute set is rarely in one file — `extendsEntity` chains and shared `attributeGroupReference` libraries compose it from multiple files. Drives [ADR-0007](../adr/0007-resolver-scope-bounded-anti-corruption-layer.md)'s bounded resolution scope.

### Polymorphic relationships
A reusable `customerIdAttribute` group defines a `Customer` as *either* an Account *or* a Contact (`accountOption` / `contactOption`) — the classic Dynamics CRM "who is the customer on this record" pattern. Any entity relationship. Combined with the explicit `Relationship` entity (party-to-party associations, e.g. spouse/lawyer/child), this is *why* "how does Contact relate to Organization" needs two hops, not one — drives [ADR-0009](../adr/0009-relationship-traversal-bounded-to-depth-2.md).

### Name collision: Account and Contact
Both manifests define an entity literally named **Account** and **Contact**, with different, incompatible definitions in different files:

| | Banking-scoped `Account` | Common CRM `Account` |
|---|---|---|
| `extendsEntity` | `CdmEntity` (root) | (CRM inheritance chain) |
| Attributes | 1 (`accountId` only) | dozens, incl. relationships to Lead, Territory, FacilityEquipment, Service |

Disambiguated by source-path namespacing inside the Resolver — see [ADR-0007](../adr/0007-resolver-scope-bounded-anti-corruption-layer.md).

## Canonical Model (this system's representation)

The domain concepts above are resolved into this system's own vendor-independent representation — Entity / Attribute / Relationship / Trait, plus provenance — which is the actual data structure the rest of the system operates on. See [Architecture: Components](../architecture/components.md) for where it sits in the pipeline, [ADR-0007](../adr/0007-resolver-scope-bounded-anti-corruption-layer.md) for how it's built, and [ADR-0021](../adr/0021-schema-based-design-at-port-boundaries.md) for its concrete schema.
