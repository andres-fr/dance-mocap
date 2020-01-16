# -*- coding:utf-8 -*-


"""
Scene builder script for Blender. It performs the following tasks:
xxx

TODO:

* Hide arbitrary dots from render. Way: Give a list of keypoint names
that should have a dot, and generate only for those.

* dots should be on the root AND tail of every bone, but without
duplicates.
Ugly way: set bone lengths to zero, dot.parent=bone, add extra dots
Nicer way: create dots and grab the sequences from the Mvn object.
  but this is redundant with many in the armature, so make sure that
  the timing and positions are correct. A good way would be to actually
  copy the sequences

blender --python ~/Desktop/dance_mocap/render_dots.py -- -b 4 -q
"""


import argparse
import sys
from math import radians, degrees

from mathutils import Vector, Euler  # mathutils is a blender package
import bpy

from io_anim_mvnx.mvnx_import import load_mvnx_into_blender

C = bpy.context
D = bpy.data


__author__ = "Andres FR"
__email__ = "aferro@em.uni-frankfurt.de"

###############################################################################
### HELPERS
###############################################################################

def rot_euler_degrees(rot_x, rot_y, rot_z, order="XYZ"):
    """
    Returns an Euler rotation object with the given rotations (in degrees)
    and rotation order.
    """
    return Euler((radians(rot_x), radians(rot_y), radians(rot_z)), order)

###

def update_scene():
    """
    Sometimes changes don't show up due to lazy evaluation. This function
    triggers scene update and recalculation of all changes.
    """
    C.scene.update()

def save_blenderfile(filepath=D.filepath):
    """
    Saves blender file
    """
    O.wm.save_as_mainfile(filepath=filepath)

def open_blenderfile(filepath=D.filepath):
    """
    Saves blender file
    """
    O.wm.open_mainfile(filepath=filepath)

def set_render_resolution_percentage(p=100):
    """
    """
    D.scenes[0].render.resolution_percentage = p

def get_obj(obj_name):
    """
    Actions like undo or entering edit mode invalidate the object references.
    This function returns a reference that is always valid, assuming that the
    given obj_name is a key of bpy.data.objects.
    """
    return D.objects[obj_name]

def select_by_name(*names):
    """
    Given a variable number of names as strings, tries to select all existing
    objects in D.objects by their name.
    """
    for name in names:
        try:
            D.objects[name].select_set(True)
        except Exception as e:
            print(e)

def deselect_by_name(*names):
    """
    Given a variable number of names as strings, tries to select all existing
    objects in D.objects by their name.
    """
    for name in names:
        try:
            D.objects[name].select_set(False)
        except Exception as e:
            print(e)

def select_all(action="SELECT"):
    """
    Action can be SELECT, DESELECT, INVERT, TOGGLE
    """
    bpy.ops.object.select_all(action=action)

def delete_selected():
    bpy.ops.object.delete()

def set_mode(mode="OBJECT"):
    """
    """
    bpy.ops.object.mode_set(mode=mode)

def purge_unused_data(categories=[D.meshes, D.materials, D.textures, D.images,
                                  D.curves, D.lights, D.cameras, D.screens]):
    """
    Blender objects point to data. E.g., a lamp points to a given data lamp
    object. Removing the objects doesn't remove the data, which may lead to
    data blocks that aren't being used by anyone. Given an ORDERED collection
    of categories, this function removes all unused datablocks.
    See https://blender.stackexchange.com/a/102046
    """
    for cat in categories:
        for block in cat:
            if block.users == 0:
                cat.remove(block)

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

def set_shading_mode(mode="SOLID", screens=[]):
    """
    Performs an action analogous to clicking on the display/shade button of
    the 3D view. Mode is one of "RENDERED", "MATERIAL", "SOLID", "WIREFRAME".
    The change is applied to the given collection of bpy.data.screens.
    If none is given, the function is applied to bpy.context.screen (the
    active screen) only. E.g. set all screens to rendered mode:
      set_shading_mode("RENDERED", D.screens)
    """
    screens = screens if screens else [C.screen]
    for s in screens:
        for spc in s.areas:
            if spc.type == "VIEW_3D":
                spc.spaces[0].shading.type = mode
                break # we expect at most 1 VIEW_3D space


def maximize_layout_3d_area():
    """
    TODO: this function assumes Layout is the bpy.context.workspace.
    It does the following:
    1. If there is an area with the given name:
       1.1. Minimizes any other maximized window
       1.2. Maximizes the desired area
    """
    screen_name = "Layout"
    area_name = "VIEW_3D"
    screen = D.screens[screen_name]
    for a in screen.areas:
        if a.type == area_name:
            # If screen is already in some fullscreen mode, revert it
            if screen.show_fullscreen:
                bpy.ops.screen.back_to_previous()
            # Set area to fullscreen (dict admits "window","screen","area")
            bpy.ops.screen.screen_full_area({"screen": screen, "area": a})
            break

###############################################################################
### GLOBALS
###############################################################################

parser = ArgumentParserForBlender()
parser.add_argument("-x", "--mvnx", type=str, required=True,
                    help="MVNX motion capture file to be loaded")
parser.add_argument("-S", "--mvnx_schema", type=str, default=None,
                    help="XML validation schema for the given MVNX (optional)")
args = parser.parse_args()


MVNX_PATH = args.mvnx
SCHEMA_PATH = args.mvnx_schema
MVNX_POSITION = (-0.1, -0.07, 0)
MVNX_ROTATION = (0, 0, radians(-6.6))  # euler angle


BACKGROUND_COLOR = (0, 0, 0, 0)
DOT_COLOR = (100, 100, 100, 0)
DOT_DIAMETER = 0.08
ALL_KEYPOINTS = {"Pelvis", "L5", "L3", "T12", "T8", "Neck", "Head",
                       "RightShoulder", "RightUpperArm", "RightForeArm",
                       "RightHand",
                       "LeftShoulder", "LeftUpperArm", "LeftForeArm",
                       "LeftHand",
                       "RightUpperLeg", "RightLowerLeg", "RightFoot",
                       "RightToe",
                       "LeftUpperLeg", "LeftLowerLeg", "LeftFoot",
                       "LeftToe"}
KEYPOINT_SELECTION = {"Pelvis", "Neck", "Head",
                      "RightShoulder", "RightUpperArm", "RightForeArm",
                      "RightHand",
                      "LeftShoulder", "LeftUpperArm", "LeftForeArm",
                      "LeftHand",
                      "RightUpperLeg", "RightLowerLeg", #  "RightFoot",
                      "RightToe",
                      "LeftUpperLeg", "LeftLowerLeg", # "LeftFoot",
                      "LeftToe"}

BONE_TAILS_WITH_DOT = ALL_KEYPOINTS


INIT_SHADING_MODE = "RENDERED"
INIT_3D_MAXIMIZED = False
# renderer
EEVEE_RENDER_SAMPLES = 32
EEVEE_VIEWPORT_SAMPLES = 0  # 1
EEVEE_VIEWPORT_DENOISING = True
# sequencer
FRAME_START = 1000 # 2  # 1 is T-pose if imported with MakeWalk
FRAME_END = None  # If not None sequence will be at most this

# In Blender, x points away from the cam, y to the left and z up
# (right-hand rule). Locations are in meters, rotation in degrees.
# Positive rotation on an axis means counter-clockwise when
# the axis points to the cam. 0,0,0 rotation points straight
# to the bottom.

# SUN_NAME = "SunLight"
# SUN_LOC = Vector((0.0, 0.0, 10.0))
# SUN_ROT = rot_euler_degrees(0, 0, 0)
# SUN_STRENGTH = 1.0  # in units relative to a reference sun

CAM_NAME = "Cam"
CAM_LOC = Vector((8.16, 0, 1.6))  # cam is on the front-right
CAM_ROT = rot_euler_degrees(86.0, 0.0, 90.0)  # human-like view at the origin

CAM_LIGHT_NAME = "CamLight"
CAM_LIGHT_LOC = Vector((0.0, 1.0, 0.0))
CAM_LIGHT_WATTS = 40.0  # intensity of the bulb in watts
CAM_LIGHT_SHADOW = False

# FLOOR_NAME = "Floor"
# FLOOR_SIZE = 10  # in meters
# FLOOR_METALLIC = 0.0  # metalic aspect, ratio from 0 to 1
# FLOOR_SPECULAR = 0.0  # specular aspect, ratio from 0 to 1
# FLOOR_ROUGHNESS = 1.0  # the higher the more light difussion. From 0 to 1
# FLOOR_SUBSURFACE_RATIO = 0.5
# FLOOR_SUBSURFACE_COLOR = Vector((1.0, 1.0, 1.0, 1.0))  # RGBA (A=1 for opaque)
# floor_mat_name = FLOOR_NAME+"Material"
# FLOOR_IMG_ABSPATH = '/home/a9fb1e/github-work/human-renderer/blender_data/assets/marble_chess.jpg'

# MHX2_ABSPATH = "/home/a9fb1e/github-work/human-renderer/makehuman_data/exported_models/tpose_african.mhx2"
# MHX2_NAME = "TposeAfrican"


# BVH_ABSPATH = "/home/a9fb1e/github-work/human-renderer/makehuman_data/poses/cmu_motion_captures/01/01_06.bvh"




# ###########################################################################
# # MAIN ROUTINE
# ###########################################################################

# general settings
C.scene.world.node_tree.nodes["Background"].inputs['Color'].default_value = BACKGROUND_COLOR

# set denoising feature
C.scene.eevee.use_taa_reprojection = EEVEE_VIEWPORT_DENOISING
C.scene.eevee.taa_render_samples = EEVEE_RENDER_SAMPLES
C.scene.eevee.taa_samples = EEVEE_VIEWPORT_SAMPLES
# set all 3D screens to RENDERED mode
set_shading_mode(INIT_SHADING_MODE, D.screens)

# set fullscreen
if INIT_3D_MAXIMIZED:
    maximize_layout_3d_area()


# select and delete all objects
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete()
purge_unused_data()

# # add a sun
# bpy.ops.object.light_add(type="SUN", location=SUN_LOC, rotation=SUN_ROT)
# C.object.name = SUN_NAME
# C.object.data.name = SUN_NAME
# C.object.data.energy = SUN_STRENGTH

# add a cam
bpy.ops.object.camera_add(location=CAM_LOC, rotation=CAM_ROT)
C.object.name = CAM_NAME
C.object.data.name = CAM_NAME

# # add light as a child of cam
# bpy.ops.object.light_add(type="POINT", location=CAM_LIGHT_LOC)
# C.object.name = CAM_LIGHT_NAME
# C.object.data.name = CAM_LIGHT_NAME
# C.object.data.energy = CAM_LIGHT_WATTS
# C.object.parent = get_obj(CAM_NAME)
# C.object.data.use_shadow = False



try:
    armature, mvnx = load_mvnx_into_blender(C, MVNX_PATH, SCHEMA_PATH,
                                            connectivity="INDIVIDUAL",
                                            scale=1.0,
                                            frame_start=FRAME_START,
                                            inherit_rotations=False,
                                            add_identity_pose=False,
                                            add_t_pose=False,
                                            verbose=True)
except Exception as e:
    if isinstance(e, lxml.etree.DocumentInvalid):
        print("MNVX didn't pass given validation schema.",
              "Remove schema path to bypass validation.")
    else:
        print("Something went wrong:", e)

# readjust fps
C.scene.render.fps = 60
C.scene.render.frame_map_old = 400
C.scene.render.frame_map_new = 100
if FRAME_END is not None:
    assert FRAME_END > FRAME_START, "Frame end must be bigger than start!"
    fe = C.scene.frame_end
    new_fe = int(FRAME_END)
    if new_fe < fe:
        fe = new_fe

print(">>>>>>>>!!!", C.scene.frame_start, C.scene.frame_end)
# readjust armature position
armature.location = MVNX_POSITION
armature.rotation_euler = MVNX_ROTATION


# define glowing material for all spheres
sphere_material = bpy.data.materials.new(name="sphere_material")
sphere_material.use_nodes = True
bsdf_inputs = sphere_material.node_tree.nodes["Principled BSDF"].inputs
bsdf_inputs["Specular"].default_value = 0
bsdf_inputs["Emission"].default_value = DOT_COLOR


# # frames_metadata, config_frames, normal_frames = mvnx.extract_frame_info()
# fcurves = {pb.name: [] for pb in armature.pose.bones}
# spheres = {}
# for b in armature.data.bones:
#     bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3,
#                                           radius=DOT_DIAMETER / 2,
#                                           location=(0, 0, 0))
#     sph = C.object
#     spheres[b.name] = sph
#     sph.data.materials.append(sphere_material)

# print(">>>>>>", fcurves, spheres)


# TODO: iterate over armature bones. For each bone, create a sphere
# and assign bone as parent
for b in armature.data.bones:
    if b.name in BONE_TAILS_WITH_DOT:
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3,
                                              radius=DOT_DIAMETER / 2,
                                              location=(0, 0, 0))
        sph = C.object
        sph.data.materials.append(sphere_material)
        sph.parent = armature
        sph.parent_type = "BONE"
        sph.parent_bone = b.name

# # set lengths to zero
# bpy.ops.object.mode_set(mode="EDIT")
# for b in D.armatures[armature.name].edit_bones:
#     print(">>>>>>>>>>>", b.name)
#     b.head = b.tail


# >>> for b in D.armatures['ILF12_20191207_SEQ1_REC-001.mvnx'].edit_bones:
# ...     b.tail = b.head
# bpy.ops.screen.animation_play()
