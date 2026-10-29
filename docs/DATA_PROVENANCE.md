# Data source and provenance

## Verified source

- **Publisher:** Telecommunications and Digital Government Regulatory Authority (TDRA).
- **Title:** `TDRA Service Transcation 2025` (publisher archive-member filename, including its spelling).
- **Official portal:** https://tdra.gov.ae/en/open-data/data-sets
- **Actual download:** https://tdra.gov.ae/api/sitecore/OpenDataDGT/DownloadALlDataSets
- **Reuse conditions:** https://tdra.gov.ae/en/open-data/open-data-policy
- **Retrieval:** 29 October 2026. Source workbook: 2025. Exact publisher release date: not confirmed.
- **Original:** `data/tdra-service-transactions-2025.xlsx`. The archive member has a `.zip` suffix but contains XLSX workbook bytes. It was opened and its worksheets inspected. The original workbook is preserved.
- **Snapshot and checksum:** `data/source-snapshot.json`. SHA-256 records the original workbook bytes.

The official policy describes reuse with attribution, public sharing under the open-data principle, and additional stated restrictions on uses. A standard named licence is **not confirmed**. Refer to the full publisher terms rather than assuming an unrestricted licence. This note is not legal advice or a determination of organizational applicability.

## Fields and transformations

The summary worksheet `مخلص البيانات` contains the original service name and total transactions for 2025. The snapshot retains 11 service rows and the published total row with original row numbers. Surrounding label whitespace was trimmed. Counts were not altered. The detail worksheet contains 132 monthly rows. ModelFit uses summary facts, not personal data.

Examples: summary row 11 has 6,221 inquiry transactions; row 10 has 9,488 complaint transactions; row 9 has 6,375 telecom-equipment registration and approval transactions. Four evaluation examples ask about these facts in English or Arabic and cite the relevant row. A refusal case asks whether counts establish service fees (they do not); a synthetic human-escalation case is grounded in the service's configured exclusions.

Questions, English translations, scope rubrics, fictional models, governance records and model outputs are human-authored/synthetic. They are not original dataset facts. All model outputs are simulated; no measured supplier benchmark is claimed. Source verification and model-performance verification are separate.

## Update approach and limits

Manual refresh: download official archive → identify workbook → compare checksum → inspect changed source facts → version the snapshot → record a data-context event → review affected findings. No live provider or dataset polling is connected. Counts establish neither fees nor eligibility, processing times, government AI obligations, nor individual case outcomes. Open data is a source corpus, not a policy rulebook.

All governance requirements in this prototype originate in the user's service brief and explicit service-owner configuration. Their displayed validation status is "Prototype choice, awaiting governance validation." No UAE legal rule has been inferred from this dataset.
