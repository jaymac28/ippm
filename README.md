# The Integrated Parallel Processing Model (IPPM)

A systems dynamics respecification and completion of Witte's (1992) Extended Parallel Process Model (EPPM) of fear appeals in health communication.

Version 0.0.2 available on Insight Maker: https://insightmaker.com/insight/7pjXKK2Ctq6obBQ9T9QJ6B

## Overview

The EPPM has accumulated a mixed and contradictory empirical record despite its theoretical elegance and widespread application in public health. This model argues that the apparent failures are methodological rather than theoretical — specifically, that the experimental literature systematically confused message characteristics with perceived characteristics, testing what messages were designed to convey rather than what audiences actually perceived.

This systems dynamics model corrects that error and extends Witte's framework in three ways:

1. **Measurement correction** — The four operative variables (perceived severity, susceptibility, self-efficacy, response efficacy) are treated as empirically measured audience perceptions rather than assumed message properties. This is what Witte's theory actually specifies.

2. **Structural completion** — Witte described the fear reinforcing feedback loop but never specified its balancing counterpart. A reinforcing loop without a balancing loop has no stable attractor. The model adds the *hope loop* — optimism as the balancing counterpart to fear, driven by efficacy experience and positive outcome feedback from adaptive behavior.

3. **Dynamic formalization** — The EPPM as typically depicted is a static branching flowchart. This model represents it as a system of stocks, flows, and feedback loops with a time dimension, revealing attractor dynamics, oscillation behavior, and threshold effects that the original static framework cannot represent.

## Key Findings

- The model correctly reproduces Witte's propositions when perceptual variables are properly specified
- Consistent danger control requires efficacy to *exceed* threat by approximately 0.2 units — matched inputs produce indeterminate mixed behavior, not clean danger control as Witte predicted
- Repeated exposure produces attractor dynamics: well-designed campaigns create oscillating drift toward hope dominance; poorly designed campaigns lock audiences into fear-dominant attractors they cannot escape
- Population variance differentially affects emotional versus behavioral outcomes — emotions are variance-sensitive, behavior is variance-robust
- Witte's P1 (no response to low threat) is not supported by the dynamic model — even minimal threat with zero efficacy produces weak fear control by default

## Model Variables

### Message Resonance Inputs (0–1)
| Variable | Description |
|---|---|
| `severity` | Perceived seriousness of the threat |
| `susceptibility` | Perceived personal relevance of the threat |
| `self_efficacy` | Perceived ability to perform the recommended behavior |
| `response_efficacy` | Perceived effectiveness of the recommended behavior |

### Stocks
| Stock | Description |
|---|---|
| `Threat` | Accumulated threat appraisal |
| `Efficacy` | Accumulated efficacy appraisal |
| `fear` | Negative emotional state; reinforcing loop driver |
| `optimism` | Positive emotional state; hope loop (balancing loop) driver |
| `Maladaptive` | Fear control behaviors |
| `Adaptive` | Danger control behaviors |
| `consequences` | Negative outcome feedback from maladaptive behavior |
| `rewards` | Positive outcome feedback from adaptive behavior |

### Control Variables
| Variable | Default | Description |
|---|---|---|
| `population_variance` | 0.1 | Noise on appraisal; models heterogeneous audience perception |
| `cross_dampening` | 0 | Switch (0/1); enables cognitive interference at message evaluation |
| `repeated_exposure` | 0 | Switch (0/1); fires appraisal pulse at regular intervals |
| `exposure_interval` | 30 | Units between exposures when repeated_exposure=1 |

### Initial State Variables (Individual Differences / P12)
| Variable | Default | Description |
|---|---|---|
| `initial_fear` | 0 | Baseline trait anxiety before message exposure |
| `initial_optimism` | 0 | Baseline dispositional hope before message exposure |
| `initial_threat` | 0 | Pre-existing threat perception |
| `initial_efficacy` | 0 | Pre-existing efficacy belief |

## Key Structural Decisions

**Single pulse appraisal** — By default the appraisal flows fire only at t=0, representing a single message exposure. The model tracks the subsequent emotional and behavioral trajectory. Enable `repeated_exposure` to model campaigns.

**Stock-based behavioral gating** — Danger control fires when `Efficacy >= Threat`; fear control fires when `Threat > Efficacy`. The comparison uses the dynamic stock values, not the input variables, so the perceptual competition can shift during a run as feedback loops operate.

**Continuous competition formulation** — Rather than a binary switch, behavioral flow rates are modulated by the magnitude of the gap between Efficacy and Threat:
```
danger control gap = Max(0, Efficacy - Threat)
fear control gap   = Max(0, Threat - Efficacy)
```
This means both pathways are always potentially active, with rates proportional to perceptual dominance rather than categorical on/off.

**Mutual emotional suppression** — Fear and optimism suppress each other's dissipation:
```
fear dissipation     = fear * 0.05 + optimism * 0.05
optimism dissipation = optimism * 0.05 + fear * 0.05
```
This produces the oscillatory competition between fear and hope observed under repeated exposure.

**The hope loop** — The balancing counterpart to Witte's fear reinforcing loop:
```
Efficacy → (+emotional response) → optimism → (optimism feedback) → Efficacy
rewards  → (optimism reinforcement) → optimism
```
Without this loop the system has no stable attractor on the efficacy side.

## Repository Structure

```
ippm/
├── model/
│   └── IPPM.json              # Insight Maker native model file
├── scenarios/
│   └── propositions.json      # All 12 EPPM proposition scenarios
├── scripts/
│   └── run_scenario.mjs       # Node.js CLI runner
├── docs/
│   └── model_variables.md     # Full variable and equation documentation
├── package.json
└── README.md
```

## Running the Model

### In Insight Maker (recommended for interactive use)

1. Go to [insightmaker.com](https://insightmaker.com) and create a free account
2. From your dashboard, click **New Insight** → **Import**
3. Upload `model/IPPM.json`
4. Use the sliders panel to set scenario variables
5. Click **Simulate**

Alternatively, import directly: **Share → Import → Upload File**

### From the command line (Node.js)

Requires Node.js 16+. Uses the [simulation](https://github.com/scottfr/simulation) package which loads Insight Maker models natively.

```bash
npm install
npm run list        # list available scenarios
npm run p2          # run proposition 2
npm run p3          # run proposition 3
```

For variable overrides, CSV output, repeated exposure, and individual difference modeling see the full CLI usage in `scripts/run_scenario.mjs` or run:

```bash
node scripts/run_scenario.mjs --help

### In R (via sdbuildR)

```r
# install.packages("sdbuildR")
library(sdbuildR)

# Load directly from Insight Maker URL (requires public model)
sfm <- insightmaker_to_sfm(URL = "https://insightmaker.com/insight/YOUR_MODEL_ID")
sim <- simulate(sfm)
plot(sim)
```

### In Python

### From the command line (Python)

Requires Python 3.8+. Independent implementation using numpy/scipy — no external SD package required. Results should be qualitatively identical to the Insight Maker version and serve as a cross-validation of the model.

```bash
pip install -r requirements.txt

python scripts/run_scenario.py --list
python scripts/run_scenario.py --scenario P2
python scripts/run_scenario.py --scenario P3 --format csv --output p3.csv
python scripts/run_scenario.py --scenario P2 --severity 0.7 --self_efficacy 0.9
python scripts/run_scenario.py --scenario P5 --initial_fear 0.8
python scripts/run_scenario.py --scenario P2 --repeated_exposure 1 --exposure_interval 30
python scripts/run_scenario.py --scenario P2 --plot
```

## Proposition Scenarios

| Scenario | Description | Key Variables |
|---|---|---|
| P1 | Minimal threat, no efficacy | severity=0.05, self_efficacy=0 |
| P2 | High efficacy exceeds threat | severity=0.6, self_efficacy=0.8 |
| P3 | High threat, low efficacy | severity=0.8, self_efficacy=0.1 |
| P4 | Extreme threat, minimal efficacy (boomerang) | severity=0.9, self_efficacy=0.05 |
| P5 | High threat, moderate efficacy (unstable) | severity=0.8, self_efficacy=0.5 |
| P6 | Fear/fear control decoupling (structural) | Same as P3 |
| P7 | Efficacy/danger control decoupling (structural) | Same as P2 |
| P8 | Fear spiral isolation | severity=0.5, self_efficacy=0.1 |
| P9 | Maximum threat + efficacy | severity=0.9, self_efficacy=0.9 |
| P10 | Maximum threat, minimum efficacy | severity=0.9, self_efficacy=0.1 |
| P11 | Comparative: efficacy determines nature, threat determines intensity | Compare P2, P3, P5 |
| P12 | Individual differences (vary initial_fear on P5) | initial_fear: 0.2 / 0.5 / 0.8 |

## What to Chart

For each scenario, the four primary charts are:

1. **Adaptive vs Maladaptive** — Primary behavioral outcome; ratio during active window is the core validation criterion
2. **fear vs optimism** — Emotional dynamics; which feedback loop is dominating and how amplitude envelopes shift under repeated exposure
3. **Efficacy vs Threat** — Appraisal stocks; confirms message inputs produced intended perceptual loading
4. **rewards vs consequences** — Outcome feedback layer; whether behavioral loops are generating meaningful feedback signals

## Theoretical Background

This model draws on:
- Witte, K. (1992). Putting the fear back into fear appeals: The extended parallel process model. *Communication Monographs, 59*, 329–349.
- Leventhal, H. (1970). Findings and theory in the study of fear communications. In *Advances in experimental social psychology* (Vol. 5). Academic Press.
- Rogers, R. W. (1975). A protection motivation theory of fear appeals and attitude change. *Journal of Psychology, 91*(1), 93–114.
- Popova, L. (2012). The extended parallel process model: Illuminating the gaps in research. *Health Education & Behavior, 39*(4), 455–473.
- Peters, G. J. Y., Ruiter, R. A., & Kok, G. (2013). Threatening communication: A critical re-analysis and a revised meta-analytic test of fear appeal theory. *Health Psychology Review, 7*(sup1), S8–S31.
- Dillard, J. P., Plotnick, C. A., Godbold, L. C., Freimuth, V. S., & Edgar, T. (1996). The multiple affective outcomes of AIDS PSAs. *Communication Research, 23*(1), 44–72.

## Version History

- **0.0.2** — Current version. Adds hope loop, continuous competition formulation, initial state variables, repeated exposure switch, cross-dampening switch, population variance, corrected dissipation rates
- **0.0.1** — Initial model with basic stock/flow structure

## Citation

If you use this model in research, please cite:

> McLachlan, Justin. (2025). *The Integrated Parallel Processing Model (IPPM): A systems dynamics respecification of the Extended Parallel Process Model* (Version 0.0.2). GitHub. https://github.com/jaymac28/ippm

## License

MIT License. See LICENSE file.
