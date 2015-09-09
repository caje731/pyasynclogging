#!../bin/python
"""
Tests for the logging module.
"""
print 'This print statement is within module1'
print 'printing name', __name__

import sys
sys.path += ['..']
import module2, module3
from module2.logtest import testlog, testlog2
testlog()
testlog2()