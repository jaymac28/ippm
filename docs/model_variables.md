# IPPM Model Variables and Equations

Full documentation of all stocks, flows, variables, and equations in the Integrated Parallel Processing Model version 0.0.2.

## Simulation Settings

| Setting | Value |
|---|---|
| Algorithm | RK4 |
| Time Start | 0 |
| Time Length | 600 |
| Time Step | 1 |
| Time Units | Days (treat as abstract units for single-message runs) |

## Input Variables (Message Resonance)

These represent empirically measured audience perceptions of the message. They are the four constructs Witte (1992) specifies as the operative variables of the EPPM. They should be set by measuring actual audience perception, not by researcher declaration of message intent.

| Variable | Default | Min | Max | Step |
|---|---|---|---|---|
| severity | 0.5 | 0 | 1 | 0.01 |
| susceptibility | 0.5 | 0 | 1 | 0.01 |
| self_efficacy | 0.5 | 0 | 1 | 0.01 |
| response_efficacy | 0.5 | 0 | 1 | 0.01 |

**Note on resonance:** What matters for behavioral outcome is the ratio between the threat sum (severity + susceptibility) and the efficacy sum (self_efficacy + response_efficacy). Individual variable combinations that produce the same sum on each side produce equivalent behavioral trajectories.

## Control Variables

| Variable | Default | Min | Max | Step | Description |
|---|---|---|---|---|---|
| population_variance | 0.1 | 0.01 | 0.5 | 0.01 | SD on RandNormal appraisal noise. Higher values represent more heterogeneous audience perception. Affects emotional stocks more than behavioral stocks due to gate buffering. |
| cross_dampening | 0 | 0 | 1 | 1 | Binary switch. When ON, enables cognitive interference at moment of message evaluation — optimism/rewards dampen threat appraisal; fear/consequences dampen efficacy appraisal. Only meaningful when initial emotional stocks are pre-seeded. |
| repeated_exposure | 0 | 0 | 1 | 1 | Binary switch. When ON, re-fires the appraisal pulse at every exposure_interval units, modeling campaign-level repeated messaging rather than single message event. |
| exposure_interval | 30 | 7 | 180 | 1 | Units between message exposures when repeated_exposure=1. Default 30 represents monthly campaign cadence. |

## Initial State Variables (Individual Differences)

These set the starting emotional and appraisal conditions before any message is received. At default zero they represent a blank slate. Non-zero values represent an audience with prior emotional history, directly operationalizing Witte's P12 (individual differences).

| Variable | Default | Min | Max | Step | Theoretical Meaning |
|---|---|---|---|---|---|
| initial_fear | 0 | 0 | 1 | 0.05 | Trait anxiety / baseline negative affect |
| initial_optimism | 0 | 0 | 2 | 0.1 | Dispositional hope / baseline positive affect |
| initial_threat | 0 | 0 | 2 | 0.1 | Pre-existing threat perception for this health topic |
| initial_efficacy | 0 | 0 | 2 | 0.1 | Pre-existing efficacy belief for this health topic |

**Theoretical combinations of note:**
- Anxious/vulnerable: initial_fear=0.8, initial_optimism=0.1
- Calm/competent: initial_fear=0.1, initial_optimism=0.8
- Learned helplessness: initial_fear=0.9, initial_optimism=0, initial_efficacy=0
- Health-aware: initial_threat=0.3, initial_efficacy=0.5, initial_optimism=0.5

## Stocks

### Threat
- **Initial value:** `[initial_threat]`
- **Non-negative:** yes
- **Description:** Accumulated threat appraisal stock. Loaded by single message pulse at t=0. Subsequently driven by fear feedback (reinforcing loop) and depleted by threat dissipation.

### Efficacy
- **Initial value:** `[initial_efficacy]`
- **Non-negative:** yes
- **Description:** Accumulated efficacy appraisal stock. Loaded by single message pulse at t=0. Subsequently driven by optimism feedback (hope/balancing loop) and depleted by efficacy dissipation.

### fear
- **Initial value:** `[initial_fear]`
- **Non-negative:** yes
- **Description:** Negative emotional state activated by Threat. Feeds back to amplify Threat (reinforcing loop R1 — the fear spiral). Mutually suppressed by optimism through dissipation dynamics.

### optimism
- **Initial value:** `[initial_optimism]`
- **Non-negative:** yes
- **Description:** Positive emotional state activated by Efficacy. Feeds back to amplify Efficacy (balancing loop B1 — the hope loop). Mutually suppressed by fear through dissipation dynamics. This is the structural addition absent from Witte's original EPPM.

### Adaptive
- **Initial value:** `[initial_efficacy]` (or 0 for blank slate)
- **Non-negative:** yes
- **Description:** Cumulative danger control behavioral response attributable to this message exposure. Driven by danger control flow when Efficacy >= Threat.

### Maladaptive
- **Initial value:** `[initial_threat]` (or 0 for blank slate)
- **Non-negative:** yes
- **Description:** Cumulative fear control behavioral response attributable to this message exposure. Driven by fear control flow when Threat > Efficacy.

### rewards
- **Initial value:** 0
- **Non-negative:** yes
- **Description:** Positive outcome feedback from adaptive behavior. Feeds optimism reinforcement loop. Represents the experience of successful protective behavior generating hope-sustaining feedback.

### consequences
- **Initial value:** 0
- **Non-negative:** yes
- **Description:** Negative outcome feedback from maladaptive behavior. Feeds fear reinforcement loop and adds secondary pressure toward danger control. Represents the experience of consequences from avoidance/denial.

## Flows

### Threat Appraisal
- **From:** null → Threat
- **Fires:** Only at Days() < 1 (single message event), or every exposure_interval if repeated_exposure=1
```
severity <- RandNormal([severity], [population_variance])
susceptibility <- RandNormal([susceptibility], [population_variance])
base <- severity + susceptibility

// CROSS-DAMPENING: When enabled, reduces perceived threat based on recipient's
// current optimism level and accumulated rewards from prior adaptive behavior.
// A person who already feels capable and has experienced good outcomes will
// perceive the same threatening message as less severe and less personally
// relevant. Represents cognitive interference at moment of message evaluation.
// Only meaningful when initial stocks are pre-seeded to represent prior history.
dampening <- IfThenElse([cross_dampening] = 1, ([optimism] + [rewards]) * 0.1, 0)

IfThenElse(Days() < 1 OR ([repeated_exposure] = 1 AND Days() mod [exposure_interval] < 1),
  base - dampening, 0)
```

### Efficacy Appraisal
- **From:** null → Efficacy
- **Fires:** Only at Days() < 1 (single message event), or every exposure_interval if repeated_exposure=1
```
self_efficacy <- RandNormal([self_efficacy], [population_variance])
response_efficacy <- RandNormal([response_efficacy], [population_variance])
base <- self_efficacy + response_efficacy

// CROSS-DAMPENING: When enabled, reduces perceived efficacy based on recipient's
// current fear level and accumulated consequences from prior maladaptive behavior.
// A person who is already frightened and experiencing negative outcomes will find
// it harder to believe they can perform the recommended action or that it will work.
// Represents fear impairing prefrontal processing of efficacy information —
// a well-documented neurological effect where high fear states reduce the ability
// to evaluate coping options clearly.
dampening <- IfThenElse([cross_dampening] = 1, ([fear] + [consequences]) * 0.1, 0)

IfThenElse(Days() < 1 OR ([repeated_exposure] = 1 AND Days() mod [exposure_interval] < 1),
  base - dampening, 0)
```

### - emotional response (Threat → fear)
- **From:** null → fear
- **Rate:** `[Threat] * 0.1`
- **Description:** Threat perception generates negative emotional response. Runs continuously — Threat keeps activating fear as long as Threat stock has value.

### + emotional response (Efficacy → optimism)
- **From:** null → optimism
- **Rate:** `[Efficacy] * 0.1`
- **Description:** Efficacy perception generates positive emotional response. Runs continuously — Efficacy keeps activating optimism as long as Efficacy stock has value.

### fear feedback (fear → Threat)
- **From:** fear → Threat
- **Rate:** `[fear] * 0.1`
- **Description:** The fear reinforcing loop (R1). Fear amplifies threat perception, which generates more fear. This is the loop Witte identified. Coefficient 0.1 prevents immediate runaway while preserving the reinforcing dynamic.

### optimism feedback (optimism → Efficacy)
- **From:** optimism → Efficacy
- **Rate:** `[optimism] * 0.1`
- **Description:** The hope balancing loop (B1). Optimism amplifies efficacy perception, which generates more optimism. This is the structural addition absent from Witte's original EPPM. Without this loop the model has no stable attractor on the efficacy side.

### danger control (Efficacy → Adaptive)
- **From:** Efficacy → Adaptive
- **Rate (continuous competition formulation):**
```
gap <- Max(0, [Efficacy] - [Threat])
([Efficacy] + ([consequences] * 0.1)) * gap
```
- **Description:** Danger control pathway. Active and proportional to how much Efficacy exceeds Threat. Consequences provide secondary motivational pressure — experience of maladaptive outcomes adds urgency to danger control. Both pathways can be active simultaneously; rates are modulated by perceptual gap magnitude.

### fear control (Threat → Maladaptive)
- **From:** Threat → Maladaptive
- **Rate (continuous competition formulation):**
```
gap <- Max(0, [Threat] - [Efficacy])
([Threat] + ([rewards] * 0.1)) * gap
```
- **Description:** Fear control pathway. Active and proportional to how much Threat exceeds Efficacy. Rewards from maladaptive behavior (short-term anxiety reduction) add secondary reinforcement to fear control.

### fear reinforcement (consequences → fear)
- **From:** consequences → fear
- **Rate:** `[consequences] * 0.1`
- **Description:** Negative outcome feedback loop. Consequences from maladaptive behavior feed back to amplify fear. Represents the experience of negative outcomes confirming and deepening the sense of threat and helplessness.

### optimism reinforcement (rewards → optimism)
- **From:** rewards → optimism
- **Rate:** `[rewards] * 0.1`
- **Description:** Positive outcome feedback loop. Rewards from adaptive behavior feed back to amplify optimism. Represents the experience of successful protective behavior building hope and sustaining further adaptive behavior.

### reward pathway (Adaptive → rewards)
- **From:** Adaptive → rewards
- **Rate:** `[Adaptive] - (([self_efficacy] + [response_efficacy]) * RandNormal(0.5, 0.15))`
- **Non-negative:** yes
- **Description:** Adaptive behavior generates reward feedback, dampened by a stochastic term scaled to efficacy inputs. Personal competence (self_efficacy + response_efficacy) reduces outcome noise — more capable individuals have more predictable positive outcomes.

### pain pathway (Maladaptive → consequences)
- **From:** Maladaptive → consequences
- **Rate:** `[Maladaptive] - (([severity] + [susceptibility]) * RandNormal(0.5, 0.15))`
- **Non-negative:** yes
- **Description:** Maladaptive behavior generates consequence feedback, dampened by a stochastic term scaled to threat inputs. Objective threat characteristics (severity + susceptibility) modulate consequence severity — higher real-world threat produces more variable and potentially more severe consequences.

### threat dissipation (Threat → null)
- **From:** Threat → null
- **Rate:** `[Threat] * 0.05`
- **Description:** Proportional decay of threat appraisal. Cognitive appraisals of threat fade more quickly than the emotional residue they produce, consistent with the dissipation hierarchy (Threat decays faster than fear).

### efficacy dissipation (Efficacy → null)
- **From:** Efficacy → null
- **Rate:** `[Efficacy] * 0.05`
- **Description:** Proportional decay of efficacy appraisal. Symmetrical with threat dissipation.

### fear dissipation (fear → null)
- **From:** fear → null
- **Rate:** `[fear] * 0.05 + ([optimism] * 0.05)`
- **Description:** Fear decays naturally (proportional term) and is suppressed by optimism (cross-suppression term). The mutual suppression between fear and optimism produces the oscillatory competition observed under repeated exposure. Coefficient 0.05 on optimism term means optimism suppresses fear but does not completely neutralize the fear feedback loop unless optimism substantially exceeds fear.

### optimism dissipation (optimism → null)
- **From:** optimism → null
- **Rate:** `[optimism] * 0.05 + ([fear] * 0.05)`
- **Description:** Optimism decays naturally (proportional term) and is suppressed by fear (cross-suppression term). Symmetrical with fear dissipation.

### reward dissipation (rewards → null)
- **From:** rewards → null
- **Rate:** `RandNormal(0.01, 0.005)`
- **Description:** Stochastic dissipation of reward stock representing the unpredictability of how long positive outcomes sustain motivational effect.

### consequence dissipation (consequences → null)
- **From:** consequences → null
- **Rate:** `RandNormal(0.01, 0.005)`
- **Description:** Stochastic dissipation of consequences stock. Uniform randomness may be appropriate here given high real-world variability in how long negative outcomes remain salient.

## Feedback Loop Summary

| Loop | Type | Path | Witte (1992) |
|---|---|---|---|
| R1 — Fear Spiral | Reinforcing | fear → Threat → (- emotional response) → fear | Identified |
| R2 — Fear Reinforcement | Reinforcing | consequences → fear → Threat → fear control → Maladaptive → pain pathway → consequences | Partially identified |
| B1 — Hope Loop | Balancing | optimism → Efficacy → (+ emotional response) → optimism | **Not identified** |
| B2 — Reward Reinforcement | Balancing | rewards → optimism → Efficacy → danger control → Adaptive → reward pathway → rewards | **Not identified** |
| B3 — Consequence Pressure | Balancing | consequences → danger control (secondary term) | **Not identified** |

## Dissipation Rate Hierarchy

Based on affective persistence literature: cognitive appraisals fade faster than emotional states; emotional states are stickier than cognitive updates.

| Stock | Rate | Rationale |
|---|---|---|
| Threat | 0.05 (proportional) | Cognitive appraisal; fades relatively quickly |
| Efficacy | 0.05 (proportional) | Cognitive appraisal; symmetrical with Threat |
| fear | 0.05 * fear + 0.05 * optimism | Emotional; persists longer; suppressed by optimism |
| optimism | 0.05 * optimism + 0.05 * fear | Emotional; symmetrical with fear; suppressed by fear |
| rewards | RandNormal(0.01, 0.005) | Outcome memory; slow stochastic decay |
| consequences | RandNormal(0.01, 0.005) | Outcome memory; slow stochastic decay |

## Modeling Decisions and Assumptions

**Single message event:** The appraisal flows fire only at t=0 by default. This represents a single message exposure. The 600-unit run models the full trajectory from initial exposure through eventual dissipation. Both fear and optimism return to near-zero in a single-exposure run — these stocks represent message-activated emotional response, not dispositional traits.

**Continuous competition:** The behavioral gating uses gap-modulated continuous flows rather than binary IfThenElse. This means both pathways can be active simultaneously with rates proportional to perceptual dominance. This is more theoretically defensible than binary exclusion and avoids encoding the unproved assumption that one process completely suppresses the other.

**Threshold for consistent danger control:** Simulation testing shows that efficacy inputs must exceed threat inputs by approximately 0.2 units (e.g., threat sum = 1.2, efficacy sum = 1.4) to produce consistent Adaptive dominance throughout the active window. Matched inputs produce indeterminate mixed behavior. This is a model finding, not a programmed assumption.

**Commented cross-dampening in original:** The original model contained commented lines in the appraisal flows for cross-dampening. These are now implemented as a user-controlled switch (cross_dampening) rather than hardcoded, with zero-initialized stocks meaning they have no effect unless initial stocks are pre-seeded.

**Stochastic terms:** RandNormal is used throughout rather than uniform Rand() for theoretical defensibility — outcomes cluster around a typical value with symmetric variation rather than being uniformly distributed across the entire range.
