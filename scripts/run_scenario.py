"""
run_scenario.py

Command-line runner for the Integrated Parallel Processing Model (IPPM).
Implements the model directly using scipy for RK4 numerical integration.
No external SD package required beyond standard scientific Python stack.

This is an independent Python implementation of the same model defined in
model/IPPM.json (Insight Maker format). Results should be qualitatively
identical — any discrepancy between this and the Insight Maker version is
worth investigating as a model validation check.

Usage:
    python scripts/run_scenario.py --list
    python scripts/run_scenario.py --scenario P2
    python scripts/run_scenario.py --scenario P3 --format csv
    python scripts/run_scenario.py --scenario P2 --severity 0.7 --self_efficacy 0.9
    python scripts/run_scenario.py --scenario P5 --initial_fear 0.8
    python scripts/run_scenario.py --scenario P2 --repeated_exposure 1 --exposure_interval 30
    python scripts/run_scenario.py --scenario P2 --plot

Requirements:
    pip install numpy scipy pandas matplotlib
"""

import argparse
import json
import sys
import os
import numpy as np
from scipy.integrate import solve_ivp
import pandas as pd

# ---------------------------------------------------------------------------
# Load scenarios
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
SCENARIOS_PATH = os.path.join(ROOT_DIR, 'scenarios', 'propositions.json')

with open(SCENARIOS_PATH, 'r') as f:
    SCENARIO_DATA = json.load(f)

SCENARIOS = {s['id']: s for s in SCENARIO_DATA['scenarios']}

# ---------------------------------------------------------------------------
# Model implementation
# ---------------------------------------------------------------------------

# Stocks vector index mapping
S_THREAT      = 0
S_EFFICACY    = 1
S_FEAR        = 2
S_OPTIMISM    = 3
S_ADAPTIVE    = 4
S_MALADAPTIVE = 5
S_REWARDS     = 6
S_CONSEQUENCES= 7

STOCK_NAMES = ['Threat', 'Efficacy', 'fear', 'optimism',
               'Adaptive', 'Maladaptive', 'rewards', 'consequences']


def make_model(params):
    """
    Returns the ODE right-hand-side function for the IPPM given a params dict.
    Uses a seeded RNG for reproducibility. Stochastic terms use fixed random
    draws per timestep, approximating the Insight Maker RandNormal behavior.
    """
    rng = np.random.default_rng(params.get('seed', 42))

    severity         = params['severity']
    susceptibility   = params['susceptibility']
    self_efficacy    = params['self_efficacy']
    response_efficacy= params['response_efficacy']
    pop_var          = params['population_variance']
    cross_damp       = params['cross_dampening']
    rep_exposure     = params['repeated_exposure']
    exp_interval     = params['exposure_interval']

    def appraisal_fires(t):
        """Returns True if the appraisal pulse should fire at time t."""
        if t < 1.0:
            return True
        if rep_exposure and exp_interval > 0:
            return (t % exp_interval) < 1.0
        return False

    def model(t, y):
        Threat       = max(0.0, y[S_THREAT])
        Efficacy     = max(0.0, y[S_EFFICACY])
        fear         = max(0.0, y[S_FEAR])
        optimism     = max(0.0, y[S_OPTIMISM])
        Adaptive     = max(0.0, y[S_ADAPTIVE])
        Maladaptive  = max(0.0, y[S_MALADAPTIVE])
        rewards      = max(0.0, y[S_REWARDS])
        consequences = max(0.0, y[S_CONSEQUENCES])

        # --- Appraisal flows (single pulse at t=0, or repeated) ---
        if appraisal_fires(t):
            sev  = rng.normal(severity, pop_var)
            susc = rng.normal(susceptibility, pop_var)
            base_threat = sev + susc

            se   = rng.normal(self_efficacy, pop_var)
            re   = rng.normal(response_efficacy, pop_var)
            base_efficacy = se + re

            if cross_damp:
                damp_threat   = (optimism + rewards) * 0.1
                damp_efficacy = (fear + consequences) * 0.1
            else:
                damp_threat   = 0.0
                damp_efficacy = 0.0

            threat_appraisal   = max(0.0, base_threat   - damp_threat)
            efficacy_appraisal = max(0.0, base_efficacy - damp_efficacy)
        else:
            threat_appraisal   = 0.0
            efficacy_appraisal = 0.0

        # --- Emotional response flows ---
        neg_emotional_response = Threat   * 0.1
        pos_emotional_response = Efficacy * 0.1

        # --- Feedback flows ---
        fear_feedback     = fear     * 0.1
        optimism_feedback = optimism * 0.1

        # --- Dissipation flows ---
        threat_dissipation   = Threat   * 0.05
        efficacy_dissipation = Efficacy * 0.05
        fear_dissipation     = fear     * 0.05 + optimism * 0.05
        optimism_dissipation = optimism * 0.05 + fear     * 0.05

        # Stochastic dissipation for rewards and consequences
        reward_dissipation      = max(0.0, rng.normal(0.01, 0.005))
        consequence_dissipation = max(0.0, rng.normal(0.01, 0.005))

        # --- Behavioral flows (continuous competition formulation) ---
        # Gap determines which pathway is active and at what rate
        danger_gap = max(0.0, Efficacy - Threat)
        fear_gap   = max(0.0, Threat   - Efficacy)

        danger_control = (Efficacy + consequences * 0.1) * danger_gap
        fear_control   = (Threat   + rewards      * 0.1) * fear_gap

        # --- Outcome feedback flows ---
        fear_reinforcement     = consequences * 0.1
        optimism_reinforcement = rewards      * 0.1

        # --- Pathway outcome flows ---
        reward_pathway = max(0.0,
            Adaptive - (self_efficacy + response_efficacy) * rng.normal(0.5, 0.15))
        pain_pathway   = max(0.0,
            Maladaptive - (severity + susceptibility) * rng.normal(0.5, 0.15))

        # --- Derivatives ---
        dThreat       = (threat_appraisal
                         + fear_feedback
                         - fear_control          # outflow via fear control
                         - threat_dissipation)

        dEfficacy     = (efficacy_appraisal
                         + optimism_feedback
                         - danger_control        # outflow via danger control
                         - efficacy_dissipation)

        dFear         = (neg_emotional_response
                         + fear_reinforcement
                         - fear_dissipation)

        dOptimism     = (pos_emotional_response
                         + optimism_reinforcement
                         - optimism_dissipation)

        dAdaptive     = (danger_control
                         - reward_pathway)

        dMaladaptive  = (fear_control
                         - pain_pathway)

        dRewards      = (reward_pathway
                         - reward_dissipation)

        dConsequences = (pain_pathway
                         - consequence_dissipation)

        return [dThreat, dEfficacy, dFear, dOptimism,
                dAdaptive, dMaladaptive, dRewards, dConsequences]

    return model


def run(params):
    """
    Runs the simulation and returns a pandas DataFrame with time series results.
    """
    t_start  = 0
    t_end    = 600
    t_eval   = np.arange(t_start, t_end + 1, 1.0)

    y0 = [
        params.get('initial_threat',   0.0),   # Threat
        params.get('initial_efficacy', 0.0),   # Efficacy
        params.get('initial_fear',     0.0),   # fear
        params.get('initial_optimism', 0.0),   # optimism
        0.0,                                   # Adaptive
        0.0,                                   # Maladaptive
        0.0,                                   # rewards
        0.0,                                   # consequences
    ]

    model_fn = make_model(params)

    sol = solve_ivp(
        model_fn,
        [t_start, t_end],
        y0,
        method='RK45',      # scipy's adaptive RK; equivalent to RK4 for this model
        t_eval=t_eval,
        max_step=1.0,       # enforce maximum step size of 1 unit, matching IM setting
        dense_output=False
    )

    if not sol.success:
        raise RuntimeError(f"Simulation failed: {sol.message}")

    df = pd.DataFrame(sol.y.T, columns=STOCK_NAMES)
    df.insert(0, 'time', sol.t)

    # Enforce non-negativity (mirrors Insight Maker non-negative stock setting)
    for col in STOCK_NAMES:
        df[col] = df[col].clip(lower=0.0)

    return df


def summary(df):
    """Returns a summary dict at t=300 and t=600."""
    def row_at(t):
        idx = (df['time'] - t).abs().idxmin()
        r = df.iloc[idx]
        mal = r['Maladaptive'] if r['Maladaptive'] > 0 else 0.0001
        return {
            'Adaptive':                    round(r['Adaptive'],     4),
            'Maladaptive':                 round(r['Maladaptive'],  4),
            'ratio_adaptive_maladaptive':  round(r['Adaptive'] / mal, 4),
            'fear':                        round(r['fear'],         4),
            'optimism':                    round(r['optimism'],     4),
        }
    return {'at_t300': row_at(300), 'at_t600': row_at(600)}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description='Run IPPM proposition scenarios',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('--list',      action='store_true',
                        help='List available scenarios')
    parser.add_argument('--scenario',  type=str,
                        help='Scenario ID to run (e.g. P2)')
    parser.add_argument('--format',    type=str, default='json',
                        choices=['json', 'csv'],
                        help='Output format (default: json)')
    parser.add_argument('--output',    type=str,
                        help='Save results to file')
    parser.add_argument('--plot',      action='store_true',
                        help='Show matplotlib plot of results')
    parser.add_argument('--seed',      type=int, default=42,
                        help='Random seed for reproducibility (default: 42)')

    # Variable overrides
    var_group = parser.add_argument_group('variable overrides')
    for v in ['severity', 'susceptibility', 'self_efficacy', 'response_efficacy',
              'population_variance']:
        var_group.add_argument(f'--{v}', type=float)
    var_group.add_argument('--cross_dampening',   type=int, choices=[0, 1])
    var_group.add_argument('--repeated_exposure', type=int, choices=[0, 1])
    var_group.add_argument('--exposure_interval', type=float)
    var_group.add_argument('--initial_fear',      type=float)
    var_group.add_argument('--initial_optimism',  type=float)
    var_group.add_argument('--initial_threat',    type=float)
    var_group.add_argument('--initial_efficacy',  type=float)

    return parser.parse_args()


def main():
    args = parse_args()

    if args.list:
        print('\nAvailable scenarios:\n')
        for s in SCENARIO_DATA['scenarios']:
            print(f"  {s['id']:<6} {s['name']}")
        print('\nUsage: python scripts/run_scenario.py --scenario <ID>\n')
        sys.exit(0)

    if not args.scenario:
        print('Error: --scenario required. Use --list to see options.')
        sys.exit(1)

    scenario = SCENARIOS.get(args.scenario.upper())
    if not scenario:
        print(f"Error: Scenario '{args.scenario}' not found. Use --list.")
        sys.exit(1)

    if scenario.get('variables') is None:
        print(f"\nScenario {args.scenario} is a comparative scenario.")
        print(f"Compare: {', '.join(scenario.get('compare', []))}")
        print(f"\nExpected: {scenario['expected']}\n")
        sys.exit(0)

    # Build params from scenario then apply CLI overrides
    params = dict(scenario['variables'])
    params['seed'] = args.seed

    override_keys = [
        'severity', 'susceptibility', 'self_efficacy', 'response_efficacy',
        'population_variance', 'cross_dampening', 'repeated_exposure',
        'exposure_interval', 'initial_fear', 'initial_optimism',
        'initial_threat', 'initial_efficacy'
    ]
    for key in override_keys:
        val = getattr(args, key, None)
        if val is not None:
            params[key] = val

    print(f"\nScenario: {scenario['name']}")
    print(f"Description: {scenario['description']}\n")

    # Run simulation
    df = run(params)
    s  = summary(df)

    if args.plot:
        try:
            import matplotlib.pyplot as plt
            fig, axes = plt.subplots(2, 2, figsize=(12, 8))
            fig.suptitle(scenario['name'], fontsize=11)

            axes[0, 0].plot(df['time'], df['Adaptive'],    label='Adaptive',    color='steelblue')
            axes[0, 0].plot(df['time'], df['Maladaptive'], label='Maladaptive', color='yellowgreen')
            axes[0, 0].set_title('Adaptive vs Maladaptive')
            axes[0, 0].legend()

            axes[0, 1].plot(df['time'], df['fear'],     label='fear',     color='steelblue')
            axes[0, 1].plot(df['time'], df['optimism'], label='optimism', color='yellowgreen')
            axes[0, 1].set_title('Fear vs Optimism')
            axes[0, 1].legend()

            axes[1, 0].plot(df['time'], df['Efficacy'], label='Efficacy', color='steelblue')
            axes[1, 0].plot(df['time'], df['Threat'],   label='Threat',   color='yellowgreen')
            axes[1, 0].set_title('Efficacy vs Threat')
            axes[1, 0].legend()

            axes[1, 1].plot(df['time'], df['rewards'],      label='rewards',      color='steelblue')
            axes[1, 1].plot(df['time'], df['consequences'], label='consequences', color='yellowgreen')
            axes[1, 1].set_title('Rewards vs Consequences')
            axes[1, 1].legend()

            for ax in axes.flat:
                ax.set_xlabel('Time')
                ax.set_ylabel('Value')
                ax.grid(True, alpha=0.3)

            plt.tight_layout()
            plt.show()
        except ImportError:
            print('matplotlib not installed. Install with: pip install matplotlib')

    # Output
    if args.format == 'csv':
        output = df.to_csv(index=False)
    else:
        result = {
            'scenario': scenario['id'],
            'name':     scenario['name'],
            'params':   {k: v for k, v in params.items() if k != 'seed'},
            'expected': scenario['expected'],
            'summary':  s,
            'results':  df.to_dict(orient='list')
        }
        output = json.dumps(result, indent=2)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Results written to {args.output}")
    else:
        print(output)


if __name__ == '__main__':
    main()
