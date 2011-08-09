#!/usr/bin/python

import os
import subprocess
import glob

for oldtestfile in glob.glob('test/*'):
    os.unlink(oldtestfile)

for testcase in glob.glob('data/*.blend'):
    subprocess.call(["blender", "-b", testcase, "-P", "src/osgexport.py", "--", "test/" + os.path.basename(testcase) + ".osg"])

