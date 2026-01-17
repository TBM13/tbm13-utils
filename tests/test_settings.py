import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

import tbm13_utils.settings as settings
from tbm13_utils.encoding import SerializableFile
from tbm13_utils.settings import RawSetting, Setting


class TestSettings(unittest.TestCase):
    def setUp(self):
        # Create temp dir & SerializableFile
        self.test_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.test_dir, 'test_config.json')
        self.settings_file: SerializableFile[str, RawSetting] = SerializableFile(self.config_path, 'key', RawSetting)
        
        # Patch the _settings object in the settings module
        self.patcher = patch.object(settings, '_settings', self.settings_file)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.test_dir)

    def test_default_value(self):
        setting = Setting('test_key', int, 10)
        self.assertEqual(setting.value, 10)

        # Since the setting has the default value, it shouldn't have been written
        self.assertFalse(self.settings_file.contains('test_key'))
        self.assertEqual(len(self.settings_file), 0)

    def test_set_and_get_value(self):
        setting = Setting('test_key', int, 10)

        # Change default value
        setting.value = 20
        self.assertEqual(setting.value, 20)
        self.assertEqual(len(self.settings_file), 1)
        self.assertEqual(self.settings_file.get('test_key').value, '20')

        # Change value
        setting.value = 15
        self.assertEqual(setting.value, 15)
        self.assertEqual(len(self.settings_file), 1)
        self.assertEqual(self.settings_file.get('test_key').value, '15')

        # Delete value
        setting.value = None
        self.assertEqual(setting.value, 10) # Should return default
        self.assertEqual(len(self.settings_file), 0)

        # Set value to invalid type
        with self.assertRaises(TypeError):
            setting.value = "not an int"    # type: ignore

    def test_multiple_instances(self):
        setting1 = Setting('shared_key', int, 5)
        setting2 = Setting('shared_key', int, 5)
        
        setting1.value = 42
        self.assertEqual(setting2.value, 42)
        setting2.value = None
        self.assertEqual(setting1.value, 5)

        # Different default value
        setting1.value = 20
        setting3 = Setting('shared_key', int, 100)
        self.assertEqual(setting3.value, 20)
        setting1.value = None
        self.assertEqual(setting1.value, 5)
        self.assertEqual(setting3.value, 100)

    def test_file_persistence(self):
        setting = Setting('file_key', int, 123)
        setting.value = 456
        
        with open(self.config_path, 'r') as f:
            content = f.read()
            # SerializableFile writes compact JSON
            self.assertIn('"key":"file_key"', content)
            self.assertIn('"value":"456"', content)

if __name__ == '__main__':
    unittest.main()