# SchemeSetu source review packet: first five pilot schemes

Prepared 2026-09-28 from the Kaggle-derived pilot and linked government sources. This is an AI-assisted source comparison, **not a human-confirmed review**. No catalog record or evaluation label should be marked verified from this packet. Source dates matter: an older notice may describe an earlier academic year rather than current rules.

| Scheme | Source access | Finding | Current review status |
| --- | --- | --- | --- |
| AICTE Saksham Degree | Linked AICTE PDF available, dated 2021-22 | Three dataset conditions align with section 2; current-year applicability remains open | Historical support; current terms unconfirmed |
| Andaman ST Additional Scholarship | Linked A&N Administration guideline available, dated January 2021 | Course list aligns, but the dataset eligibility excerpt omits ST, domicile and qualifying-study conditions | Incomplete dataset; current terms unconfirmed |
| Andhra Pradesh BOC Workers' Children | Linked G.O. PDF returned HTTP 502 | No official clause text could be checked | Insufficient |
| Assam Combined Merit | Linked 2018-19 PDF and newer 2025-26 DHE notice available | Newer notice says male students only and narrows institution/semester scope; dataset omits these | Material conflict; do not promote rules |
| Bihar Post-Matric | Linked guideline URL returned HTTP 502; 2026-27 official portal available | Portal gives application window, but does not substantiate the dataset's two income thresholds | Thresholds insufficient; scheme appears active for 2026-27 |

## 1. AICTE Saksham Scholarship (Degree)

- Catalog ID: `myscheme-38265a91e80340be`; [myScheme record](https://www.myscheme.gov.in/schemes/sak-deg).
- [AICTE degree guideline PDF](https://www.aicte-india.org/sites/default/files/stdc/AICTE%20Saksham%20Scheme%20Guidelines_Degree.pdf), cover marked 2021-22, section 2. The PDF text supports admission to the first year of a degree or second year by lateral entry in an AICTE-approved institution, disability of at least 40%, and family income of at most ₹8 lakh with a state/UT income certificate.
- These three conditions correspond to the dataset eligibility text. The PDF additionally has conditions in section 8, including the gap after the qualifying examination and restrictions on concurrent financial assistance. The imported eligibility excerpt is therefore not a complete rule set.
- The [Maharashtra DTE scholarship section](https://dte.maharashtra.gov.in/desk-18-e/) listed Saksham Degree in its July 2026 page. The [National Scholarship Portal listing](https://scholarships.gov.in/All-Scholarships) shows Saksham Technical Degree open for 2026-27 (1 June–31 October 2026), but its [Specifications PDF](https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2012_G.pdf) is marked **2020-21**. These pages establish the 2026 application listing, not the current validity of each old eligibility clause. Find a current-year guideline or obtain official clarification before promotion.
- Proposed human action: check the latest year-specific guideline and record each condition, exceptions, dates and exact official passage. Keep `human_confirmed: false`, `verified: false` meanwhile.

## 2. Andaman and Nicobar ST Additional Scholarship

- Catalog ID: `myscheme-442fd8993bcfa9ef`; [myScheme record](https://www.myscheme.gov.in/schemes/sgassbstaniphsaip-sscp10p2c).
- [A&N Administration guideline PDF](https://scholarships.gov.in/public/schemeGuidelines/Andaman/3030_G.pdf), notification dated 15 January 2021, section 3(a)-(h). The dataset's course examples correspond to section 3(b), but its eligibility excerpt does not state the initial conditions: notified ST membership for A&N Islands, A&N domicile, passing senior secondary or a higher qualifying examination, and a recognized regular full-time post-secondary course/institution. Section 3 also describes exclusions and exceptions for repeated stages and classes XI/XII.
- The document gives a broader rule set than the dataset excerpt; a course match alone cannot establish eligibility. Its 2021 date calls for a current-status check.
- Proposed human action: compare every section 3 condition with the current official guidance; record exact clauses and exceptions before creating executable rules.

## 3. Andhra Pradesh BOC Workers' Children Scholarship

- Catalog ID: `myscheme-4b79805c164c8818`; [myScheme record](https://www.myscheme.gov.in/schemes/pscbocw).
- The catalog links [G.O.Ms.No.14 PDF](https://apbocwwb.ap.nic.in/APBOCWW3/2018LETF_MS14.pdf). Both the source review request and a `www`-host retry returned HTTP 502. The dataset mentions worker registration, Chandranna Bima, course levels and a two-child limit, but these remain **unverified** from the linked order.
- Proposed human action: obtain a readable official copy of the order or a current APBOCWWB notice; do not reuse a non-official mirror as ground truth.

## 4. Assam Combined Merit Scholarship

- Catalog ID: `myscheme-f17ece2bc7e807e3`; [myScheme record](https://www.myscheme.gov.in/schemes/cms-g).
- The [catalog-linked DHE PDF](https://directorateofhighereducation.assam.gov.in/sites/default/files/swf_utility_folder/departments/dhe_medhassu_in_oid_4/portlet/level_1/files/Combined%20Merit%20Scholarship.pdf) is a **2018-19** advertisement. It supports 60% marks for degree/master entry, Assam domicile, relevant course and bank-account conditions for that year.
- A [newer Assam DHE advertisement for 2025-26](https://directorateofhighereducation.assam.gov.in/sites/default/files/swf_utility_folder/departments/dhe_medhassu_in_oid_4/menu/document/regarding_publication_of_advertisement_for_combined_merit_scholarship.pdf), page 2, explicitly limits the fresh award to **male students**, first-semester general degree/master courses at specified Assam institutions, with 60% qualifying marks and Assam domicile. The dataset eligibility excerpt does **not** mention the male-only restriction or first-semester/institution limits.
- The newer notice itself refers to session 2024-25 in an advertisement headed 2025-26; this inconsistency should be clarified with DHE before labeling a current-year rule. The 2025 application dates have passed as of this review.
- Proposed human action: treat this as a material source conflict and update the catalog only after identifying the correct current cycle and exact eligibility clauses. Do not use the 2018-19 PDF as current ground truth.

## 5. Bihar Post-Matric Scholarship

- Catalog ID: `myscheme-dfc6438296fab715`; [myScheme record](https://www.myscheme.gov.in/schemes/pmssb).
- The [catalog-linked guideline PDF](https://pmsonline.bih.nic.in/pmsedu2223/(S(05cddllei4wwdyhxtllm3h04))/pms/SamplePdf/PMSPPORTAL2021_Guidelines.pdf) returned HTTP 502. Its URL embeds an older session identifier, so it is not a stable current guideline link.
- The [official Bihar PMS institute portal](https://instpmsonline.bihar.gov.in/2026/pms/pms_online/Default.aspx) states the 2026-27 BC-EBC and SC-ST application window is **15 July–30 September 2026** and directs Bihar-resident students to the portal. It does not establish the dataset's EBC ₹2.5 lakh or OBC ₹3 lakh income limits. Those amounts remain unverified and may represent different scheme variants or years.
- Proposed human action: locate the current BC-EBC scheme notification and SC-ST guidelines separately, then check their income ceilings, domicile and course rules. Keep the dataset's two threshold strings out of executable rules.

## Follow-up checklist

1. A human reviewer opens the cited documents, records exact clauses, page/section, URL and review date in `data/verification/reviews/{scheme_id}.json`.
2. A second reviewer checks conflicts and year-specific conditions, especially Assam and Bihar.
3. Promote only confirmed, complete conditions to `eligibility_rules`; leave all five `verified: false` until the review is complete.
4. Create evaluation cases only after human-confirmed reviews are saved. These five source comparisons are not evaluation labels.
