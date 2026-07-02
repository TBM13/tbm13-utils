import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

import pytest

import tbm13_utils.settings as settings
from tbm13_utils.encoding import SerializableFile
from tbm13_utils.settings import RawSetting, Setting


class TestSettings(unittest.TestCase):
    def setUp(self):
        # Create temp dir & SerializableFile
        self.test_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.test_dir, "test_config.json")
        self.settings_file: SerializableFile[str, RawSetting] = SerializableFile(
            self.config_path, "key", RawSetting
        )

        # Patch the _settings object in the settings module
        self.patcher = patch.object(settings, "_settings", self.settings_file)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.test_dir)

    def test_default_value(self):
        setting = Setting("test_key", int, 10)
        assert setting.value == 10

        # Since the setting has the default value, it shouldn't have been written
        assert not self.settings_file.contains("test_key")
        assert len(self.settings_file) == 0

    def test_set_and_get_value(self):
        setting = Setting("test_key", int, 10)

        # Change default value
        setting.value = 20
        assert setting.value == 20
        assert len(self.settings_file) == 1
        assert self.settings_file.get("test_key").value == "20"

        # Change value
        setting.value = 15
        assert setting.value == 15
        assert len(self.settings_file) == 1
        assert self.settings_file.get("test_key").value == "15"

        # Delete value
        setting.value = None
        assert setting.value == 10  # Should return default
        assert len(self.settings_file) == 0

        # Set value to invalid type
        with pytest.raises(TypeError):
            setting.value = "not an int"  # type: ignore

    def test_multiple_instances(self):
        setting1 = Setting("shared_key", int, 5)
        setting2 = Setting("shared_key", int, 5)

        setting1.value = 42
        assert setting2.value == 42
        setting2.value = None
        assert setting1.value == 5

        # Different default value
        setting1.value = 20
        setting3 = Setting("shared_key", int, 100)
        assert setting3.value == 20
        setting1.value = None
        assert setting1.value == 5
        assert setting3.value == 100

    def test_file_persistence(self):
        setting = Setting("file_key", int, 123)
        setting.value = 456

        with open(self.config_path) as f:
            content = f.read()
            # SerializableFile writes compact JSON
            assert '"key":"file_key"' in content
            assert '"value":"456"' in content
