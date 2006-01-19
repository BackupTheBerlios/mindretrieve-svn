"""
Load a test version of config and create the necessary directories.
Import this module as the first application module instead of minds.config.
"""

from minds.config import cfg as testcfg

# Note testcfg and cfg reference the same Config object
# In test code we use testcfg to emphasize
# Normal code reference cfg but it is load with test_config

testcfg.load_test_config()
testcfg.setupPaths()
