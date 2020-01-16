#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
https://lxml.de/validation.html
"""


from os.path import basename
import argparse
#
from lxml import etree, objectify
import lxml
#


__author__ = "Andres FR"
__email__ = "aferro@em.uni-frankfurt.de"


# #############################################################################
# ## GLOBALS
# #############################################################################

# #############################################################################
# ## HELPERS
# #############################################################################

def load_and_validate(xml_path, xsd_path, raise_if_error=False):
    """
    :param bool raise_if_error: if true, raise an exception if validation fails
    """
    x = etree.parse(xml_path, etree.ETCompatXMLParser())
    s = etree.XMLSchema(file=xsd_path)
    if raise_if_error:
        s.assertValid(x)
        is_valid = True
    else:
        is_valid = s.validate(x)  # True if passed, False otherwise
    # in case an exception wasn't thrown
    return is_valid

# #############################################################################
# ## MAIN ROUTINE
# #############################################################################

def main():
    """
    """
    # parse arguments from command line:
    parser = argparse.ArgumentParser(description="Synch and trim MVN")
    parser.add_argument("-x", "--xml_path",
                        help="Absolute path to the XML file to validate",
                        type=str, required=True)
    parser.add_argument("-s", "--xsd_path",
                        help="Abspath to the XML schema to validate against",
                        type=str, required=True)
    parser.add_argument("-I", "--raise_if_error",
                        help="If given and validation fails, raise exception.",
                        action="store_true")
    args = parser.parse_args()

    # main globals
    XML_PATH = args.xml_path
    XSD_PATH = args.xsd_path
    RAISE_IF_ERROR = args.raise_if_error

    is_valid = load_and_validate(XML_PATH, XSD_PATH, RAISE_IF_ERROR)

    msg = "[VALIDATION PASSED]:" if is_valid else "[VALIDATION FAILED]:"
    print(msg, basename(XML_PATH), basename(XSD_PATH))


if __name__ == "__main__":
    main()
