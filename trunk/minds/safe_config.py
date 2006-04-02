"""
Initalize cfg with test config data.
"""

from minds import base_config

if base_config.cfg:
    raise RuntimeError('Unable to load safe_config because config is already loaded')

base_config.cfg = base_config.Config()
cfg = base_config.cfg
cfg.load_test_config()
cfg.setupPaths()

# test application may save config to this test file
config_path = cfg.getpath('data') / base_config.CONFIG_FILE
assert 'test' in config_path
cfg.config_path = config_path
