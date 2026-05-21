# Section Prep — 2026-05-21

**Current session:** 2026-05-27 (Wednesday) — Week 9: Community-Led Justice — *Data Ownership (Indigenous Nations examples)*
**Previous session:** 2026-05-20 (Wednesday) — Week 8: Environmental Justice

---

## Previous Lecture (2026-05-20)

*No lecture deck found for 2026-05-20.*

The Environmental Justice session covered Week 8 themes: how AI and health technology systems generate environmental burdens distributed along lines of race, class, and global geography. Crawford's "Earth" chapter (committed PDF, assigned Monday May 18) anchors the week's conceptual framework; the Wednesday readings (Cornell SAHAI framework and *Sustainable AI in Medicine*) situate that framework in healthcare settings.

---

## Previous Session Readings (due 2026-05-20)

### 1. Crawford, Kate — "Earth," *The Atlas of AI* (Yale UP, 2021), Chapter 1 [PDF — summarized from extracted text]

*Note: section_prep.py matched the citation "Balancing the Promise of Healthcare AI with Its Carbon Costs" to this committed PDF with low confidence (score 0.333). The Crawford chapter was assigned Monday May 18; its PDF is committed in the Week 8 folder. A separate summary of the actual Cornell article (the May 20 citation) follows as entry 1b. The Crawford chapter is summarized here from the full extracted text.*

Kate Crawford opens *The Atlas of AI* with a physical journey to Silver Peak, Nevada—the only operating U.S. lithium mine—to materialize what the tech industry abstracts as "the cloud." Her central argument is that AI is a **megamachine** (invoking Lewis Mumford): an opaque assemblage of extraction, logistics, and labor whose true costs are systematically concealed from the cities and corporations that profit most. Crawford traces a **logic of extraction** across multiple scales and centuries: rare earth mining in Inner Mongolia that has created a toxic lake holding 180 million tons of waste powder; gray-market tin miners in Indonesia's Bangka Islands scraping seabeds from makeshift pontoons; Congo's "conflict minerals" financing militia warfare; and the Victorian near-extinction of Malaysia's Palaquium gutta tree to insulate telegraph cables. She argues these are not isolated episodes but a **planetary mine**—a diffuse, globally distributed infrastructure of depletion that predates AI but is now intensified by it. The "clean tech" myth is punctured with data: training a single NLP model emits 660,000 pounds of CO₂; China's data centers drew 73 percent of power from coal in 2018; shipping vessels emit as much pollution as 50 million cars each. For justice, Crawford insists that the costs of computation are always externalized onto communities near mines, low-paid maritime workers, and ecosystems degraded by e-waste, while the greatest benefits accrue to a handful of tech corporations and their shareholders. The ghost town of Blair, Nevada—a twelve-year boom that poisoned the ground and collapsed—serves as her closing emblem for Silicon Valley's current extractive moment.

---

### 1b. "Balancing the Promise of Healthcare AI with Its Carbon Costs" — *NEJM Catalyst* / Cornell Chronicle, September 2025

*(external link, paywalled — summarized from citation + secondary sources)*

Researchers at Cornell Tech (Chethan Sarabu, Udit Gupta) and Stanford School of Medicine (lead author Anu Ramachandran) published the **SAHAI (Sustainably Advancing Health AI)** framework in *NEJM Catalyst* in September 2025. The paper argues that health systems are deploying AI tools with no methodology to account for their environmental footprint—a structural blind spot that reproduces in healthcare the "clean tech" mythology Crawford identifies. As a proof-of-concept, the authors calculated that a single AI-powered physician messaging tool, with 3,000 physicians each answering 50 messages per day for one year, produces approximately **48,000 kg of CO₂**—around 2,300 "tree-years"—plus substantial water consumed for data center cooling. SAHAI provides decision-makers a framework to factor greenhouse gas emissions and water use into AI procurement *before* deployment. Practical recommendations include preferring smaller or quantized models when clinical performance is equivalent, batching inference requests, and sourcing data center power from renewables. For justice, the paper operationalizes Crawford's externality argument: the carbon and water costs of "digital health" fall not on elite hospitals adopting the tools but on communities hosting data centers and mining hardware minerals—a spatial injustice invisible to most clinicians and administrators.

---

### 2. "Sustainable AI in Medicine: Navigating Innovation, Challenges, and Environmental Impact" — *Health Economics Review*, 2025

*(external link, paywalled — summarized from citation + secondary sources)*

This review examines the tension between AI's expanding clinical applications and its growing environmental footprint, arguing that sustainability must become a first-class governance criterion alongside accuracy and safety. The authors map environmental costs across three dimensions: **carbon emissions** from energy-intensive model training and inference; **water consumption** for cooling the data centers that run medical AI; and **electronic waste** from the short lifecycle of AI hardware. The justice argument is that these costs concentrate near extraction sites, data centers, and informal e-waste hubs in the Global South—not in the wealthy health systems that benefit from the tools. Mitigation strategies range from technical (model compression, batched inference, renewable procurement, waste heat reuse, circular hardware economy) to institutional (mandatory lifecycle assessments). Crucially, the authors also argue that AI can *reduce* medicine's overall environmental footprint: telemedicine and remote monitoring cut travel and facility use; AI-optimized supply chains reduce pharmaceutical and material waste. The paper calls on individual clinicians to treat model selection and query frequency as an ethical responsibility comparable to clinical resource stewardship. Within the course's justice framework, this piece extends Crawford's argument from *building* AI (mines, logistics) to *operating* it at clinical scale—showing that environmental harm is embedded throughout the AI lifecycle, not only in hardware supply chains.

---

## Current Session Readings (due 2026-05-27)

*Note: Memorial Day (May 25) and May 26 discussion sections are canceled. The next session is Wednesday May 27, with guest lecturer **Krystal Tsosie, PhD, MPH, MA** (Diné/Navajo Nation).*

---

### 3. Anderson MZ, Tsosie KS, et al. — "A Tribal Data Repository to Advance Indigenous Health and Sovereignty" — *Nature Genetics* 57(11), 2025

*(external link, paywalled — summarized from citation + secondary sources)*

Anderson, Tsosie (Diné/Navajo Nation; co-founder of NativeBio, the first U.S. Indigenous-led biobank), and 20 co-authors describe the first federally funded Tribal data repository: the **DI³TDR (Data for Indigenous Implementations, Interventions, and Innovations Tribal Data Repository)**, supported by a 2023 NIH $9 million award. The paper's central argument is that conventional open-science infrastructure—built around FAIR principles, institutional ownership, and maximal researcher access—is structurally incompatible with Indigenous data sovereignty. The DI³TDR inverts this default: researchers can access data from participating Tribal Nations only under governance frameworks controlled by those nations, aligning with the CARE Principles (Collective Benefit, Authority to Control, Responsibility, Ethics). The paper responds directly to the Havasupai case and the broader history of extractive biomedical research by creating durable institutional infrastructure that embeds consent and community governance rather than leaving them to individual investigators' discretion. A key technical argument is that federated architectures can preserve Tribal sovereignty while enabling inter-tribal analyses that individual nations could not otherwise conduct. For justice, the paper frames data governance as an extension of land sovereignty: just as colonialism dispossessed Indigenous peoples of physical territory, extractive biomedical research dispossesses communities of genomic and health data. The DI³TDR is presented as a structural remedy—not a policy recommendation—that shifts power from researchers and institutions to communities and connects directly to the course's themes of who controls data as a form of who controls community futures.

---

### 4. Mello, M. M., & Wolf, L. E. — "The Havasupai Indian Tribe Case—Lessons for Research Involving Stored Biologic Samples" — *NEJM* 363(3), 2010

*(external link, paywalled — summarized from citation + secondary sources)*

In 2010, Arizona State University settled with 41 Havasupai Tribe members for $700,000 after a decade-long lawsuit. Havasupai members had donated blood samples in the 1990s for a diabetes genetics study; researchers then used those samples—without additional consent—for studies on schizophrenia, population migration patterns, and inbreeding. Mello and Wolf use the case to diagnose a structural failure of informed consent for biospecimens. Their key argument is that standard "broad consent" for future research is inadequate when the study population holds cultural or spiritual beliefs that make certain secondary uses not just unapproved but deeply offensive: the Havasupai regard blood and ancestry as sacred, making psychiatric and migration studies a violation of community identity rather than merely a procedural breach. The case reveals **clashing values**: researchers' interest in maximizing use of rare, high-quality samples versus communities' interest in controlling how their genetic heritage is represented and used. Mello and Wolf recommend layered consent protocols with community-specific deliberation, particularly for Indigenous populations with documented histories of exploitation. The justice argument is structural: standard informed consent was designed around individual autonomy but systematically fails communities whose interests are collective. The Havasupai case makes visible how biomedical institutions can extract biological and genomic resources from Indigenous communities under a veneer of consent—reproducing the logic of physical extraction in a medical register, and providing the concrete case that motivates both the CARE Principles and the DI³TDR infrastructure.

---

### 5. CARE Principles for Indigenous Data Governance — Global Indigenous Data Alliance, 2019

*(external link, paywalled — summarized from citation + secondary sources)*

The CARE Principles were developed in 2019 by the International Indigenous Data Sovereignty Interest Group (Research Data Alliance) as a people-and-purpose counterpart to the data-properties-focused FAIR principles. Where FAIR asks "what should data look like?", CARE asks "whose interests does data use serve?" The four principles:

- **C — Collective Benefit:** Indigenous data use must generate tangible benefits for Indigenous collectives—inclusive development, improved governance, equitable outcomes—not merely advance external research agendas. Data practices that extract value without returning it violate this principle.

- **A — Authority to Control:** Indigenous peoples have the right to determine how their cultures, knowledges, lands, and peoples are represented in data, to develop culturally grounded governance protocols, and to be active leaders in stewardship and access decisions—not merely consulted.

- **R — Responsibility:** Those working with Indigenous data bear an affirmative obligation to support Indigenous data literacy, workforce capacity, and self-determination. Responsibility is a relational, ongoing commitment, not a one-time compliance checkbox.

- **E — Ethics:** Data practices must minimize current and future harm, refuse deficit framing, and respect Indigenous worldviews and ontologies rather than imposing Western scientific frameworks. This includes refusing uses that stigmatize or misrepresent Indigenous peoples.

CARE is a values framework designed to shift the default from institutional control to Indigenous self-governance. For the course's justice themes, it reframes data as a site of sovereignty: the right to control one's data is inseparable from political, cultural, and epistemic self-determination. Together with Mello & Wolf (the problem) and Anderson et al. (the structural solution), CARE forms a conceptual trilogy for understanding how justice can be built into data infrastructure rather than grafted onto it after the fact.

---

## Source Notes

| Entry | Provenance |
|---|---|
| Crawford "Earth" (entry 1) | Summarized from committed PDF extracted text — primary source |
| Cornell SAHAI article (entry 1b) | External link, publisher page returned HTTP 403 — summarized from citation + secondary sources (Cornell Chronicle, MirageNews, Inc. magazine) |
| Sustainable AI in Medicine (entry 2) | External link, publisher page returned HTTP 403 — summarized from citation + secondary sources (PubMed, Nature Reviews, Health Affairs, Yale School of Medicine) |
| Anderson et al. 2025 (entry 3) | External link, publisher page (Nature Genetics) returned HTTP 403 — summarized from citation + secondary sources (ASU News, R Discovery, ScienceNews) |
| Mello & Wolf 2010 (entry 4) | External link, publisher page (NEJM) returned HTTP 403 — summarized from citation + secondary sources (SSRN, PMC, PubMed, Seeds of Native Health PDF) |
| CARE Principles 2019 (entry 5) | External link, gida-global.org returned HTTP 403 — summarized from citation + secondary sources (Wikipedia, Data Science Journal, ARDC, Ada Lovelace Institute) |
