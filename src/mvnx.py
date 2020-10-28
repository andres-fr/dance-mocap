#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
This module contains functionality concerning the adaption of the
XSENS MVN-XML format into our Python setup.
The adaption tries to be as MVN-version-agnostc as possible. Still,
it is possible to validate the file against a given schema.

The official explanation can be found in section 14.4 of the
*XSENS MVN User Manual*:

  https://usermanual.wiki/Document/MVNUserManual.1147412416.pdf
"""


__author__ = "Andres FR"


from lxml import etree, objectify  # https://lxml.de/validation.html


# #############################################################################
# ## GLOBALS
# #############################################################################

KNOWN_STR_FIELDS = {"tc", "type"}
KNOWN_INT_FIELDS = {"segmentCount", "sensorCount", "jointCount",
                    "time", "index", "ms"}  # "audio_sample"
KNOWN_FLOAT_VEC_FIELDS = {"orientation", "position", "velocity",
                          "acceleration", "angularVelocity",
                          "angularAcceleration", "sensorFreeAcceleration",
                          "sensorMagneticField", "sensorOrientation",
                          "jointAngle", "jointAngleXZY", "jointAngleErgo",
                          "centerOfMass"}


# #############################################################################
# ## HELPERS
# #############################################################################
def make_timestamp(timezone="Europe/Berlin"):
    """
    Output example: day, month, year, hour, min, sec, milisecs:
    10_Feb_2018_20:10:16.151
    """
    ts = datetime.datetime.now(tz=pytz.timezone(timezone)).strftime(
        "%d_%b_%Y_%H:%M:%S.%f")[:-3]
    return "%s (%s)" % (ts, timezone)

def str_to_vec(x):
    """
    Converts a node with a text like '1.23, 2.34 ...' into a list
    like [1.23, 2.34, ...]
    """
    try:
        return [float(y) for y in x.text.split(" ")]
    except Exception as e:
        print("Could not convert to vector (skip conversion):", e)
        return x


def process_dict(d, str_fields, int_fields, fvec_fields):
    """
    :returns: a copy of the given dict where the values (expected strings)
      whose keys are in the specified fields are converted to the specified
      type. E.g. If ``int_fields`` contains the ``index`` string and the given
      dict contains the ``index`` key, the corresponding value will be
      converted via ``int()``.
    """
    result = {}
    for k, v in d.items():
        if k in str_fields:
            result[k] = str(v)
        elif k in int_fields:
            result[k] = int(v)
        elif k in fvec_fields:
            result[k] = str_to_vec(v)
        else:
            result[k] = v
    return result


# #############################################################################
# ## MVNX CLASS
# #############################################################################

class Mvnx:
    """
    This class imports and adapts an XML file (expected to be in MVNX format)
    to a Python-friendly representation. See this module's docstring for usage
    examples and more information.
    """
    def __init__(self, mvnx_path, mvnx_schema_path=None,
                 str_fields=KNOWN_STR_FIELDS, int_fields=KNOWN_INT_FIELDS,
                 float_vec_fields=KNOWN_FLOAT_VEC_FIELDS):
        """
        :param str mvnx_path: a valid path pointing to the XML file to load
        :param str mvnx_schema_path: (optional): if given, the given MVNX will
          be validated against this XML schema definition.
        :param collection fields: List of strings with field names that are
          converted to the specified type when calling ``extract_frame_info``.
        """
        self.mvnx_path = mvnx_path
        #
        mvnx = etree.parse(mvnx_path, etree.ETCompatXMLParser())
        # if a schema is given, load it and validate mvn
        if mvnx_schema_path is not None:
            self.schema = etree.XMLSchema(file=mvnx_schema_path)
            self.schema.assertValid(mvnx)
        #
        self.mvnx = objectify.fromstring(etree.tostring(mvnx))
        #
        self.str_fields = str_fields
        self.int_fields = int_fields
        self.fvec_fields = float_vec_fields

    def export(self, filepath, pretty_print=True, extra_comment=""):
        """
        Saves the current ``mvnx`` attribute to the given file path as XML and
        adds the ``self.mvnx.attrib["pythonComment"]`` attribute with
        a timestamp.
        """
        #
        with open(filepath, "w") as f:
            msg = "Exported from %s on %s. " % (
                self.__class__.__name__, make_timestamp()) + extra_comment
            self.mvnx.attrib["pythonComment"] = msg
            s = etree.tostring(self.mvnx,
                               pretty_print=pretty_print).decode("utf-8")
            f.write(s)
            print("[Mvnx] exported to", filepath)

    # EXTRACTORS: LIKE "GETTERS" BUT RETURN A MODIFIED COPY OF THE CONTENTS
    def extract_frame_info(self):
        """
        :returns: The tuple ``(frames_metadata, config_frames, normal_frames)``
        """
        f_meta, config_f, normal_f = self.extract_frames(self.mvnx,
                                                         self.str_fields,
                                                         self.int_fields,
                                                         self.fvec_fields)
        frames_metadata = f_meta
        config_frames = config_f
        normal_frames = normal_f
        #
        assert (frames_metadata["segmentCount"] ==
                len(self.extract_segments())), "Inconsistent segmentCount?"
        return frames_metadata, config_frames, normal_frames

    @staticmethod
    def extract_frames(mvnx, str_fields, int_fields, fvec_fields):
        """
        The bulk of the MVNX file is the ``mvnx->subject->frames`` section.
        This function parses it and returns its information in a
        python-friendly format, mainly via the ``process_dict`` function.

        :param mvnx: An XML tree, expected to be in MVNX format
        :param collection fields: Collection of strings with field names that
          are converted to the specified type (fvec is a vector of floats).

        :returns: a tuple ``(frames_metadata, config_frames, normal_frames)``
          where the metadata is a dict in the form ``{'segmentCount': 23,
          'sensorCount': 17, 'jointCount': 22}``, the config frames are the
          first 3 frame entries (expected to contain special config info)
          and the normal_frames are all frames starting from the 4th.
          Fields found in the given int and vec field lists will be converted
          and the rest will remain as XML nodes.
        """
        frames_metadata = process_dict(mvnx.subject.frames.attrib,
                                       str_fields, int_fields, fvec_fields)
        # first 3 frames are config. types: "identity", "tpose", "tpose-isb"
        all_frames = mvnx.subject.frames.getchildren()
        # rest of frames contain proper data. type: "normal"
        config_frames = [process_dict({**f.__dict__, **f.attrib},
                                      str_fields, int_fields, fvec_fields)
                         for f in all_frames[:3]]
        normal_frames = [process_dict({**f.__dict__, **f.attrib},
                                      str_fields, int_fields, fvec_fields)
                         for f in all_frames[3:]]
        return frames_metadata, config_frames, normal_frames

    def extract_segments(self):
        """
        :returns: A list of the segment names in ``self.mvnx.subject.segments``
          ordered by id (starting at 1 and incrementing +1).
        """
        segments = [ch.attrib["label"] if str(i) == ch.attrib["id"] else None
                    for i, ch in enumerate(
                            self.mvnx.subject.segments.iterchildren(), 1)]
        assert all([s is not None for s in segments]),\
            "Segments aren't ordered by id?"
        return segments

    def extract_joints(self):
        """
        :returns: A tuple (X, Y). The element X is a list of the joint names
          ordered as they appear in the MVNX file.
          The element Y is a list in the original MVNX ordering, in the form
          [((seg_ori, point_ori), (seg_dest, point_dest)), ...], where each
          element contains 4 strings summarizing the origin->destiny of a
          connection.
        """
        names, connectors = [], []
        for j in self.mvnx.subject.joints.iterchildren():
            names.append(j.attrib["label"])
            #
            seg_ori, point_ori = j.connector1.text.split("/")
            seg_dest, point_dest = j.connector2.text.split("/")
            connectors.append(((seg_ori, point_ori), (seg_dest, point_dest)))
        return names, connectors
