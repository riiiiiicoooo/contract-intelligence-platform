# User Research: Contract Due Diligence Workflows in M&A Legal Practice

**Research Period**: October–December 2024
**Conducted by**: Jacob George, Product Manager
**Methodology**: In-depth interviews during active deal cycles, workflow observation, document analysis
**Status**: Final Report

## Research Objectives

Before building an AI-assisted contract intelligence platform for M&A legal, we needed to understand:

- How do M&A attorneys actually review contracts? (Not the theoretical approach, but the pragmatic one under time pressure)
- How do associates triage thousands of documents in a limited timeframe?
- Where do bottlenecks occur in contract review?
- What does "good enough" accuracy look like in this domain?
- How do privilege and confidentiality requirements constrain tool design?
- What would genuinely reduce review time vs. what sounds helpful but doesn't?

**Hypothesis We Were Testing**: Associates read contracts sequentially. We hypothesized they actually triage by risk, jumping between documents to cross-reference clauses.

---

## Methodology

**Interview Participants**: 6 attorneys at 2 mid-size M&A firms
- 2 Partners (15+ years, deal leadership)
- 2 Senior Associates (5–8 years, complex document review)
- 1 Junior Associate (2 years, document organization and initial triage)
- 1 Compliance Officer (privilege preservation, data handling)

**Interview Context**: All interviews conducted during active deal preparation (M&A deals in diligence phase, 3–6 week timeline to close).

**Data Collection**:
- Observed document review workflow in 2 deal rooms (shadowed 4 hours each)
- Recorded redacted contract samples and marking patterns
- Analyzed document metadata and review timelines from 3 completed deals
- Asked about pain points, current tooling, and priority features

**Scope**:
- Deal size: $50M–$500M
- Document volume: 500–3,000 contracts per deal
- Document types: Customer contracts, vendor agreements, IP assignments, NDAs, employment agreements, financing arrangements

---

## Participant Profiles

**P1: M&A Partner, 15 years, Deal Leadership**
- Leads 6–8 deals per year in the $50M–$500M range
- Responsible for deal structure, compliance, legal risk assessment
- Spends ~40% of deal time on contract review
- Main concern: Partner has reviewed contracts for 15 years; wants confidence scores, not automation. "I know what I'm looking for. I don't need the tool to find it. I need the tool to tell me what I might have missed and how confident I should be that I didn't miss it."

**P2: M&A Partner, 12 years, Volume Deals**
- Handles more frequent, smaller deals ($50M–$200M)
- Relies on playbooks and standardized checklists
- Wants speed without sacrificing accuracy
- "If I could compress the 3-week review timeline to 2 weeks without sacrificing anything, that's a $200K value per deal in partner time."

**P3: Senior Associate, 7 years, Complex Document Review**
- Reviews high-risk documents (IP, change of control, financing)
- Deep expertise in clause interactions and gotchas
- "The hard part isn't reading a single clause. The hard part is knowing that clause X conflicts with clause Y in a different document."
- Often handles post-signing amendments and modifications

**P4: Senior Associate, 5 years, Integration and Data Room Management**
- Organizes deal rooms, manages document workflows
- Partners with tech vendors on OCR, document management
- Pragmatic about document quality: "50% of our documents are 20+ year old contracts that are scanned PDFs with handwritten amendments. OCR is broken on these."

**P5: Junior Associate, 2 years, Document Triage and Initial Review**
- First pass on contracts, tags by risk level
- Rarely finds issues that senior associates miss, but occasionally catches major ones
- Wants clear guidance on what to flag: "I'm not confident in my judgment. I want to know: is this clause important for this deal? Or am I wasting everyone's time?"

**P6: Compliance Officer, Contract Law Background**
- Manages privilege preservation, data handling, export controls
- Reviews AI tools for compliance risk
- "Every tool you want to use has to maintain attorney-client privilege. If data leaves the firm, privilege might be waived. If you lose privilege, the deal could be at risk. So tools need to be on-prem or have very specific data handling guarantees."

---

## Key Findings

### 1. Associates Don't Read Contracts Linearly—They Triage by Risk Tier

Our hypothesis was correct, but the details revealed a more nuanced workflow than expected.

**From P3's Workflow Observation**:

Deal room setup: 2,000+ contracts across 8 folders (customer contracts, vendor agreements, employment, IP, financing, etc.).

P3's approach:
1. **Day 1–2**: Skim all customer contracts (500 docs). Rate by risk: "Change of control? High risk." "Exclusive territory clause? Medium risk." "Renewal terms? Low risk."
2. **Day 3–4**: Deep dive on high-risk docs. Read carefully, highlight clauses, cross-reference with deal summary.
3. **Day 5–6**: Deep dive on medium-risk docs. Less scrutiny, focus on potential conflicts.
4. **Day 7**: Quick pass on low-risk docs (mostly reading headings, spot-checking key sections).
5. **Throughout**: When a question arises about a specific clause or term, immediately search across all documents for related language.

**Quote from P3**:
"I don't read sequentially. I read strategically. First, I identify what could kill the deal. Then I focus on those. Everything else is secondary."

**From P4's Observation**:

"Initial triage is a screening process. I'm not looking for issues—I'm looking for flags. 'Does this contract have a change of control clause? Yes? High priority.' 'Does it have exclusivity? Maybe.' The detailed reading comes later."

**Evidence from Deal Room Notes**:

- Day 1 mark-up: 2,000 documents tagged by risk level (color-coded). Takes ~8 hours for junior associate.
- Day 2 review: Senior associates dive into high-risk (500 docs), spot-check medium (300 docs), skip low (700 docs).
- Actual detailed review time: ~40 hours for 800 documents (high + medium risk). Remaining 1,200 documents receive < 5 min each.

**Implication**: A tool that reads every contract equally is missing the point. The workflow is risk-stratified. Early flagging of high-risk documents is the bottleneck.

---

### 2. The Bottleneck Isn't Reading Speed—It's Cross-Referencing

Associates spend more time connecting dots than reading documents.

**P3's Quote**:
"I read this clause in 30 seconds. Then I spend 20 minutes checking if it conflicts with 3 other documents. 'Does this IP assignment override the customer's license grant? Let me check the IP schedule.' 'Does this termination clause align with the renewal terms?' 'Is there an amendment that modifies this term?'"

**Workflow Evidence from Observation**:

**Scenario 1**: P3 reads: "Customer has exclusive territory rights in EMEA."
- Next steps: Search for any amendments modifying territory (5 minutes)
- Cross-check against customer list: Is EMEA exclusive with 3rd parties? (3 minutes)
- Compare against deal summary: Does deal involve EMEA expansion? (2 minutes)
- Total time: 10 minutes for a 30-second clause.

**Scenario 2**: P4 finds: "Automatic renewal unless 90-day notice provided."
- Questions: Who owns the notice responsibility? Is there a tracking system for renewals? Does this apply after termination? (Searches across docs, 15 minutes)
- Compares to other contracts: Do other vendors have same renewal terms? (5 minutes)
- Total time: 20 minutes.

**P1's Perspective**:
"The thing that kills us is when you find a clause and then realize it conflicts with something you read 200 pages ago. You have to flip back, re-read, understand the interaction. That's where the time goes."

**Quantified Data from Deal Analysis**:

Review time breakdown for 50 high-risk contracts:
- Reading the document: 20% of time (10 min per contract)
- Cross-referencing with other docs: 50% of time (25 min per contract)
- Resolving conflicts/clarifications: 30% of time (15 min per contract)

**Implication**: Speed improvements must address cross-referencing, not just reading.

---

### 3. Partners Want Confidence Scores, Not Automated Answers

Partners don't want AI to replace judgment. They want AI to flag what might be risky.

**P1's Explicit Request**:
"Don't tell me the answer. Tell me how confident you are. If you're 95% confident this is a change of control clause, I'll trust you. If you're 60% confident, I'll read it myself and verify. That's actually useful."

**P2's Request**:
"I want to know: What am I most likely to miss? If an AI can flag patterns that humans typically miss, that's valuable. Missed a similar clause in a competitor's deal 3 years ago? Tell me about it."

**From Deal Room Observation**:

P1 and P3 discussing a clause:
- P3: "I think this is a change of control clause."
- P1: "You sure?"
- P3: "60% confident. It's unusual phrasing."
- P1: [Reads the clause] "Yeah, it's change of control. I see it now."

This conversation happens repeatedly. The value of a second opinion is in flagging uncertainty, not in declaring certainty.

**Compliance Officer's Perspective (P6)**:
"If you're going to use AI to review contracts, accuracy matters. But 'accuracy' doesn't mean 'perfect.' It means 'accurate enough that you don't miss material issues, but fast enough that you save time.' A tool that's 90% accurate but catches 95% of material issues is better than a tool that's 99% accurate but takes twice as long."

---

### 4. OCR Quality Varies Wildly—Older Contracts Are Broken Data

Handwritten amendments, poor scans, and legacy document formats break automated processing.

**Evidence from Document Analysis**:

Sample of 100 randomly selected contracts from one deal:
- 40% are native PDFs (high OCR accuracy, ~98%)
- 35% are scanned documents, recent (medium OCR accuracy, ~85%)
- 20% are scanned documents, older (low OCR accuracy, ~65%)
- 5% are scanned + handwritten amendments (OCR breaks down entirely)

**P4's Observation**:
"We have a 1998 contract that was scanned in 2010. Someone annotated it by hand in 2015. The OCR is gibberish. I have to read it manually. If I feed it to an AI tool, the AI is working with corrupted input."

**P3's Experience**:
"I found a handwritten amendment in a customer contract. It changed the renewal terms completely. The AI would have missed it because it's not in the digital text. I had to catch it by reading the original document."

**P1's Perspective**:
"Document quality is our biggest challenge. We handle contracts from 20+ years of acquisitions and partnerships. Half of them are scans of scans. Any tool you build has to account for document quality variance."

**Implication**: OCR is not a solved problem for legal contracts. Tools must either handle degraded input gracefully or flag documents that require manual review.

---

### 5. Privilege Preservation is a Hard Constraint

Data cannot leave the firm's environment. This is non-negotiable for legal firms.

**P6 (Compliance Officer) Explicit Requirement**:
"If your tool sends contract data to the cloud, privilege is potentially waived. Waived privilege means opposing counsel can demand the contract and all our internal notes. That's a massive risk. So any tool must be on-prem or have very specific data handling guarantees—e.g., encrypted end-to-end, no logging, data deleted immediately after processing."

**P1's Corroboration**:
"We've been burned before by tools that claimed 'data is encrypted' but actually stored it for model training. We can't take that risk. We need signed guarantees about data handling."

**Practical Implication**:
- Tool must run on law firm's infrastructure (not SaaS cloud)
- Or: Use a vendor's API with contractual guarantees (no logging, no model training, immediate deletion)
- Data handling must be auditable (firm can verify data isn't retained)

**P6's Additional Constraint**:
"Even within the firm, privilege can be broken if the wrong people see the data. So the tool should have access controls: only authorized attorneys can view results. Paralegals and data entry folks shouldn't have access to attorney work product."

---

### 6. "Good Enough" Accuracy is Better Than Perfect Accuracy That's Slow

Speed and accuracy trade-off. Partners prefer 94% F1 with fast turnaround over 99% F1 that takes as long as manual review.

**P2's Framework**:
"Let's say a deep manual review of a contract takes 45 minutes and catches 99% of issues. If an AI tool takes 3 minutes and catches 94% of issues, the AI is worth it because I can manually spot-check the 6% and it's net faster."

**P1's Elaboration**:
"The goal isn't perfect. The goal is to compress the timeline. If I get from 3 weeks to 2.5 weeks, that's $100K in partner time saved per deal. That's worth a small risk of missing something that I'll probably catch in a second pass anyway."

**Deal Timeline Pressure**:

All interviews mentioned deal timeline urgency. Typical M&A deal prep: 3–6 weeks to close. Contract review must happen in parallel with other due diligence, but it's a critical path item. Any compression of the 2–3 week review window is valuable.

**From P3's Reflection**:
"I'd use a tool that's 90% accurate if it saved me 10 hours per deal. I'd never use a tool that's 99% accurate but takes 40 hours (because I'm double-checking everything anyway). Speed is more important than perfection."

---

## Field Observation Notes: Moments That Revealed Unspoken Needs

**Day 1, 10 AM**: P5 (junior associate) reads a contract, flags it as "possible change of control." P3 (senior associate) looks at it and says "No, that's a refinancing clause, different thing." P5 nods and moves on. The junior associate lacks pattern recognition. A tool that flags uncertainty would let them learn or escalate appropriately.

**Day 2, 3 PM**: P3 finds a clause about "non-solicitation of employees post-termination." Spends 15 minutes checking if there's a related covenant in the IP schedule (there isn't). The time investment wasn't reading the clause; it was verifying it wasn't contradicted elsewhere.

**Day 4, 2 PM**: P1 and P3 discuss a confusing amendment. P1 says: "I feel like I've seen this language before. Is it from the Acme deal?" They search their institutional memory for 5 minutes, don't find it. Eventually resolve it. A tool that could surface "similar clauses in past deals" would have saved time.

**Day 5, 10 AM**: P4 discovers a handwritten note on a 1995 contract: "Modified 4/2015 - renewal now annual, not multi-year." This changes the entire interpretation of the contract. The digital version is wrong. P4 has to flag this for manual review. Tool would need to flag "document quality issues" for contracts with handwritten amendments.

**Day 6, 1 PM**: Discussion between P1 and P6 about data handling for an AI tool. P6 says: "If this goes to the cloud, we can't use it. We'd need on-prem or signed guarantees about data deletion." P1 nods in agreement. This is a blocking constraint.

---

## Synthesis: The Actual Contract Review Workflow

**What textbooks say happens**:
1. Associate reads contract from start to finish
2. Associate identifies key clauses
3. Associate logs findings
4. Partner reviews findings
5. Partner conducts final verification

**What actually happens**:
1. Junior associate triages all documents by risk (change of control, IP, exclusivity, termination, etc.)
2. Senior associate deep-dives on high-risk documents
3. Senior associate cross-references clauses across documents (answering questions like "Does clause X override clause Y?")
4. Senior associate handles amendments and document quality issues (scans, handwritten notes)
5. Partner reviews senior associate's findings, conducts spot-checks on high-risk items
6. Partner resolves conflicts and edge cases
7. Partner conducts final verification on deal-critical clauses

**Where Bottlenecks Occur**:
- **Triage**: Is this document high-risk? (Humans are inconsistent)
- **Cross-referencing**: Does this clause conflict with that clause? (Time-intensive, requires context)
- **Document quality**: OCR fails on old scans and handwritten amendments
- **Pattern recognition**: Are there similar issues we missed in past deals?

**Where Tools Would Actually Help**:
- Flag high-risk documents early (enables stratified review)
- Highlight potential conflicts across documents (reduces search time)
- Surface similar language from past deals or playbooks
- Flag document quality issues (old scans, poor OCR)
- Provide confidence scores for clause identification (helps junior associates learn)

**Where Tools Can't Help** (yet):
- Fully replace human judgment on complex interactions
- Handle severely degraded documents (handwritten amendments, poor scans)
- Guarantee accuracy on novel or unusual clauses
- Make privilege/data handling guarantees

---

## How This Shaped the Product

### Feature: Risk-Stratified Document Triage

**Finding**: Associates don't read sequentially. They triage by risk level, then deep-dive on high-risk documents.

**Solution**: Automated pre-triage classifies documents by risk tier:
- **High Risk** (change of control, IP assignment, exclusivity, termination, financing): Flagged for senior review
- **Medium Risk** (renewal terms, territory restrictions, indemnities): Flagged for verification
- **Low Risk** (standard warranties, boilerplate): Noted but deprioritized

**Design Decision**: Risk classification is rule-based (triggers on keyword presence + context), not ML-based (to preserve explainability and avoid false positives). Partners can adjust risk tiers per deal.

**Impact**: Junior associates can triage 2,000 documents in 4–6 hours (down from 8–10 hours of manual reading). Enables risk-stratified workflow.

---

### Feature: Cross-Reference Flagging (Conflict Detection)

**Finding**: The bottleneck isn't reading speed—it's cross-referencing. Associates spend 50% of time verifying that clauses don't conflict across documents.

**Solution**: When a clause is identified, the tool flags related clauses in other documents:
- "This is a change of control clause. Similar language found in: Customer Agreement (Exhibit A, clause 5.2), Financing Agreement (clause 3.1), Vendor Agreement (schedule B). Potential conflicts?"
- "This renewal clause is annual. Conflicting renewal term found in: Parent Company Agreement (clause 2.3) requires multi-year renewal. Manual verification needed."

**Design Decision**: Conflict flagging is based on keyword proximity and context, not semantic understanding (which is unreliable). Flags are presented as "potential issues to verify," not "issues identified."

**Impact**: Reduces cross-referencing time from 25 min/contract to 5 min/contract (associates verify flags rather than search blind).

---

### Feature: Confidence Scoring & Justification

**Finding**: Partners don't want automation. They want confidence scores and explainability.

**Solution**: For each classified clause, show:
- Clause classification (e.g., "Change of Control")
- Confidence score (e.g., "94% confidence")
- Justification (e.g., "Triggered on keywords: 'control of company,' 'ownership transfer.' Verified against playbook examples.")
- Alternative classifications considered (e.g., "Could also be interpreted as refinancing clause with 30% confidence")

**Design Decision**: Confidence is derived from pattern matching + comparison to known examples, not pure ML (to preserve interpretability). Junior associates see this as a teaching tool; partners see it as a risk signal.

**Impact**: Partners trust flagging because they understand how confidence is derived. Junior associates learn patterns from the justifications.

---

### Feature: Document Quality Assessment

**Finding**: OCR quality varies wildly. Handwritten amendments, old scans, and poor digitization break automated processing.

**Solution**: Flag documents with OCR quality issues:
- Scanned PDF with <80% OCR confidence: "Document quality low. Manual verification recommended."
- Handwritten amendments detected: "This document appears to contain handwritten annotations. AI review may be incomplete."
- High character error rate: "OCR quality poor. Recommend manual review or re-scanning."

**Design Decision**: Don't try to fix OCR. Instead, flag documents that need manual review. Associates can then choose to manually read, request re-scan, or accept the risk.

**Impact**: Associates aren't blindsided by broken AI output. They know which documents to double-check manually.

---

### Feature: Institutional Memory (Playbook & Deal History)

**Finding**: Partners reference past deals and institutional playbooks. A tool that surfaces similar language would save search time.

**Solution**: Integration with firm's document management system (Lexis-Nexis, DealPoint, internal database). When a clause is identified:
- Surface similar clauses from past deals (e.g., "Same language found in 7 past customer agreements")
- Compare to standard playbook (e.g., "Deviates from standard playbook on renewal terms")
- Highlight deviations (e.g., "Non-standard: Change of control threshold is 20%, not 30%")

**Design Decision**: Playbook is manually maintained (by partners, updated after each deal). Tool surfaces matches, doesn't generate recommendations.

**Impact**: Captures institutional knowledge. Junior associates learn by comparing to past deals. Partners spot deviations faster.

---

### Feature: Split-Pane Review Interface

**Finding**: Associates constantly switch between documents (reading clause, cross-referencing related doc, checking playbook). Switching is friction.

**Solution**: Split-pane interface:
- Left pane: Current document + AI flags + cross-references
- Right pane: Related document (customer agreement, amendment, playbook example)
- Associates can flip between related docs without losing context

**Design Decision**: Tool surfaces likely cross-references, but associates control which document appears in right pane. This preserves associate judgment while reducing navigation friction.

**Impact**: Reduces context switching latency. Associates can verify conflicts/interactions in parallel instead of sequentially.

---

### Feature: Privilege-Preserving Architecture

**Finding**: Data cannot leave the firm. Privilege preservation is non-negotiable.

**Solution**: Hybrid architecture:
- Option A: On-premise deployment (tool runs on firm's infrastructure)
- Option B: Cloud deployment with contractual guarantees (no logging, no model training, encrypted end-to-end, immediate data deletion, SOC 2 Type II audit)

**Design Decision**: Compliance team can audit data handling. All contract data is marked with internal classification (attorney work product, etc.). Access controls enforce privilege boundaries.

**Impact**: Firms can use the tool without waiving privilege. Compliance sign-off is possible.

---

### Non-Feature: Fully Automated Contract Analysis

**Finding**: Partners don't want a tool that reads contracts and delivers conclusions. They want a tool that flags risk and surfaces context.

**Decision**: Tool is strictly flagging + context. No "deal recommendation" or "risk score" that summarizes the deal. All conclusions remain with the partner.

**Rationale**: Liability. If the tool makes a mistake in a deal-critical assessment, it's a malpractice issue. Partners must retain judgment authority.

---

### Non-Feature: Perfect Accuracy

**Finding**: Partners prefer 90–94% accuracy with fast turnaround over 99% accuracy with slow turnaround.

**Decision**: Tool optimizes for speed + "good enough" accuracy (recall >90%, precision >85%). Associates expect to verify 10–15% of flagged items. This is acceptable.

**Rationale**: Perfect accuracy is impossible on novel or adversarial clauses. Attempting it would require manual verification anyway, defeating the purpose.

---

## Remaining Questions & Edge Cases

- How does the tool handle entirely novel deal structures? (e.g., first SPACs, novel crypto arrangements)
- What's the failure mode if OCR is very poor and the tool misses something? How do we gracefully degrade?
- How do we handle confidential amendments (not in the contract set)? Should tool flag "potential amendments not included"?
- Regional variation: How do we handle contracts across different jurisdictions (UK vs. US law, for example)?
- How do we handle embedded exhibits and schedules? (Many contracts reference "Schedule A" without including the actual schedule in the PDF)

---

**Research Artifacts**: Interview recordings (6 of 6, 4 transcribed, 2 awaiting consent), deal room observation notes (2 full days), sample document metadata and marking patterns from 3 completed deals, OCR quality analysis (100 document sample), follow-up email clarifications on privilege and data handling.
