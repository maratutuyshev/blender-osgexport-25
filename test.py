#!/usr/bin/python

import os
import subprocess
import glob
import sys


print("Delete old test files\n")
for oldtestfile in glob.glob('test/*'):
    os.unlink(oldtestfile)


if len(sys.argv) > 1:
    testcase = sys.argv[1]
    subprocess.call(["blender", "-b", testcase, "-P", "src/io_export_osg.py", "--", "test/" + os.path.basename(testcase) + ".osg"])
else:
    for testcase in glob.glob('data/*.blend'):
        subprocess.call(["blender", "-b", testcase, "-P", "src/io_export_osg.py", "--", "test/" + os.path.basename(testcase) + ".osg"])

