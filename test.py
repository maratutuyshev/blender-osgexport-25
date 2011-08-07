#!/usr/bin/python

import os
import subprocess
import glob

for testcase in glob.glob('data/*.blend'):
     subprocess.call(["blender", "-b", testcase, "-P", "src/osgexport.py", "--", "test/" + os.path.basename(testcase) + ".osg"])

