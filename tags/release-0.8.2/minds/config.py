"""
Initalize cfg with configuration data.
"""
from minds import base_config

if not base_config.cfg:
    base_config.cfg = base_config.Config()
    base_config.cfg.load(base_config.CONFIG_FILE)

# BUG: testlogs & testdata pops up in abitrary places
# https://developer.berlios.de/bugs/?func=detailbug&bug_id=6701&group_id=2905
#
# Note: config is also loaded indirectly by
# minds.weblib.win32.context_menu. Although it looks like a standalone
# module, minds.weblib would loads config. Since the current directory
# is whereever the explorer is, loading config would likely fail. Doing
# setupPaths() would actually create test directories in unexpected
# places!
    #base_config.cfg.setupPaths()

# we maybe using test config if it is loaded first
cfg = base_config.cfg
