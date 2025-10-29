#!/usr/bin/env python3

"""
Layer order marking generator

@author Bence Csókás
"""

import sys
import os

import argparse
from dataclasses import dataclass, asdict
from enum import Enum
from itertools import product
from logging import info

sys.path.append(os.path.join(sys.path[0], "..", "..")) # load kicad_mod path
sys.path.append(os.path.join(sys.path[0], "..", "..", "src")) # load kilibs path

from KicadModTree import *  # NOQA
from scripts.tools.footprint_generator import FootprintGenerator
from scripts.tools.global_config_files.global_config import GlobalConfig
from kilibs.geom.shapes.geom_polygon import GeomPolygon

def getLayerNames(layer_nr: int) -> list:
	return ["F.Cu"] + \
	       ["In{d:d}.Cu".format(d=d) for d in (range(1, layer_nr - 1))] + \
	       ["B.Cu"]

# characters '1'-'9', 'A'-'Z'
alphanumerobet = [str(i) for i in range(1, 10)] + [chr(i) for i in range(ord('A'), ord('Z') + 1)]

class LayerNumbering(Enum):
	# simple ordinal i.e. 1, 2, 3, ...
	ORDINAL = 0
	# layer name, i.e. T, 1, 2, ..., B
	NAMED = 1
	# numbers 1-9, then uppercase letters A-W
	AL_NUM = 2

	def asHumanReadable(self) -> str:
		if self == LayerNumbering.ORDINAL:
			return "simple ordinals"
		elif self == LayerNumbering.NAMED:
			return "layer names"
		if self == LayerNumbering.AL_NUM:
			return "alphanumeric ordinals"
		else:
			raise IndexError()

	def asFootprintName(self) -> str:
		if self == LayerNumbering.ORDINAL:
			return ""
		elif self == LayerNumbering.NAMED:
			return "_Named"
		elif self == LayerNumbering.AL_NUM:
			return "_AlNum"
		else:
			raise IndexError()

	def getLayerLabels(self, layer_nr: int) -> list:
		if self == LayerNumbering.ORDINAL or self == LayerNumbering.AL_NUM:
			return alphanumerobet[:layer_nr]
		elif self == LayerNumbering.NAMED:
			return ['T'] + alphanumerobet[:layer_nr - 2] + ['B']
		else:
			raise IndexError()

	def isLayerSupported(self, layer_nr) -> bool:
		if self == LayerNumbering.ORDINAL:
			return layer_nr <= 9 # 1-9
		elif self == LayerNumbering.NAMED:
			return layer_nr <= 11 # T, 1-9, B
		if self == LayerNumbering.AL_NUM:
			return layer_nr > 9 and layer_nr <= 32 # A-W
		else:
			raise IndexError()

class MirrorType(Enum):
	# no mirroring, all text faces the Top layer
	NONE = 0
	# Bottom layer mirrored
	BOTTOM = 1
	# Lower half of layers mirrored
	LOWER_HALF = 2

	def asHumanReadable(self) -> str:
		if self == MirrorType.NONE:
			return "not mirrored"
		elif self == MirrorType.BOTTOM:
			return "bottom layer mirrored"
		elif self == MirrorType.LOWER_HALF:
			return "lower layers mirrored"
		else:
			raise IndexError()

	def asFootprintName(self) -> str:
		if self == MirrorType.NONE:
			return ""
		elif self == MirrorType.BOTTOM:
			return "_BottomMirrored"
		elif self == MirrorType.LOWER_HALF:
			return "_LowerMirrored"
		else:
			raise IndexError()

	def getMirrorings(self, layer_nr: int) -> list:
		if self == MirrorType.NONE:
			return [False] * layer_nr
		elif self == MirrorType.BOTTOM:
			return [False] * (layer_nr - 1) + [True]
		elif self == MirrorType.LOWER_HALF:
			return [False] * (layer_nr // 2) + [True] * (layer_nr // 2)
		else:
			raise IndexError()

# Filter function for invalid combinations
# @see LayerMarkerGenerator#getVariants()
def isSane(variant_spec):
	layer_nr, numbering, text_height, pitch, m = variant_spec

	# LOWER_HALF mirroring redundant on 2 layers (same as BOTTOM)
	if layer_nr == 2 and m == MirrorType.LOWER_HALF:
		return False

	if not numbering.isLayerSupported(layer_nr):
		return False

	return True

class LayerMarkerGenerator(FootprintGenerator):

	@dataclass
	class Variant():
		# @param layer_nr how many layers
		layer_nr: int
		# @param numbering the numbering scheme
		numbering: LayerNumbering
		# @param text_height font size
		text_height: float
		# @param pitch distance between numbers/footprint edge
		pitch: float
		# @param mirroring style of mirroring
		mirroring: MirrorType

		def __init__(self, **kwargs):
			self.layer_nr = kwargs["layer_nr"]
			self.numbering = kwargs["numbering"]
			self.text_height = kwargs["text_height"]
			self.pitch = kwargs["pitch"]
			self.mirroring = kwargs["mirroring"]

		def getBounds(self) -> dict:
			return {
				"w": self.pitch * (self.layer_nr + 1),
				"h": self.pitch * 2
			}

		def getFootprintName(self) -> str:
			s = "LayerMarker_{layer_nr:d}_{w:.3g}x{h:.3g}mm_" + \
			    "TextH{text_height:.3g}mm_P{pitch:.3g}mm{variant:s}"

			variant = self.numbering.asFootprintName() + \
			          self.mirroring.asFootprintName()

			return s.format(**asdict(self), **self.getBounds(),
			                variant=variant)

		def getDescription(self) -> str:
			s = "Layer marker, {layer_nr:d} layers, {human_numbering:s}, " + \
			    "text size {text_height:.3g}mm, pitch {pitch:.3g}mm, margin {pitch:.3g}mm"

			return s.format(**asdict(self), human_numbering=self.numbering.asHumanReadable())

		def getLayerLabels(self) -> list:
			return self.numbering.getLayerLabels(self.layer_nr)

		def getMirrorings(self) -> list:
			return self.mirroring.getMirrorings(self.layer_nr)

	@classmethod
	def getVariants(self):
		pitches = [1.27]
		layers = range(2, 33, 2)
		nrs = LayerNumbering.__members__.values()
		text_sizes = [1]
		mirroring = MirrorType.__members__.values()

		variants = filter(isSane, product(layers, nrs, text_sizes, pitches, mirroring))

		return list(
			self.Variant(layer_nr=layer_nr, numbering=numbering,
			             text_height=text_height, pitch=pitch, mirroring=m)
			for layer_nr, numbering, text_height, pitch, m in variants
		)

	def generateFootprints(self):
		for v in self.getVariants():
			self.generateFootprintVariant(v)

	def generateFootprintVariant(self, variant: Variant):
		# assemble footprint name
		fp_name = variant.getFootprintName()

		# information about what is generated
		info(f"Making {fp_name}...")

		# create the footprint
		kicad_mod = Footprint(fp_name, FootprintType.UNSPECIFIED)
		kicad_mod.excludeFromBOM = True
		kicad_mod.excludeFromPositionFiles = True
		kicad_mod.allow_missing_courtyard = True
		kicad_mod.not_in_schematic = True

		# set the FP description
		description = variant.getDescription()
		kicad_mod.setDescription(description)
		kicad_mod.setTags("layer order identification numbering")

		# indicator text
		layers = getLayerNames(variant.layer_nr)
		labels = variant.getLayerLabels()
		mirroring = variant.getMirrorings()
		cur_x = 0
		for layer, label, m in zip(layers, labels, mirroring):
			txt = Text(text=label, layer=layer, at=[cur_x, -variant.pitch],
			           size=[variant.text_height, variant.text_height],
			           thickness=0.2*variant.text_height, mirror=m)
			kicad_mod.append(txt)
			cur_x += variant.pitch

		# knockout zone
		deny_cu = Keepouts(tracks=Keepouts.DENY, vias=Keepouts.DENY,
		                   copperpour=Keepouts.DENY, pads=Keepouts.DENY)
		bbox = variant.getBounds()
		top_left = [-variant.pitch, -2*variant.pitch]
		top_rght = [top_left[0]+bbox["w"], top_left[1]]
		bottom_l = [top_left[0], top_left[1]+bbox["h"]]
		bottom_r = [top_rght[0], bottom_l[1]]
		pts = GeomPolygon(shape=[top_left, top_rght, bottom_r, bottom_l])
		zone = Zone(pts, Hatch(Hatch.EDGE, 0.5), keepouts=deny_cu, layers=["*.Cu"])
		kicad_mod.append(zone)

		# reference and value text
		ref = Property(name=Property.REFERENCE, text='REF**', layer='F.SilkS',
		         at=[0, variant.pitch], hide=True)
		kicad_mod.append(ref)
		ref = Property(name=Property.VALUE, text=fp_name, layer='F.Fab',
		         at=[0, 2*variant.pitch], hide=True)
		kicad_mod.append(ref)

		lib_name = "Symbol"
		self.write_footprint(kicad_mod, lib_name)

if __name__ == "__main__":

	parser = argparse.ArgumentParser(description='footprint generation settings.')
	args = FootprintGenerator.add_standard_arguments(parser)

	gen = LayerMarkerGenerator(output_dir=args.output_dir, global_config=args.global_config)
	gen.generateFootprints()
