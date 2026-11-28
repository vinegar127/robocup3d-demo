"""Local RCSSServerMJ 0.2.1 workaround for invalid controls after model recompile.

Preserves finite controls by actuator name and initializes newly added actuators
to zero before the first forward-dynamics call. No game rules are changed.
"""
import importlib.metadata
from pathlib import Path
import rcsssmj.sim.simulation

if importlib.metadata.version('rcsssmj') != '0.2.1':
    raise SystemExit('This workaround applies only to rcsssmj 0.2.1')
path = Path(rcsssmj.sim.simulation.__file__)
text = path.read_text(encoding='utf-8')
marker = '# local: preserve actuator controls by name across recompile'
old = '        self._mj_model, self._mj_data = self._mj_spec.recompile(self._mj_model, self._mj_data)'
new = '''        # local: preserve actuator controls by name across recompile
        previous_controls = {
            self._mj_model.actuator(i).name: float(value)
            for i, value in enumerate(self._mj_data.ctrl)
            if np.isfinite(value) and abs(value) < 1e6
        }
        self._mj_model, self._mj_data = self._mj_spec.recompile(self._mj_model, self._mj_data)
        self._mj_data.ctrl[:] = [
            previous_controls.get(self._mj_model.actuator(i).name, 0.0)
            for i in range(self._mj_model.nu)
        ]'''
if marker in text:
    print('Recompile-control workaround already present')
elif text.count(old) == 1:
    backup = path.with_suffix('.py.original')
    if not backup.exists():
        backup.write_bytes(path.read_bytes())
    path.write_text(text.replace(old, new), encoding='utf-8')
    print('Applied local recompile-control workaround:', path)
else:
    raise SystemExit('Unexpected source; nothing changed')
