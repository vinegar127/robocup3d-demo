"""Protect native-opponent identity when Linux builds have no bundled assets."""
from pathlib import Path
import tempfile
import unittest

from tools.opponents import native_assets


class NativeAssetTests(unittest.TestCase):
    def test_my3d_build_does_not_load_apollo_assets(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            apollo = root/'third_party/apollo/assets'
            my3d = root/'third_party/my3d/runtime/apollo/assets'
            for directory, text in [(apollo, 'apollo-original'), (my3d, 'my3d-original')]:
                directory.mkdir(parents=True)
                (directory/'formation.yaml').write_text(text)
            assets = native_assets(root, 'my3d', my3d.parent/'build')
            self.assertEqual((assets/'formation.yaml').read_text(), 'my3d-original')

    def test_bundled_runtime_assets_are_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            runtime = Path(temporary)/'native-runtime'
            (runtime/'assets').mkdir(parents=True)
            self.assertEqual(native_assets(Path(temporary), 'my3d', runtime), runtime/'assets')

    def test_missing_my3d_assets_never_silently_use_apollo(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root/'third_party/apollo/assets').mkdir(parents=True)
            with self.assertRaises(FileNotFoundError):
                native_assets(root, 'my3d', root/'build')


if __name__ == '__main__':
    unittest.main()
