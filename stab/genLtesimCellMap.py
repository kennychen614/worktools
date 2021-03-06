#!/app/vbuild/SLED11-x86_64/python/2.7.10/bin/python

"""
Author: ekaiqch
Date: 2016-11-23
"""

import re
import sys
import os
from argparse import ArgumentParser
from collections import OrderedDict
from Tkinter import *
import subprocess
import tkFont
import shutil

KV_PATTERN = re.compile(
    r':(?P<name>\w+)\s*=>\s*"?(?P<value>[-_0-9a-zA-Z.]+)"?')
GROUP_PATTERN = re.compile(r'{(.+?)}')
LTESIMCLI_PATTERN = re.compile(':rec=>')
UEPAIR_PATTERN = re.compile(
    r'(?P<cnt1>\d+)\.times.*(?P<cnt2>\d+)\.times.*create_user_pair\(\s*""\s*,\s*"(?P<mobility1>\w+)"\s*,\s*"(?P<csmodel1>\w+)"\s*,\s*"(?P<psmodel1>\w+)"\s*,\s*"(?P<uetype1>\w+)"\s*,\s*"(?P<area1>\w+)"\s*,\s*"(?P<mobility2>\w+)"\s*,\s*"(?P<csmodel2>\w+)"\s*,\s*"(?P<psmodel2>\w+)"\s*,\s*"(?P<uetype2>\w+)"\s*,\s*"(?P<area2>\w+)"\s*\)')



global cvs
global fnt
global southBoundMap, northBoundMap, westBoundMap, eastBoundMap
global width, height, c_width, c_height


def normalize_x(x):
    return x * c_width / width

def normalize_y(y):
    return y * c_height / height

def transform_coord(x, y):
    x_coord = normalize_x(x - westBoundMap)
    y_coord = c_height - normalize_y(y - southBoundMap)
    return x_coord, y_coord

def draw_area(south, north, west, east, name=""):
    w = normalize_x(east - west)
    h = normalize_y(north - south)
    coord = transform_coord(west, north)
    area = cvs.create_rectangle(0, 0, w, h, fill='red')
    cvs.move(area, *coord)    
    tx, ty = transform_coord((west+east)/2, (north+south)/2)
    cvs.create_text(tx, ty, text=name, font=fnt)

    
def draw_cell(x, y, name="", pci="", radius=5000):
    x0, y0 = transform_coord(x - radius, y + radius)
    x1, y1 = transform_coord(x + radius, y - radius)
    cvs.create_oval(x0, y0, x1, y1)


    if re.search(r'\d1', name):
        tx, ty = transform_coord(x - radius, y)
	cvs.create_text(tx+10, ty+5, text='{}({})'.format(name, pci), fill='magenta', font=fnt)
    if re.search(r'\d2', name):
        tx, ty = transform_coord(x + radius, y)
	cvs.create_text(tx + 5, ty-5, text='{}({})'.format(name, pci), fill='magenta', font=fnt)	

def save(is_to_quit):
    f = 'ltesim_cell_map.eps'
    cvs.postscript(file=f, colormode='color', pagewidth=c_width, pageheight=c_height)
    subprocess.Popen('ps2pdf -dEPSCrop -dAutoRotatePages=/None {}'.format(f), shell=True)
    #subprocess.Popen('pstoimg -density 150 {}'.format(f), shell=True)
    if is_to_quit:
        master.destroy()



if __name__ == '__main__':

	ap = ArgumentParser()
	ap.add_argument('-f', dest='ltesim_cmd_file', required=True)
	ap.add_argument('-w', dest='screen_width', default=1024)
	ap.add_argument('-q', dest='is_quit', action='store_true')
        
	args = ap.parse_args()
	
	ltesim_cli_cmd = None
	with open(args.ltesim_cmd_file) as f:
            ctx = f.read()
            ctx = re.sub('\n|\r| ', '', ctx)
            print ctx

	    if LTESIMCLI_PATTERN.search(ctx):
		ltesim_cli_cmd = ctx

	if not ltesim_cli_cmd:
		sys.exit('can not find valid ltesim cli configuration command')


	m = re.search(r':southBoundMap\s*=>\s*(?P<southBoundMap>\d+)', ltesim_cli_cmd)
	if (m):
		southBoundMap = int(m.group('southBoundMap'))
	m = re.search(r':westBoundMap\s*=>\s*(?P<westBoundMap>\d+)', ltesim_cli_cmd)
	if (m):
		westBoundMap = int(m.group('westBoundMap'))
	m = re.search(r':northBoundMap\s*=>\s*(?P<northBoundMap>\d+)', ltesim_cli_cmd)
	if (m):
		northBoundMap = int(m.group('northBoundMap'))
	m = re.search(r':eastBoundMap\s*=>\s*(?P<eastBoundMap>\d+)', ltesim_cli_cmd)
	if (m):
		eastBoundMap = int(m.group('eastBoundMap'))

	width = eastBoundMap - westBoundMap
	height = northBoundMap - southBoundMap
	c_width = int(args.screen_width)
	c_height = c_width * height / width
			
	master=Tk()
	cvs = Canvas(master, width=c_width, height=c_height, takefocus=True, bg='white')
	cvs.pack()
        
        # Use explict font object, because default font will be rotated after conversion
        fnt = tkFont.Font(family='Helvetica') 

	for g in GROUP_PATTERN.finditer(ltesim_cli_cmd):
		attr_list = []  # list of dict

		is_area = is_cell = False
		for p in KV_PATTERN.finditer(g.group(1)):
			attr_list.append(p.groupdict())
			if ('area' == p.group('name')):
				is_area = True
			if ('cell' == p.group('name')):
				is_cell = True

		if is_area and is_cell:
			raise RuntimeError('Incorrect ltesim_cli command parameters? Found both "area" and "cell" parameter in same group')

		# create 'cell' map
		if is_cell:    
			cellobj = OrderedDict()
			for attr in attr_list:
				if attr['name'] == 'cell':
					cellobj['name'] = attr['value']
				if attr['name'] == 'pci':
					cellobj['pci'] = attr['value']
				if attr['name'] == 'position_X':
					cellobj['x'] = int(attr['value'])
				if attr['name'] == 'position_Y':
					cellobj['y'] = int(attr['value'])
			
			print(cellobj.items())
			draw_cell(cellobj['x'], cellobj['y'], cellobj['name'], cellobj['pci'])
			
		# create 'area' map
		if is_area:
			areaobj = OrderedDict()
			for attr in attr_list:
				if attr['name'] == 'area':
					areaobj['name'] = attr['value']
				if attr['name'] == 'southBoundary':
					areaobj['south'] = int(attr['value'])
				if attr['name'] == 'northBoundary':
					areaobj['north'] = int(attr['value'])
				if attr['name'] == 'westBoundary':
					areaobj['west'] = int(attr['value'])
				if attr['name'] == 'eastBoundary':
					areaobj['east'] = int(attr['value'])
					
			print(areaobj.items())
			draw_area(areaobj['south'], areaobj['north'], areaobj['west'], areaobj['east'], areaobj['name'])


        master.after(5000, save, args.is_quit)
        master.mainloop()
        
