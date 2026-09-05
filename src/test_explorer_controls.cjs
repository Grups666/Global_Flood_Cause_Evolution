// Native Node regression checks: object and both event-filter axes are independent.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const context = {window: {}, innerWidth: 1366, innerHeight: 900};
vm.runInNewContext(fs.readFileSync(path.join(root, 'public/modules/flood-cause-evolution/index.js'), 'utf8'), context);
const explorer = new context.window.FloodCauseEvolutionModule({});
explorer.data = JSON.parse(fs.readFileSync(path.join(root, 'public/modules/flood-cause-evolution/data/flood-cause-explorer.json'), 'utf8'));
explorer.catchments = explorer.data.catchments;
for (const method of ['updateToolbar', 'updateLegend', 'redraw']) explorer[method] = () => {};
const options = () => Array.from(explorer.availableOutcomes());
const receipts = [];
assert.equal(explorer.mechanism, 'All-All');
assert.equal(explorer.population, 'all');
assert.equal(explorer.data.meta.filterGroups.length, 12);
for (const object of ['conditions', 'overall']) {
  explorer.setScope(object);
  for (const wetness of ['All', 'Dry', 'Moderate', 'Wet']) {
    for (const forcing of ['All', 'Intensity', 'Volume']) {
      const mechanism = `${wetness}-${forcing}`;
      explorer.setMechanism(mechanism);
      const population = mechanism === 'All-All' ? 'all' : 'process';
      assert.equal(explorer.population, population);
      assert.equal(explorer.mechanism, mechanism);
      const expected = object === 'conditions'
        ? ['rainfall_concentration', 'antecedent_wetness', ...(population === 'process' ? ['mechanism_share'] : [])]
        : ['direct_runoff_volume', 'flood_peak', population === 'process' ? 'mechanism_frequency' : 'exceedance_frequency'];
      assert.deepEqual(options(), expected);
      for (const key of expected) {
        explorer.setOutcome(key);
        assert.equal(explorer.outcomeKey, key);
        for (const item of explorer.catchments) {
          const reference = population === 'process' ? item.processes?.[mechanism]?.[key]
            : object === 'conditions' ? item.conditions?.[key] : item.overall?.[key];
          assert.equal(explorer.metric(item), reference);
        }
        assert(explorer.catchments.some(item => explorer.metric(item)), `${mechanism}/${key} must have actual fitted data`);
        if (object === 'conditions' && population === 'all') {
          assert.equal(explorer.outcome().limit, explorer.data.meta.conditionLimits[key]);
        } else {
          assert.equal(explorer.outcome().limit, explorer.data.meta.outcomes[key].limit);
        }
      }
      receipts.push({object, mechanism, outcomes:expected});
    }
  }
}
explorer.setScope('overall');
explorer.setMechanism('All-All');
explorer.setOutcome('exceedance_frequency');
explorer.setMechanism('Wet-All');
assert.equal(explorer.outcomeKey, 'mechanism_frequency');
explorer.setMechanism('All-All');
assert.equal(explorer.outcomeKey, 'exceedance_frequency');
explorer.setMechanism('Wet-Volume');
explorer.setScope('conditions');
assert.equal(explorer.population, 'process');
assert.equal(explorer.mechanism, 'Wet-Volume');
explorer.setOutcome('flood_peak');
assert.equal(explorer.outcomeKey, 'rainfall_concentration');
explorer.setOutcome('mechanism_share');
explorer.setMechanism('All-All');
assert.equal(explorer.outcomeKey, 'rainfall_concentration');
explorer.setMechanism('All-Intensity');
assert.equal(explorer.processLabel(), 'all antecedent wetness · intensity-led');
explorer.setMechanism('Wet-All');
assert.equal(explorer.processLabel(), 'wet antecedent soil · all rainfall forcing');
explorer.setMechanism('Unknown-All');
assert.equal(explorer.mechanism, 'Wet-All');
// Exercise the inspector on both marginal axes: no inapplicable rainfall gate.
let inspector = '';
explorer.app.showInspector = (_title, html) => { inspector = html; };
explorer.setOutcome('rainfall_concentration');
explorer.showInspector(explorer.catchments.find(item => explorer.metric(item)));
assert(!inspector.includes('Classification threshold'));
explorer.setMechanism('All-Intensity');
explorer.showInspector(explorer.catchments.find(item => explorer.metric(item)));
assert(inspector.includes('Classification threshold'));
const source = fs.readFileSync(path.join(root, 'public/modules/flood-cause-evolution/index.js'), 'utf8');
assert(!source.includes('data-population'));
assert(!source.includes('Intensity-led rainfall</option>'));
assert(!source.includes('Volume-led rainfall</option>'));
console.log(JSON.stringify({status:'passed', cases:receipts, catchments:explorer.catchments.length}, null, 2));
