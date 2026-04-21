/**
 * run_scenario.mjs
 * 
 * Command-line runner for IPPM scenarios using the `simulation` npm package.
 * Loads the IPPM model JSON, applies scenario variable overrides, runs the
 * simulation, and outputs results as CSV or JSON.
 * 
 * Usage:
 *   node run_scenario.mjs --scenario P2
 *   node run_scenario.mjs --scenario P3 --format csv
 *   node run_scenario.mjs --scenario P2 --severity 0.7 --self_efficacy 0.9
 *   node run_scenario.mjs --list
 * 
 * Requirements:
 *   npm install simulation
 */

import { readFileSync, writeFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..');

// --- Argument parsing ---
const args = process.argv.slice(2);
const getArg = (flag) => {
  const i = args.indexOf(flag);
  return i !== -1 ? args[i + 1] : null;
};
const hasFlag = (flag) => args.includes(flag);

// --- Load model and scenarios ---
const modelText = readFileSync(join(ROOT, 'model', 'IPPM.json'), 'utf8');
const scenarioData = JSON.parse(readFileSync(join(ROOT, 'scenarios', 'propositions.json'), 'utf8'));

// --- List scenarios ---
if (hasFlag('--list')) {
  console.log('\nAvailable scenarios:\n');
  scenarioData.scenarios.forEach(s => {
    console.log(`  ${s.id.padEnd(6)} ${s.name}`);
  });
  console.log('\nUsage: node run_scenario.mjs --scenario <ID>\n');
  process.exit(0);
}

// --- Load simulation package ---
let loadInsightMaker, Model;
try {
  const sim = await import('simulation');
  loadInsightMaker = sim.loadInsightMaker;
  Model = sim.Model;
} catch (e) {
  console.error('\nError: simulation package not found.');
  console.error('Install it with: npm install simulation\n');
  process.exit(1);
}

// --- Get scenario ---
const scenarioId = getArg('--scenario');
if (!scenarioId) {
  console.error('\nError: --scenario flag required. Use --list to see available scenarios.\n');
  process.exit(1);
}

const scenario = scenarioData.scenarios.find(s => s.id === scenarioId);
if (!scenario) {
  console.error(`\nError: Scenario "${scenarioId}" not found. Use --list to see available scenarios.\n`);
  process.exit(1);
}

if (!scenario.variables) {
  console.log(`\nScenario ${scenarioId} is a comparative scenario.`);
  console.log(`Compare these scenarios: ${scenario.compare.join(', ')}`);
  console.log(`\nExpected: ${scenario.expected}\n`);
  process.exit(0);
}

// --- Build variable overrides from CLI args ---
const cliOverrides = {};
const overridableVars = [
  'severity', 'susceptibility', 'self_efficacy', 'response_efficacy',
  'population_variance', 'cross_dampening', 'repeated_exposure',
  'exposure_interval', 'initial_fear', 'initial_optimism',
  'initial_threat', 'initial_efficacy'
];

overridableVars.forEach(v => {
  const val = getArg(`--${v}`);
  if (val !== null) cliOverrides[v] = parseFloat(val);
});

// Merge scenario variables with CLI overrides
const variables = { ...scenario.variables, ...cliOverrides };

// --- Load and configure model ---
console.log(`\nRunning scenario: ${scenario.name}`);
console.log(`Description: ${scenario.description}\n`);

const model = loadInsightMaker(modelText);

// Apply variable values
overridableVars.forEach(varName => {
  if (variables[varName] !== undefined && variables[varName] !== null) {
    const primitive = model.getVariable(v => v.name === varName || v.name === varName + ' ');
    if (primitive) {
      primitive.value = variables[varName];
    }
  }
});

// --- Run simulation ---
const results = model.simulate();

// --- Output tracked variables ---
const tracked = [
  'Threat', 'Efficacy', 'fear', 'optimism',
  'Adaptive', 'Maladaptive', 'rewards', 'consequences'
];

const format = getArg('--format') || 'json';
const outputFile = getArg('--output');

if (format === 'csv') {
  const times = results.times();
  const header = ['time', ...tracked].join(',');
  const rows = times.map((t, i) => {
    const values = tracked.map(name => {
      const prim = model.getVariable(v => v.name === name);
      if (!prim) return '';
      const series = results.series(prim);
      return series ? series[i] : '';
    });
    return [t, ...values].join(',');
  });
  const csv = [header, ...rows].join('\n');

  if (outputFile) {
    writeFileSync(outputFile, csv);
    console.log(`Results written to ${outputFile}`);
  } else {
    console.log(csv);
  }
} else {
  // JSON output
  const times = results.times();
  const output = {
    scenario: scenario.id,
    name: scenario.name,
    variables,
    expected: scenario.expected,
    results: {}
  };

  tracked.forEach(name => {
    const prim = model.getVariable(v => v.name === name);
    if (prim) {
      const series = results.series(prim);
      if (series) output.results[name] = Array.from(series);
    }
  });

  output.results.time = Array.from(times);

  // Summary statistics at end of active window (t=300) and end of run (t=600)
  const t300idx = times.findIndex(t => t >= 300);
  const t600idx = times.length - 1;

  const getVal = (name, idx) => {
    const prim = model.getVariable(v => v.name === name);
    if (!prim) return null;
    const series = results.series(prim);
    return series ? series[idx] : null;
  };

  output.summary = {
    at_t300: {
      Adaptive: getVal('Adaptive', t300idx),
      Maladaptive: getVal('Maladaptive', t300idx),
      ratio_adaptive_maladaptive: getVal('Adaptive', t300idx) / (getVal('Maladaptive', t300idx) || 0.0001),
      fear: getVal('fear', t300idx),
      optimism: getVal('optimism', t300idx)
    },
    at_t600: {
      Adaptive: getVal('Adaptive', t600idx),
      Maladaptive: getVal('Maladaptive', t600idx),
      ratio_adaptive_maladaptive: getVal('Adaptive', t600idx) / (getVal('Maladaptive', t600idx) || 0.0001),
      fear: getVal('fear', t600idx),
      optimism: getVal('optimism', t600idx)
    }
  };

  const jsonOutput = JSON.stringify(output, null, 2);

  if (outputFile) {
    writeFileSync(outputFile, jsonOutput);
    console.log(`Results written to ${outputFile}`);
  } else {
    console.log(jsonOutput);
  }
}
