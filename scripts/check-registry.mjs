import {loadRegistry} from '../lib/federation.mjs';
const registry=await loadRegistry();
console.log(JSON.stringify({countries:registry.countries.length,sources:registry.sources.length,status:'valid'}));
