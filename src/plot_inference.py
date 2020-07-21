# -*- coding:utf-8 -*-


"""
EXTRACT FRAMES FROM VIDEOS

for i in videos/*; do j=`basename $i`; mkdir frames/$j; mkdir hhrnet_predictions/$j cvlc $i --video-filter=scene --vout=dummy  --scene-ratio=1 --scene-prefix=sample-image --scene-path=frames/$j --rate=2 vlc://quit; done


# RUN HHRNET INFERENCE

cd ~/github-work/POSE_ESTIMATION/realtime-pose-estimation

for i in /home/a9fb1e/Desktop/julia_dance_libraries/frames/*/; do j=`basename $i`; o=/home/a9fb1e/Desktop/julia_dance_libraries/hhrnet_predictions/$j; mkdir $o; python teacher_inference.py  -I `ls $i/*` -o $o  -m models/pose_higher_hrnet_w48_640.pth.tar; done


# MAKE OUT DIRECTORIES

for i in /home/a9fb1e/Desktop/julia_dance_libraries/frames/*/; do j=`basename $i`; o=/home/a9fb1e/Desktop/julia_dance_libraries/out_frames/$j; mkdir $o; done


# RUN THIS SCRIPT TO POPULATE OUT DIRECTORIES
for i in /home/a9fb1e/Desktop/julia_dance_libraries/frames/*/; do j=`basename $i`; python plot_inference.py -s $j -c 30 255 200 -t 0.005; done


# IMAGES TO MP4
cat *.png | ffmpeg -f image2pipe -framerate 20 -i - test.mp4
"""


import os
import argparse
#
import numpy as np
import torch
import cv2
#
from vis import add_joints


# #############################################################################
# # HELPERS
# #############################################################################


def extract_teacher_data(npz_path, out_hw=None):
    """
    :param out_hw: If given, outputs will be bilinearly interpolated to
      this shape
    """
    npz = np.load(npz_path)
    # npz["pred_heatmaps"], npz["heatmaps_refined"], npz["heatmaps_order"]
    t_hms = npz["heatmaps_refined"]
    t_ae = npz["embeddings"][0:1]
    # npz["heatmaps_refined"], npz["heatmaps_order"]
    t_hms = torch.FloatTensor(t_hms)
    t_ae = torch.FloatTensor(t_ae)
    #
    hm_h, hm_w = t_hms.shape[-2:]
    ae_h, ae_w = t_ae.shape[-2:]
    #
    if out_hw is not None:
        # Our HRNet maps can't just be rescaled to original, since the
        # NN seems to pad vertical and horizontal distances differently.
        # We need to resize conserving aspect ratio and then trim.
        # For that first find actual size and slack to be trimmed
        out_h, out_w = out_hw
        vert_ratio, horiz_ratio = out_h / hm_h, out_w / hm_w
        true_hm_ratio = max(vert_ratio, horiz_ratio)
        real_h = int(hm_h * true_hm_ratio)
        real_w = int(hm_w * true_hm_ratio)
        # resize conserving aspect ratio
        t_hms = torch.nn.functional.interpolate(
            t_hms.unsqueeze(0), (real_h, real_w), mode="bilinear",
            align_corners=True)[0]
        t_ae = torch.nn.functional.interpolate(
            t_ae.unsqueeze(0), (real_h, real_w), mode="bilinear",
            align_corners=True)[0]
        # trim out the slack if existing
        slack_h, slack_w = real_h - out_h, real_w - out_w
        if slack_h > 0:
            slack_top = slack_h // 2
            slack_bottom = slack_h - slack_top
            t_hms = t_hms[:, slack_top:-slack_bottom]
            t_ae = t_ae[:, slack_top:-slack_bottom]
        if slack_w > 0:
            slack_left = slack_w // 2
            slack_right = slack_w - slack_left
            t_hms = t_hms[:, :, slack_left:-slack_right]
            t_ae = t_ae[:, :, slack_left:-slack_right]
    #
    return t_hms, t_ae

def max_pick(hms, thresh=0.1):
    """
    """
    sh = hms[0].shape
    result = []
    for i, hm in enumerate(hms):
        max_y, max_x = np.unravel_index(hm.argmax(), sh)
        val = hm[max_y, max_x]
        if val >= thresh:
            # result[i] = max_yx  # , val.item()
            result.append((max_x, max_y, val))
        else:
            result.append((0, 0, 0))

    return result


def save_skeleton_img(img, keypoint_list, out_path,
                      rgb=(30, 255, 30)):
    """
    """
    add_joints(img, keypoint_list, rgb, dataset="COCO")
    cv2.imwrite(out_path, img)


# #############################################################################
# # MAIN ROUTINE
# #############################################################################

# globals
parser = argparse.ArgumentParser("Single-person greedy HigherHRNet Inference")
# parser.add_argument("-I", "--input_img_dir", required=True, type=str,
#                     help="Abs path for the dir holding input frames")
# parser.add_argument("-P", "--input_pred_dir", required=True, type=str,
#                     help="Abs path for the dir holding npz predictions")
# parser.add_argument("-O", "--out_dir", required=True, type=str,
#                     help="Path to output the frames with prediction on top")
parser.add_argument("-s", "--seq_name", required=True, type=str,
                    help="Name of the folder for processed sequence")
parser.add_argument("-t", "--threshold", default=0.005, type=float,
                    help="Keypoints with score less than this will be ignored")
parser.add_argument("-c", "--skeleton_color", default=[30, 255, 30], type=int,
                    nargs="+",
                    help="Color for keypoints and lines between them")
args = parser.parse_args()
#

# SEQ_NAME = "BV1.m2v"
# DETECTION_THRESH = 0.005
# SKELETON_COLOR = (30, 255, 30)
SEQ_NAME = args.seq_name
DETECTION_THRESH = args.threshold
SKELETON_COLOR = args.skeleton_color


IMG_DIR = os.path.join("frames_with_face", SEQ_NAME)
PRED_DIR = os.path.join("hhrnet_predictions_with_face", SEQ_NAME)
OUT_DIR = os.path.join("out_frames_with_face", SEQ_NAME)

img_names = sorted([i for i in os.listdir(IMG_DIR) if i.endswith(".png")])
pred_paths = [os.path.join(PRED_DIR, i + "_w48_predictions.npz")
              for i in img_names]

for i, p in zip(img_names, pred_paths):
    #
    img = cv2.imread(os.path.join(IMG_DIR, i), 0)
    img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
    #
    pred_hms, _ = extract_teacher_data(p, out_hw=img.shape[:2])
    kps = max_pick(pred_hms, DETECTION_THRESH)
    #
    out_path = os.path.join(OUT_DIR, i + "_kps.png")
    save_skeleton_img(img, np.array(kps), out_path,
                      rgb=SKELETON_COLOR)
    print("SAVED frame to", out_path)
