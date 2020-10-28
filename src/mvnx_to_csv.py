# -*- coding:utf-8 -*-


"""
This script converts MVNX fullbody data into tabular forms, and
saves them as CSV to a desired path. Usage example::

  python mvnx_to_csv.py -x '/home/mvn1e/git_work/dance-mocap/mvnx_files/ILF12_20191207_SEQ1_REC-001.mvnx' -o /tmp  -F centerOfMass position velocity acceleration

Check the -h flag for help.

The code is very tightly related to the MVNX format. Please check section 14.4:
https://usermanual.wiki/Document/MVNUserManual.1147412416.pdf
"""

import os
import sys
from argparse import ArgumentParser
import lxml
import numpy as np
import pandas as pd
#
from mvnx import Mvnx


###############################################################################
### HELPERS
###############################################################################
def split_list_in_equal_chunks(l, chunk_size):
    """
    """
    return [l[i:i + chunk_size] for i in range(0, len(l), chunk_size)]


class MvnxToTabular:
    """
    """
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

    def __init__(self, mvnx):
        """
        """
        assert mvnx.mvnx.subject.attrib["configuration"] == "FullBody", \
            "This processor works only in FullBody MVNX configurations"
        # extract skeleton and frame info
        joints, seg_detail, seg_names_sorted = self._parse_skeleton(mvnx)
        frames_metadata, config_f, normal_f = mvnx.extract_frame_info()
        #
        self.mvnx = mvnx
        self.seg_names_sorted = seg_names_sorted
        self.seg_detail = seg_detail
        self.joints = joints
        self.n_seg = len(self.seg_names_sorted)
        self.n_j = len(self.joints)
        #
        self.frames_metadata = frames_metadata
        self.config_frames = config_f
        self.normal_frames = normal_f

    def _parse_skeleton(self, mvnx):
        """
        """
        # Retrieve every segment keypoint with XYZ positions
        segproc = lambda seg: np.fromstring(seg.pos_b.text, dtype=np.float32,
                                            sep=" ")
        seg_detail = {(s.attrib["label"], ch.attrib["label"]): segproc(ch)
                      for s in mvnx.mvnx.subject.segments.iterchildren()
                      for ch in s.points.iterchildren()}
        # Retrieve every joint as a relation of segment details
        joints = [(j.attrib["label"],
                   j.connector1,
                   seg_detail[tuple(j.connector1.text.split("/"))],
                   j.connector2,
                   seg_detail[tuple(j.connector2.text.split("/"))])
                  for j in mvnx.mvnx.subject.joints.iterchildren()]
        # Retrieve segment names sorted by ID
        seg_names_sorted = [s.attrib["label"] for s in
                            sorted(mvnx.mvnx.subject.segments.iterchildren(),
                                   key=lambda elt: int(elt.attrib["id"]))]
        return joints, seg_detail, seg_names_sorted

    def __call__(self, frame_fields):
        """
        """
        # sanity check
        if frame_fields is None:
            frame_fields = self.ALLOWED_FIELDS
        assert all([f in self.ALLOWED_FIELDS for f in frame_fields]), \
            f"Error! allowed fields: {self.ALLOWED_FIELDS}"
        #
        dataframes = {}
        # process 3d segment data
        for fld in self.SEGMENT_3D_FIELDS:
            columns_3d = ["frame_idx", "ms"] + ["_".join([c, dim])
                                                for c in self.seg_names_sorted
                                                for dim in ["x", "y", "z"]]
            if fld in frame_fields:
                print("processing", fld)
                df = pd.DataFrame(([frm["index"], frm["ms"]] + frm[fld]
                                   for frm in self.normal_frames),
                                  columns=columns_3d)
                dataframes[fld] = df
        # process 4d segment data
        for fld in self.SEGMENT_4D_FIELDS:
            columns_4d = ["frame_idx", "ms"] + [
                "_".join([c, dim]) for c in self.seg_names_sorted
                for dim in ["q0", "q1", "q2", "q3"]]
            if fld in frame_fields:
                print("processing", fld)
                df = pd.DataFrame(([frm["index"], frm["ms"]] + frm[fld]
                                   for frm in self.normal_frames),
                                  columns=columns_4d)
                dataframes[fld] = df
        # process foot contacts
        fld = "footContacts"
        if fld in frame_fields:
            print("processing", fld)
            columns_foot = ["frame_idx", "ms"] + self.FOOT_CONTACTS
            df = pd.DataFrame(([frm["index"], frm["ms"]] +
                               [bool(x) for x in frm[fld].text.split(" ")]
                               for frm in self.normal_frames),
                              columns=columns_foot)
            dataframes[fld] = df
        # process center of mass
        fld = "centerOfMass"
        if fld in frame_fields:
            print("processing", fld)
            columns_com = ["frame_idx", "ms",
                           "centerOfMass_x", "centerOfMass_y", "centerOfMass_z"]
            df = pd.DataFrame(([frm["index"], frm["ms"]] +
                               frm[fld]
                               for frm in self.normal_frames),
                              columns=columns_com)
            dataframes[fld] = df
        #
        return dataframes


# ###########################################################################
# # MAIN ROUTINE
# ###########################################################################
parser = ArgumentParser()
parser.add_argument("-x", "--mvnx", type=str, required=True,
                    help="MVNX motion capture file to be loaded")
parser.add_argument("-o", "--out_dir", type=str, required=True,
                    help="Output path for the CSV files")
parser.add_argument("-S", "--mvnx_schema", type=str, default=None,
                    help="XML validation schema for the given MVNX (optional)")
parser.add_argument("-F", "--fields", type=str, nargs="+", default=None,
                    help="Field names to retrieve. Default takes all.")
args = parser.parse_args()

MVNX_PATH = args.mvnx
OUT_DIR = args.out_dir
SCHEMA_PATH = args.mvnx_schema
FIELDS = args.fields

m = Mvnx(MVNX_PATH, SCHEMA_PATH)
processor = MvnxToTabular(m)
dataframes = processor(FIELDS)
for df_name, df in dataframes.items():
    outpath = os.path.join(OUT_DIR, df_name + ".csv")
    df.to_csv(outpath)
    print("saved dataframe to", outpath)
