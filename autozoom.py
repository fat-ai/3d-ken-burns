#!/usr/bin/env python

import base64
import cupy
import cv2
import flask
import getopt
import gevent
import gevent.pywsgi
import glob
import h5py
import io
import math
import moviepy
import moviepy.editor
import numpy
import os
import random
import re
import scipy
import scipy.io
import shutil
import sys
import tempfile
import time
import torch
import torchvision
import urllib
import zipfile

##########################################################

torch.set_grad_enabled(False) # make sure to not compute gradients for computational performance

torch.backends.cudnn.enabled = True # make sure to use cudnn for computational performance

##########################################################

objCommon = {}

exec(open('./common.py', 'r').read())

exec(open('./models/disparity-estimation.py', 'r').read())
exec(open('./models/disparity-adjustment.py', 'r').read())
exec(open('./models/disparity-refinement.py', 'r').read())
exec(open('./models/pointcloud-inpainting.py', 'r').read())

##########################################################

args_strIn = './images/doublestrike.jpg'
args_strOut = './autozoom.mp4'
args_strDepth = None

for strOption, strArg in getopt.getopt(sys.argv[1:], '', [
	'in=',
	'out=',
	'depth=',
])[0]:
	if strOption == '--in' and strArg != '': args_strIn = strArg # path to the input image
	if strOption == '--out' and strArg != '': args_strOut = strArg # path to where the output should be stored
	if strOption == '--depth' and strArg != '': args_strDepth = strArg # optional path to a depth map in numpy format
# end

##########################################################

if __name__ == '__main__':
	# we don't want to resize the original image as we want to work with the whole thing
	npyImage = cv2.imread(filename=args_strIn, flags=cv2.IMREAD_COLOR)

	#intWidth = npyImage.shape[1]
	#intHeight = npyImage.shape[0]

	#fltRatio = float(intWidth) / float(intHeight)

	#intWidth = min(int(1024 * fltRatio), 1024)
	#intHeight = min(int(1024 / fltRatio), 1024)
	
        #Edit this npy image to remove size restrictions , need to check for any downstream issues with this?
	#npyImage = cv2.resize(src=npyImage, dsize=(intWidth, intHeight), fx=0.0, fy=0.0, interpolation=cv2.INTER_AREA)

	process_load(npyImage, {} if args_strDepth is None else {'npyDepth': numpy.load(args_strDepth)})

	objFrom = {
		'fltCenterU':  npyImage.shape[1] - (640+1280), #the x coordinate of the centre of the camera at start, set to npyImage.shape[1] - (1280/2), was intWidth / 2.0,
		'fltCenterV': npyImage.shape[0] / 2, #the y coordinate of the centre of the camera at start, set to  npyImage.shape[0] / 2, was intHeight / 2.0
		'intCropWidth': 1280*0.97, #the width of the image (inc small crop), set to 1280, was int(math.floor(0.97 * intWidth)),
		'intCropHeight': 720*0.97  #the height of the image (inc small crop), set to 720 was int(math.floor(0.97 * intHeight))
	}

	objTo = process_autozoom({
		'fltShift': -1000.0, # total amount of movement , was 100
		'fltZoom': 1.0, # total amount of zoom
		'objFrom': objFrom
	})

	npyResult = process_kenburns({
		'fltSteps': numpy.linspace(0.0, 120.0, 600).tolist(), # movement sideways, backward, number of frames
		'objFrom': objFrom,
		'objTo': objTo,
		'boolInpaint': True
	})

	moviepy.editor.ImageSequenceClip(sequence=[ npyFrame[:, :, ::-1] for npyFrame in npyResult + list(reversed(npyResult))[1:-1] ], fps=40).write_videofile(args_strOut)
# end
