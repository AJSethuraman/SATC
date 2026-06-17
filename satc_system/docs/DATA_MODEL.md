# SATC System — Data Model

The model is designed to port to SQL with **no restructuring**: stable keys,
normalized line-item tables, no data in merged cells, controlled vocabularies that
become lookup tables. Two physically separated layers.

## Layer 1 — Identity vault (external / access-controlled)

`satc.models.identity` — **SENSITIVE; never serialized into the workbook.**

| Table | Key | Sensitive fields |
|-------|-----|------------------|
| `IdentityRecord` | `client_id` | `legal_name`, `tin` (full SSN/EIN), addresses, contacts |

`IdentityRecord.to_public()` projects to a `PublicClient` containing only
`client_id`, `entity_type`, a non-identifying `display_label`, `tin_last4`,
`tin_masked`, `default_return_type`, and `home_state`. Only the public projection
crosses into the workbook / data mart.

## Layer 2 — Working data mart (the workbook now; SQL later)

`satc.models.mart` — de-identified, keyed by `client_id + tax_year + return_type +
jurisdiction`. Composite keys are built by `satc.ids`.

| Table | Primary key | Notes |
|-------|-------------|-------|
| `PublicClient` | `client_id` | de-identified standing data |
| `ReturnRecord` | `return_key` | one row per client × year × return_type × jurisdiction; pipeline status, residency, refund/balance |
| `LineItem` | `line_item_key` | record-level facts (`schedule`, `line_code`, `amount`, provenance) — every field queryable across years |
| `Carryforward` | `cf_id` | NOL, capital loss, §179, passive, charitable, AMT credit, QBI, state/federal overpayment, FTC; `tax_year_generated`, `applied_to_year`, `expires_after_year` |
| `OwnerBasis` | (`return_key`, `owner_id`, `tax_year`) | per-owner stock/debt basis & capital-account rollforward (1120-S / 1065) |
| `EstimatePayment` | `payment_id` | estimated-payment history |
| `EngagementRecord` | (`client_id`, `tax_year`) | engagement-letter status, fee, invoiced/paid, preparer |
| `DocumentRecord` | `document_id` | repository: doc type, status, date, actor, SharePoint link, note |

### Keys (`satc.ids`)

```
return_key   = client_id | tax_year | return_type | jurisdiction      e.g. SATC-001000|2024|1040|OH
engagement_key = client_id | tax_year
line_item_key  = return_key | schedule | line
```

`return_type ∈ {1040, 1120S, 1065, 1120}`; `jurisdiction = US` (Federal) or a USPS
state code. `client_id` is an opaque handle (`^[A-Z]{2,6}-\d{4,}$`), never a name.

## Provenance (`satc.models.provenance`)

Every staged/computed/stored value carries a `Provenance`: `source_kind`
(`SOURCE_DOC`, `PRIOR_YEAR_CARRYFORWARD`, `DRAKE_OUTPUT`, `PREPARER_ENTRY`,
`COMPUTED`, `TAX_LAW_PARAM`), `confidence`, a `SourceRef` (document_id +
SharePoint link + page + worksheet_title + citation), and a note. Only
`SOURCE_DOC` and `PRIOR_YEAR_CARRYFORWARD` may populate intake fields;
`DRAKE_OUTPUT` is for reconcile / data-mart-seed only.

## Staging (`satc.models.staging`)

`StagedField` / `StagedDocument` hold extracted values awaiting confirmation
(`STAGED` → `CONFIRMED` / `NEEDS_REVIEW` / `REJECTED`). `effective_amount()` /
`effective_text()` return the confirmed value once trusted.

## Review schema (`satc.models.review`)

Shared `Done / Exception / N/A / Note` per checklist item. Exceptions drive the
open-items rollup; `N/A` is excluded from completion %; gating items (e.g. §8867)
block "ready to file".

## SQL portability

Each dataclass maps 1:1 to a table; the `*_key` field is the primary key; lists are
child tables (e.g. `LineItem` → `line_items`). Controlled `Literal` vocabularies
(`PipelineStatus`, `CarryforwardKind`, `DocStatus`, …) become lookup tables. The
workbook renders these as flat grids on the **Data Mart** sheet — a faithful
mirror of the eventual database.

### Multi-preparer / multi-tenant seams

`ReturnRecord.preparer_id` and `EngagementRecord.preparer_id` already exist (solo
default `""`). For a future multi-tenant product, prefix keys / add a `firm_id`
dimension; no table needs restructuring.
