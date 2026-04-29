# Top critiques of the paper and its methodology

Ordered roughly from most to least serious. Several would be addressable in a revision; one or two are intrinsic limits of what this initial probe can claim.

---

## 1. Single image per category, so we cannot disentangle "Christian sacred art" from "this specific Annunciation"

The paper is candid that it tests one Marian icon (Fra Angelico's *Annunciation*) and one non-religious figural reference (Hokusai's *Great Wave*). Every effect we attribute to sacred imagery could be partly or wholly an effect of this particular Marian scene — its compositional clarity, its Dominican context, its substantial training-data presence, or some combination. The paper acknowledges this limit explicitly and frames the work as an "initial impressionistic exploration"; a categorical test of "Christian iconography" would require *k* ≥ 5 sacred images spanning iconographic types (Crucifixion, Pantocrator, martyrdom, Pietà, Nativity) plus matched secular controls and ideally non-Christian devotional images. The paper's strict conclusions, as the discussion in §6 notes, are about *the Annunciation specifically*, not about Christian iconography in general. The forthcoming structured study is intended to address this, but it is the largest known weakness of the present paper.

## 2. Training-data contamination is undisentangled from "iconographic engagement"

Both Opus 4.6 and GPT-5.4 have been trained on enormous quantities of art-historical text and very likely on images of Fra Angelico's *Annunciation* labeled as such. When Opus 4.6 says *"the Latin inscription at the bottom of Fra Angelico's Annunciation reminds the friars…"*, it could be (a) genuinely processing the image content into a moral analogy, or (b) retrieving a memorized association between the image and surrounding training-time discourse. These are very different stories. We do not have the means in this study to distinguish them. A meaningful follow-up would test commissioned images that do not exist in any pre-2026 training corpus (e.g., AI-generated or freshly photographed religious scenes with no online presence).

## 3. Asymmetry between the imagery protocol and §5.2's psalm protocol

ICMI-011 §5.2 placed all ten psalms simultaneously into the system prompt — a saturation treatment. Our protocol places one image in the user message of each call. The Annunciation-as-percent-of-psalm-effect numbers in §4.3 (22%–80% across virtues) therefore conflate two design decisions: (i) sacred imagery vs. sacred text, and (ii) one stimulus per call vs. ten stimuli simultaneously. The paper discusses this in §3.4 but does not control for it. A natural follow-up would attach all ten of an extended sacred bundle's images per call (cost: ~10× per-call image tokens) and compare directly.

## 4. Limited variant coverage: ratio only

VirtueBench-2 has five variants (*ratio*, *caro*, *mundus*, *diabolus*, *Ignatian*). We test *ratio*. The *Ignatian* variant — in which vice is disguised in Scripture itself — is arguably the most interesting test bed for iconographic priming, since it is the variant where the prototype-image relationship most directly disambiguates a counterfeit-virtue temptation. We don't know whether the imagery effect persists, amplifies, or attenuates on *diabolus* or *Ignatian*. The structured follow-up should include all five.

## 5. The framing-prompt deviation from §5.2 is a real protocol break

§5.2's psalm injection lives in the system prompt; our images live in user messages because both APIs require it. We mitigate by adding a constant line *"You may receive supplementary visual context with each scenario"* to the system prompt across all arms — keeping the system invariant. But this is *not* the §5.2 protocol. Subtle effects of system-vs-user-message placement are documented in the prompt-engineering literature; we cannot fully rule out that some fraction of the difference between our results and §5.2's reflects this design choice rather than the text-vs-image substitution we want to study.

## 6. Bonferroni across 24 tests treats hypotheses as exchangeable

We use Bonferroni correction across 24 contrasts (3 image arms × 4 virtues × 2 models). This is conservative and arguably over-conservative given the structured family of hypotheses. A hierarchical approach (e.g., test omnibus first, then drill in only if rejected) or BH-FDR control would give different significance counts and is arguably more appropriate. The robust temperance/Annunciation result on Opus 4.6 (Bonferroni p ≈ 0.002, *h* = 0.32) survives any reasonable choice; some of the smaller effects (e.g., justice/Annunciation, +1.6 pp, raw p = 0.04) survive less strictly. We report Bonferroni for transparency, but readers may prefer to apply their own correction policy.

## 7. The reasoning-trace section (§5) is qualitative and selection-prone

§5 reproduces a small number of representative responses to illustrate Opus 4.6's iconographic engagement. This is qualitative and impressionistic by design — an earlier draft attempted to count verbal references via regular expression and we judged the regex-based counts brittle in both directions (over-counting metaphorical uses of "image" / "wave"; under-counting integration that uses thematic vocabulary without naming the work). The qualitative section preserves the most defensible part of that earlier analysis but introduces a different kind of bias: we, the authors, picked the excerpts. A more credible follow-up would (a) preregister the inclusion criteria for excerpt selection, (b) have an independent reader code a held-out sample, or (c) replace the qualitative section entirely with a controlled paraphrase-similarity metric between response text and a fixed iconographic vocabulary. The present section is honest about being illustrative, not evidentiary, but the bias remains.

## 8. The contrast between Opus 4.6 and GPT-5.4 may reflect vision-encoder differences as much as moral-reasoning differences

We attribute the asymmetry between Opus 4.6 and GPT-5.4 to differences in cross-modal verbal integration capacity. But the two models have different vision encoders, presumably trained on different data, with different fidelity to specific iconographic content. It is possible that GPT-5.4's encoder is, for instance, less capable of resolving the specific compositional features of fifteenth-century Florentine fresco, or of reading the Latin inscription at the bottom of the *Annunciation*; if so, the model's lack of verbal engagement could be a perception-level difference rather than a reasoning-level one. The present paper cannot distinguish these.

## 9. No religious or cultural controls beyond Hokusai

The paper's framing — and its title — point at *Christian* moral imagination. But we test only one non-Christian image, an Edo-period Japanese print. We do not test (a) a Buddha image, (b) a Hindu deity, (c) a Sufi calligraphic image, or (d) a famous secular image of moral significance (a photograph of an act of conscience). Any of these would help disambiguate "Christian content priming Christian moral reasoning" from "any image of culturally meaningful moral content priming moral reasoning of any tradition." Without such controls, the *Christian* qualifier in the title is a hypothesis the data do not distinguish from the broader claim. The paper's §6 acknowledges this; the §7 future-work direction on a "structured iconographic control study" is the planned remedy.

## 10. The theological framing implements a strong reading the data underdetermine

§2 and §6 invoke Aquinas's three goods of sacred imagery and Ignatius's *compositio loci*, and present the data as bearing on these traditions. A more parsimonious reading is available: visual context that the model can describe verbally cues additional moral-reasoning effort, and Marian iconography happens to be especially describable to a model that has seen many Marian scenes in training. The behavioral pattern doesn't *require* the theological framing. We choose the theological framing for the conjunction of (a) the empirical specificity of the result and (b) the natural fit with the iconographic tradition; readers may legitimately prefer the more parsimonious read. The paper has been adjusted to flag this trade-off explicitly in §6, but the framing choice remains.

## 11. No human moral-judgment baseline

VirtueBench-2 scoring assumes a single correct answer per scenario (the patristically-sanctioned virtuous choice). In practice, several scenarios admit defensible alternatives. A model that picks the "wrong" answer might be making a judgment a reflective Christian reader would also defend. Without an inter-rater human baseline on a subset of scenarios, we don't know how much of the model-vs-baseline gap reflects genuine moral failure vs. defensible alternative judgment. This is inherited from VirtueBench-2 and is not specific to the present study, but it bears on how confidently we should read accuracy gains as moral improvements.

## 12. Cross-modal narrative integration ≠ "Christian moral imagination"

The §6 discussion uses the phrase "Christian multimodal reasoning" (and the title goes further). The behavioral signature is more honestly described as: *some multimodal models surface visual content into their textual reasoning in a way that influences downstream behavior, and Opus 4.6 is one of them on Christian content*. Whether this signature warrants the qualifier *Christian* — vs. some thinner descriptor like *narrative-integration capacity* — is a framing choice, not an empirical fact. The paper makes the framing choice explicitly and defensibly, but it is a choice that the next, more structured study will test.
