// Native Node regression checks: object and event population are independent.
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
for (const object of ['conditions', 'overall']) {
  explorer.setScope(object);
  for (const population of ['all', 'process']) {
    explorer.setPopulation(population);
    const expected = object === 'conditions'
      ? ['rainfall_concentration', 'antecedent_wetness', ...(population === 'process' ? ['mechanism_share'] : [])]
      : ['direct_runoff_volume', 'flood_peak', population === 'process' ? 'mechanism_frequency' : 'exceedance_frequency'];
    assert.deepEqual(options(), expected);
    const mechanisms = population === 'process' ? explorer.data.meta.mechanisms.map(row => row.id) : [explorer.mechanism];
    for (const mechanism of mechanisms) {
      explorer.setMechanism(mechanism);
      for (const key of expected) {
        explorer.setOutcome(key);
        assert.equal(explorer.outcomeKey, key);
        for (const item of explorer.catchments) {
          const reference = population === 'process' ? item.processes?.[mechanism]?.[key]
            : object === 'conditions' ? item.conditions?.[key] : item.overall?.[key];
          assert.equal(explorer.metric(item), reference);
        }
        if (object === 'conditions' && population === 'all') {
          assert.equal(explorer.outcome().limit, explorer.data.meta.conditionLimits[key]);
        } else {
          assert.equal(explorer.outcome().limit, explorer.data.meta.outcomes[key].limit);
        }
      }
    }
    receipts.push({object, population, outcomes:expected});
  }
}
explorer.setScope('overall');
explorer.setPopulation('all');
explorer.setOutcome('exceedance_frequency');
explorer.setPopulation('process');
assert.equal(explorer.outcomeKey, 'mechanism_frequency');
explorer.setPopulation('all');
assert.equal(explorer.outcomeKey, 'exceedance_frequency');
explorer.setPopulation('process');
explorer.setMechanism('Wet-Volume');
explorer.setScope('conditions');
assert.equal(explorer.population, 'process');
assert.equal(explorer.mechanism, 'Wet-Volume');
explorer.setOutcome('flood_peak');
assert.equal(explorer.outcomeKey, 'rainfall_concentration');
explorer.setOutcome('mechanism_share');
explorer.setPopulation('all');
assert.equal(explorer.outcomeKey, 'rainfall_concentration');
console.log(JSON.stringify({status:'passed', cases:receipts, catchments:explorer.catchments.length}, null, 2));
