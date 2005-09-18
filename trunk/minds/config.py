"""
Initalize cfg with configuration data.
"""
from minds import base_config 

if not base_config.cfg:
    base_config.cfg = base_config.Config()
    base_config.cfg.load(base_config.CONFIG_FILE)
    base_config.cfg.setupPaths()

# we maybe using test config if it is loaded first
cfg = base_config.cfg
