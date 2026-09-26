import { test } from 'node:test';
import assert from 'node:assert/strict';
import { matchesEntry, topicIds, plainText } from '../src/lib/discovery.ts';

test('search combines all words with topic, kind and month filters', () => {
  const entry = { text: 'ROS 2 Nav2 업데이트', topics: ['ros', 'navigation'], kind: 'daily', date: '2026-09-25' };
  const filters = { query: 'ＮＡＶ２ 업데이트', topic: 'navigation', kind: 'daily', month: '2026-09' };
  assert.equal(matchesEntry(entry, filters), true);
  for (const change of [{ query: 'Nav2 없는단어' }, { topic: 'industry' }, { kind: 'weekly' }, { month: '2026-08' }]) {
    assert.equal(matchesEntry(entry, { ...filters, ...change }), false);
  }
  assert.equal(matchesEntry(entry, { query: '  ', topic: '', kind: '', month: '' }), true);
});

test('topics describe editorial content rather than unused reference titles', () => {
  assert.deepEqual(topicIds('## 로보틱스\n- **Nav2** 업데이트\n### 🔗 출처 및 원문\nOllama'), ['navigation']);
  assert.deepEqual(topicIds('ROS 2의 Cyclone DDS와 Gazebo'), ['ros', 'simulation']);
  assert.equal(plainText('**업데이트** [Nav2](https://example.com) <span>출처</span>'), '업데이트 Nav2 출처');
});
