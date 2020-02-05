# -*- coding:utf-8 -*-


"""
Check 14.4:

https://usermanual.wiki/Document/MVNUserManual.1147412416.pdf


blender -b --python ~/github-work/dance-mocap/src/mvnx_to_csv.py -- -S ~/github-work/blender-mvnx-io/io_anim_mvnx/data/mvnx_schema_dance_dec19.xsd -x ~/github-work/dance-mocap/mvnx_files/ILF12_20191207_SEQ1_REC-001.mvnx -o /tmp/test.csv
"""


import sys
import argparse
import lxml
#
from io_anim_mvnx.mvnx import Mvnx


__author__ = "Andres FR"
__email__ = "aferro@em.uni-frankfurt.de"


###############################################################################
### HELPERS
###############################################################################

class ArgumentParserForBlender(argparse.ArgumentParser):
    """
    This class is identical to its superclass, except for the parse_args
    method (see docstring). It resolves the ambiguity generated when calling
    Blender from the CLI with a python script, and both Blender and the script
    have arguments. E.g., the following call will make Blender crash because
    it will try to process the script's -a and -b flags:
    >>> blender --python my_script.py -a 1 -b 2

    To bypass this issue this class uses the fact that Blender will ignore all
    arguments given after a double-dash ('--'). The approach is that all
    arguments before '--' go to Blender, arguments after go to the script.
    The following calls work fine:
    >>> blender --python my_script.py -- -a 1 -b 2
    >>> blender --python my_script.py --
    """

    def _get_argv_after_doubledash(self):
        """
        Given the sys.argv as a list of strings, this method returns the
        sublist right after the '--' element (if present, otherwise returns
        an empty list).
        """
        try:
            idx = sys.argv.index("--")
            return sys.argv[idx+1:] # the list after '--'
        except ValueError as e: # '--' not in the list:
            return []

    # overrides superclass
    def parse_args(self):
        """
        This method is expected to behave identically as in the superclass,
        except that the sys.argv list will be pre-processed using
        _get_argv_after_doubledash before. See the docstring of the class for
        usage examples and details.
        """
        return super().parse_args(args=self._get_argv_after_doubledash())


def split_list_in_equal_chunks(l, chunk_size):
    """
    """
    return [l[i:i + chunk_size] for i in range(0, len(l), chunk_size)]


def expand_frames(mvnx, fields):
    """
    This function should traverse the requested fields, expand them if they
    have to be expanded and return a list of same-length lists, where the
    first one contains the field names and the rest the fields.
    """
    f_meta, config_f, normal_f = mvnx.extract_frame_info()
    segment_names = [el.attrib["label"] for el in
                     mvnx.mvnx.subject.segments.iterchildren()]
    #
    expanded_names = ["a", "b", "c", "d"]  # TODO!
    #
    result = [expanded_names]
    for f in normal_f:
        # TODO!!!
        result.append([1, 2, 3, 4])
    return result

###############################################################################
### GLOBALS
###############################################################################

parser = ArgumentParserForBlender()
parser.add_argument("-x", "--mvnx", type=str, required=True,
                    help="MVNX motion capture file to be loaded")
parser.add_argument("-o", "--out_path", type=str, required=True,
                    help="Output path for the CSV file")
parser.add_argument("-S", "--mvnx_schema", type=str, default=None,
                    help="XML validation schema for the given MVNX (optional)")
parser.add_argument("-F", "--fields", type=str, nargs="+", default=None,
                    help="Field names to retrieve. Default takes all.")
args = parser.parse_args()

MVNX_PATH = args.mvnx
OUT_PATH = args.out_path
SCHEMA_PATH = args.mvnx_schema
FIELDS = args.fields

ALLOWED_FIELDS = {"orientation", "position", "velocity", "acceleration",
                  "angularVelocity", "angularAcceleration", "footContacts",
                  "jointAngle", "centerOfMass", "ms"}
# vectors of NUM_SEGMENTS*n where n is 4 or 3 respectively
SEGMENT_4D_FIELDS = {"orientation"}
SEGMENT_3D_FIELDS = {"position", "velocity",
                     "acceleration", "angularVelocity",
                     "angularAceleration"}
# check manual, 22.7.3, "JointAngle"s are in ZXY if not specified
JOINT_ANGLE_3D_LIST = ["L5S1", "L4L3", "L1T12", "C1Head",
                       "C7LeftShoulder", "LeftShoulder", "LeftShoulderXZY",
                       "LeftElbow", "LeftWrist", "Lefthip", "LeftKnee",
                       "LeftAnkle", "LeftBallFoot",
                       "C7RightShoulder", "RightShoulder", "RightShoulderXZY",
                       "RightElbow", "RightWrist", "Righthip", "RightKnee",
                       "RightAnkle", "RightBallFoot"]
# a 4D boolean vector
FOOT_CONTACTS = ["left_heel_on_ground", "left_toe_on_ground",
                 "right_heel_on_ground", "right_toe_on_ground"]

# ###########################################################################
# # MAIN ROUTINE
# ###########################################################################


with open(OUT_PATH, "w") as f:
    #
    if FIELDS is None:
        FIELDS = ALLOWED_FIELDS
    mvnx = Mvnx(MVNX_PATH, SCHEMA_PATH)
    #
    expanded_frames = expand_frames(mvnx, FIELDS)
    #
    for row in expanded_frames:
        row_str = ",".join([str(x) for x in row])
        f.write(row_str + "\n")



# {'mvnx_path': '/home/a9fb1e/Desktop/dance_mocap/ILF12_20191207_SEQ1_REC-001.mvnx', 'schema': <lxml.etree.XMLSchema object at 0x7f596c4e0f48>, 'mvnx': <Element {http://www.xsens.com/mvn/mvnx}mvnx at 0x7f596f2cc748>, 'str_fields': {'tc', 'type'}, 'int_fields': {'ms', 'jointCount', 'segmentCount', 'index', 'sensorCount', 'time'}, 'fvec_fields': {'angularAcceleration', 'sensorFreeAcceleration', 'acceleration', 'sensorMagneticField', 'position', 'jointAngle', 'velocity', 'orientation', 'angularVelocity', 'jointAngleXZY', 'jointAngleErgo', 'centerOfMass', 'sensorOrientation'}}



# mvnx.mvnx.subject.segments[0]
# mvnx.mvnx.subject.segments.segment.attrib
# [el.attrib["label"] for el in mvnx.mvnx.subject.segments.iterchildren()]

# len(normal_f[0]["orientation"])
# len(normal_f[0]["jointAngleXZY"])


# 23 segments
