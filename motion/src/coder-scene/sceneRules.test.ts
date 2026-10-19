import assert from 'node:assert/strict';
import {describe, it} from 'node:test';
import {EVENTS} from './fragment';
import {boardMetrics, fitLabel, slotTop} from './sceneRules';

const names = EVENTS.map((event) => event.text);

describe('coder scene readability', () => {
  const board = boardMetrics(504, 1424, 4);
  const inner = board.documentWidth - 36 - 16 - 8;

  it('keeps a document name on one line and inside the scaled card', () => {
    const name = fitLabel('股东决议', inner, board.documentFont, 28, names);
    assert.deepEqual(name.lines, ['股东决议']);
    assert.equal(name.overflow, false);
    assert.ok(board.documentWidth * board.activeScale < 504);
    assert.ok(board.documentHeight * board.activeScale < board.slotHeight);
  });

  it('does not split 股东决议 when a short phrase wraps', () => {
    const joined = fitLabel('或股东决议', inner, board.documentFont, 28, names);
    assert.ok(joined.lines.join('').includes('股东决议'));
    assert.ok(joined.lines.every((line) => !line.endsWith('股') && line !== '东决议'));
  });

  it('wraps a long fixture title to two lines and flags a title that cannot fit', () => {
    const long = fitLabel('这是一个很长的测试标题不会出现在原视频里', inner, board.documentFont, 28, names);
    assert.equal(long.overflow, false);
    assert.equal(long.lines.join(''), '这是一个很长的测试标题不会出现在原视频里');
    assert.ok(long.lines.length <= 2);
    const tooLong = fitLabel('这是故意超长的测试标题用来确认溢出会被标出来而不是悄悄裁掉文字继续继续继续写下去', inner, board.documentFont, 28, names);
    assert.equal(tooLong.overflow, true);
    assert.ok(tooLong.lines.length <= 2);
  });

  it('reserves slots from the full group size', () => {
    const full = boardMetrics(504, 1424, 4);
    assert.ok(slotTop(full, 1) > slotTop(full, 0));
    assert.equal(slotTop(boardMetrics(504, 1424, 4), 2), slotTop(full, 2));
  });
});
