# test_naming_cases.py — the synced vfclamp_naming.range_name() against naming-cases.json, the cases npm's rangeName() and RoboFont are checked with.
import json, os
import pytest
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "vf-clamp.roboFontExt", "lib", "vfClamp"))
import vfclamp_naming as N

CASES = json.load(open(os.path.join(os.path.dirname(__file__), 'naming-cases.json'), encoding='utf-8'))


@pytest.mark.parametrize('case', CASES['cases'], ids=lambda c: f"{c['font']}: {' + '.join(c['selected'])}")
def test_range_name(case):
	font = CASES['fonts'][case['font']]
	selected = [next(i for i in font['instances'] if i['name'] == n) for n in case['selected']]
	assert N.range_name(selected, font['instances'], font['axes'], font['labels']) == case['expected']
