# test_review_fixes.py — regression tests for the October 2026 review of the controller's clamping pipeline (STAT links, RIBBI names and bits, instance PostScript names, safe PostScript names), with vanilla stubbed so the controller imports outside RoboFont.

import os
import sys
import types
import unittest

LIB = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'vf-clamp.roboFontExt', 'lib'))
INTER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'fixtures', 'Inter-Variable.ttf'))


class _Anything:
	"""Stand-in for any vanilla class or attribute: subclassable, callable, attribute-tolerant."""

	def __init__(self, *args, **kwargs):
		pass

	def __getattr__(self, name):
		return _Anything()

	def __call__(self, *args, **kwargs):
		return _Anything()


def _import_controller():
	"""Import vfClamp.controller with a stub vanilla module (RoboFont's UI toolkit isn't installed here)."""
	if 'vanilla' not in sys.modules:
		stub = types.ModuleType('vanilla')
		stub.__getattr__ = lambda name: _Anything
		sys.modules['vanilla'] = stub
	if LIB not in sys.path:
		sys.path.insert(0, LIB)
	from vfClamp import controller
	return controller


try:
	controller = _import_controller()
	_IMPORT_ERROR = None
except Exception as e:  # AppKit missing on non-macOS CI, etc.
	controller = None
	_IMPORT_ERROR = e

from fontTools.ttLib import TTFont


@unittest.skipIf(controller is None, f'controller not importable here: {_IMPORT_ERROR}')
@unittest.skipIf(not os.path.exists(INTER), 'Inter fixture not found')
class ReviewFixes(unittest.TestCase):
	"""Run the real pipeline on Inter and check the output tables."""

	def _clamp(self, names, family, font=None):
		"""Clamp `font` (default Inter) to the named instances and reopen the saved result."""
		import tempfile
		font = font or TTFont(INTER)
		labels = [controller._get_instance_label(font['name'], inst, i) for i, inst in enumerate(font['fvar'].instances)]
		keys = [labels.index(n) for n in names]
		out = os.path.join(tempfile.mkdtemp(), 'out.ttf')
		controller.produce_restricted_vf(font, keys, family, out, overwrite=True)
		return TTFont(out)

	def test_instance_postscript_names_follow_new_prefix(self):
		f = self._clamp(['Regular', 'Medium', 'SemiBold', 'Bold'], 'Inter Regular-Bold')
		ps = [f['name'].getDebugName(i.postscriptNameID) for i in f['fvar'].instances if i.postscriptNameID != 0xFFFF]
		self.assertTrue(ps)
		self.assertFalse(any(p.startswith('InterVariable') for p in ps))

	def test_stat_keeps_ital(self):
		f = self._clamp(['Regular', 'Medium', 'SemiBold', 'Bold'], 'Inter Regular-Bold')
		self.assertIn('ital', [a.AxisTag for a in f['STAT'].table.DesignAxisRecord.Axis])

	def test_no_link_to_weight_zero(self):
		"""Out-of-range links become Format 1, never a Format 3 link to 0."""
		f = self._clamp(['Light', 'Regular'], 'Inter Light-Regular')
		for av in f['STAT'].table.AxisValueArray.AxisValue:
			if av.Format == 3:
				self.assertNotEqual(av.LinkedValue, 0)

	def test_pinned_bold_is_ribbi_bold(self):
		f = self._clamp(['Bold'], 'Inter Bold')
		fs = f['OS/2'].fsSelection
		self.assertTrue(fs & 0x20)
		self.assertFalse(fs & 0x40)
		self.assertEqual(f['name'].getDebugName(2), 'Bold')

	def test_italic_source_never_regular_and_italic(self):
		src = TTFont(INTER)
		src['OS/2'].fsSelection = (src['OS/2'].fsSelection & ~0x40) | 0x01
		f = self._clamp(['Regular', 'Medium', 'SemiBold', 'Bold'], 'Inter Italic Regular-Bold', font=src)
		fs = f['OS/2'].fsSelection
		self.assertTrue(fs & 0x01)
		self.assertFalse(fs & 0x40)
		self.assertEqual(f['name'].getDebugName(2), 'Italic')

	def test_postscript_names(self):
		self.assertEqual(controller._sanitize_ps_name('Été Grotesk'), 'Ete-Grotesk')
		self.assertTrue(controller._sanitize_ps_name('源ノ角ゴシック').startswith('Font-'))
		a = controller._sanitize_ps_name('Very Long Family Name Extended Condensed Display Text Regular-Bold A')
		b = controller._sanitize_ps_name('Very Long Family Name Extended Condensed Display Text Regular-Bold B')
		self.assertLessEqual(len(a), 63)
		self.assertNotEqual(a, b)


if __name__ == '__main__':
	unittest.main()
