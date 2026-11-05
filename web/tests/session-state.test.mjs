import test from 'node:test';
import assert from 'node:assert/strict';
import { createIdentityScope } from '../src/session-state.js';

test('old reads are invalid after sign-out and account switch', () => {
  const scope=createIdentityScope();
  scope.setUser('A');const a=scope.ticket();
  scope.setUser(null);assert.equal(scope.accepts(a),false);
  scope.setUser('B');assert.equal(scope.accepts(a),false);
  assert.equal(scope.accepts(scope.ticket()),true);
});
test('returning to the same user cannot revive a previous request', () => {
  const scope=createIdentityScope();scope.setUser('A');const old=scope.ticket();
  scope.setUser(null);scope.setUser('A');assert.equal(scope.accepts(old),false);
});
test('a token refresh for the same identity preserves current requests', () => {
  const scope=createIdentityScope();scope.setUser('A');const current=scope.ticket();
  assert.equal(scope.setUser('A'),false);assert.equal(scope.accepts(current),true);
});
