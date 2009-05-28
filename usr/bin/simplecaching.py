#!/usr/bin/python
# -*- coding: utf-8 -*-

#	Copyright (C) 2009 Daniel Fett
# 	Source inspired by Jesper Vestergaard's MokoCaching
# 	This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#	Author: Daniel Fett simplecaching@fragcom.de
#


### For the html data download and login class
import time

### For the gui :-)
import gtk
import pango

### For loading gps values
import socket
#import gpsthreads
import re

### For loading the conf file
import ConfigParser
import os


import math

### For threading
#import threading
#import thread

from threading import Thread

class coordinate():
	def __init__(self, lat, lon):
		self.lat = lat
		self.lon = lon
		
	def from_dd(self, lat, lon):
		self.lat = lat
		self.lon = lon
		
	def from_ddmm(self, latdd, latmm, londd, lonmm):
		self.lat = latdd + (latmm/60)
		self.lon = londd + (lonmm/60)
		
	def from_dm_array(self, lat, lon):
		self.from_ddmm(lat[0]*10 + lat[1], 
			float(str(lat[2]) + str(lat[3]) + "." + str(lat[4]) + str(lat[5]) + str(lat[6])),
			lon[0] * 100 + lon[1] * 10 + lon[2],
			float(str(lon[3]) + str(lon[4]) + "." + str(lon[5]) + str(lon[6]) + str(lon[7])))
			
	def to_dm_array(self):
		[[lat_d, lat_m],[lon_d, lon_m]] = self.to_ddmm()
		
		p = re.compile('^(\d?)(\d)(\d) (\d)(\d)\.(\d)(\d)(\d)$')
		d_lat = p.search("%02d %06.3f" % (lat_d, lat_m))
		#print "%06.3f" % lat_m
		d_lon = p.search("%03d %06.3f" % (lon_d, lon_m))
		return [
			[d_lat.group(i) for i in range (2, 9)],
			[d_lon.group(i) for i in range (1, 9)]
			]
		
	def to_ddmm(self):
		return [ [int(math.floor(self.lat)), (self.lat - math.floor(self.lat)) * 60] ,
			[int(math.floor(self.lon)), (self.lon - math.floor(self.lon)) * 60] ]
	
	def bearing_to(self, target):
		lat1 = math.radians(self.lat)
		lat2 = math.radians(target.lat)
		lon1 = math.radians(self.lon)
		lon2 = math.radians(target.lon)
		
		dlon = math.radians(target.lon - self.lon);
		y = math.sin(dlon) * math.cos(lat2)
		x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1)*math.cos(lat2)*math.cos(dlon)
		bearing = math.degrees(math.atan2(y, x))
		
		return (360 + bearing) % 360
		
	def distance_to (self, target):
		R = 6371*1000;
		dlat = math.radians(target.lat-self.lat);
		dlon = math.radians(target.lon-self.lon); 
		a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(self.lat)) * math.cos(math.radians(target.lat)) * math.sin(dlon/2) * math.sin(dlon/2); 
		c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a)); 
		return R * c;
		
		
		
class updown():
	def __init__(self, table, position):
		self.value = int(0)
		self.label = gtk.Label("0")
		self.button_up = gtk.Button("+")
		self.button_down = gtk.Button("-")
		table.attach(self.button_up, position, position + 1, 0, 1)
		table.attach(self.label, position, position + 1, 1, 2)
		table.attach(self.button_down, position, position + 1, 2, 3)
		self.button_up.connect('clicked', self.value_up)
		self.button_down.connect('clicked', self.value_down)
		self.label.modify_font(pango.FontDescription("sans 12"))
		self.button_up.child.modify_font(pango.FontDescription("sans 12"))
		self.button_down.child.modify_font(pango.FontDescription("sans 12"))
	
	def value_up(self, target):
		self.value = int((self.value + 1) % 10)
		self.update()
	
	def value_down(self, target):
		self.value = int((self.value - 1) % 10)
		self.update()
		
	def set_value(self, value):
		self.value = int(value)
		self.update()
		
	def update(self):
		self.label.set_text(str(self.value))
		
		

class gui():
	def __init__(self):
		self.window = gtk.Window()
		self.window.connect ("destroy", self.destroy)
		self.drawing_area_configured = False
		self.status = "?"
		self.has_fix = False
		
		c1 = coordinate(49.35454, 6.23456)
		self.target_position = c1
		#c2 = self.input_target()
		#
		#print "Distance: " + str(c1.distance_to(c2))
		#print "Bearing: " + str(c1.bearing_to(c2))
		#return
		
		self.window.set_title('Simple Geocaching Tool for Linux')
		table = gtk.Table(6, 2, False)
		self.window.add(table)
		
		global labelLatLon
		labelLatLon = gtk.Label("Current: 49 45.2345 003 23 543")
		table.attach(labelLatLon, 0, 2 ,3 ,4)
		
		
		global labelTargetLatLon
		labelTargetLatLon = gtk.Label("-")
		table.attach(labelTargetLatLon, 0, 2 ,4 ,5)
		
		global imageDirection 
		global pixBuf
		
		global labelDist
		labelDist = gtk.Label("34 m")
		table.attach(labelDist, 0, 1, 0, 1)
		
		global labelBearing
		labelBearing = gtk.Label("-199")
		table.attach(labelBearing, 1, 2, 0, 1)
		
		global progressbar		
		progressbar = gtk.ProgressBar()
		table.attach(progressbar, 0, 2, 2, 3)
		
		global buttonChange 
		buttonChange = gtk.Button("Change")
		table.attach(buttonChange, 1, 2, 5, 6)
		buttonChange.connect('clicked', self.input_target)
		
		labelDist.modify_font(pango.FontDescription("sans 10"))
		labelBearing.modify_font(pango.FontDescription("sans 10"))
		buttonChange.child.modify_font(pango.FontDescription("sans 10"))
		
		global drawing_area
		drawing_area = gtk.DrawingArea()
		drawing_area.set_size_request(470, 400)
		drawing_area.show()
		drawing_area.connect("expose_event", self.expose_event)
		drawing_area.connect("configure_event", self.configure_event)
		drawing_area.set_events(gtk.gdk.EXPOSURE_MASK)
		table.attach(drawing_area, 0,2, 1, 2)
		drawable = drawing_area.window
		
		self.gps_position = coordinate(0, 0)
		self.gps_bearing = 0.4
		self.window.show_all()	
		self.read_config()
		self.update_display()
		self.update_target_display()
		self.gps_thread = gps_reader(self)
		#self.gps_thread.start()		
		#gtk.gdk.threads_enter()
		gtk.timeout_add(1000, self.read_gps)
		gtk.main()
		#gtk.gdk.threads_leave()
		
	def expose_event(self, widget, event):
		x , y, width, height = event.area
		widget.window.draw_drawable(widget.get_style().fg_gc[gtk.STATE_NORMAL],
			pixmap, x, y, x, y, width, height)
			
		return False

	def configure_event(self, widget, event):
		global pixmap
		global xgc
		x, y, width, height = widget.get_allocation()
		pixmap = gtk.gdk.Pixmap(widget.window, width, height)
		
		xgc = widget.window.new_gc()
		self.drawing_area_configured = True
		self.draw_arrow()
		
	def draw_arrow(self):
		if (not self.drawing_area_configured):
			return
		widget = drawing_area
			
		display_bearing = self.gps_position.bearing_to(self.target_position) - self.gps_bearing
		display_distance = self.gps_position.distance_to(self.target_position)
		disabled = not self.has_fix
	
		if (display_distance < 50):
			color = "red"
		elif (display_distance < 150):
			color = "orange"
		else:
			color = "green"
	
		x, y, width, height = widget.get_allocation()
		
		xgc.set_rgb_fg_color(gtk.gdk.color_parse(color))

		
		pixmap.draw_rectangle( widget.get_style().bg_gc[gtk.STATE_NORMAL],
			True, 0, 0, width, height)
			
		arrow_transformed = self.get_arrow_transformed(x, y, width, height, display_bearing)	
			
		
		xgc.line_style = gtk.gdk.LINE_SOLID
		xgc.line_width = 5
		pixmap.draw_polygon(xgc, True, arrow_transformed)
		xgc.set_rgb_fg_color(gtk.gdk.color_parse("black"))
		pixmap.draw_polygon(xgc, False, arrow_transformed)
		
		
		
		if (disabled):		
			xgc.line_width = 3
			#xgc.line_style = gtk.gdk.LINE_ON_OFF_DASH
			xgc.set_rgb_fg_color(gtk.gdk.color_parse("red"))
			pixmap.draw_line(xgc, x, y, width, height)
			xgc.set_rgb_fg_color(gtk.gdk.color_parse("red"))
			pixmap.draw_line(xgc, x, height, width, y)
			
		
		widget.window.draw_drawable(widget.get_style().fg_gc[gtk.STATE_NORMAL],
			pixmap, x, y, x, y, width, height)
		return True

	def get_arrow_transformed(self, x, y, width, height, angle):
		arrow = [(0, -1.5), (1, 1.5), (0,0.5), (-1, 1.5)]
		multiply = height / 4
		offset_x = width / 2 + x
		offset_y = height / 2 + y
		s = math.sin(math.radians(angle))
		c = math.cos(math.radians(angle))
		arrow_transformed = []
		for (x, y) in arrow:
			arrow_transformed.append((int(round(x * multiply * c + offset_x - y * multiply * s)),
				int(round(y * multiply * c + offset_y + x * multiply * s))))
		return arrow_transformed
		
	def read_config(self):
		config = ConfigParser.ConfigParser()
		config.read(os.path.expanduser('~/simplecaching.conf'))
		try:
			target_lat = config.get("saved","last_target_lat",0)
			target_lon = config.get("saved", "last_target_lon",0)
		except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
			target_lat = 49.34567
			target_lon = 6.2345
		
		self.target_position = coordinate(float(target_lat), float(target_lon))
		
	def write_config(self):
		config = ConfigParser.ConfigParser()
		config.add_section("saved")
		config.set("saved", "last_target_lat", "%8.5f" % self.target_position.lat)
		config.set("saved", "last_target_lon", "%9.5f" % self.target_position.lon)
		config.write(open(os.path.expanduser('~/simplecaching.conf'),'w'))
		
	def input_target(self, target):
		
		#  ++ ++ +++
		#  49*45,123
		#  -- -- ---
		print "input target 1"
		dialog = gtk.Dialog("Result", None, gtk.DIALOG_MODAL, (gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))
		
		dialog.vbox.pack_start(gtk.Label("Latitude:"))
		table = gtk.Table(3, 9, False)
		chooser_lat = []
		chooser_lat.append(updown(table, 0))
		chooser_lat.append(updown(table, 1))
		table.attach(gtk.Label(" "), 2, 3, 1, 2)
		chooser_lat.append(updown(table, 3))
		chooser_lat.append(updown(table, 4))
		table.attach(gtk.Label(","), 5, 6, 1, 2)
		chooser_lat.append(updown(table, 6))
		chooser_lat.append(updown(table, 7))
		chooser_lat.append(updown(table, 8))
		dialog.vbox.pack_start(table)
		
		
		dialog.vbox.pack_start(gtk.Label("\nLongitude:"))
		table = gtk.Table(3, 9, False)
		chooser_lon = []
		chooser_lon.append(updown(table, 0))
		chooser_lon.append(updown(table, 1))
		chooser_lon.append(updown(table, 2))
		table.attach(gtk.Label(" "), 3, 4, 1, 2)
		chooser_lon.append(updown(table, 4))
		chooser_lon.append(updown(table, 5))
		table.attach(gtk.Label(","), 6, 7, 1, 2)
		chooser_lon.append(updown(table, 7))
		chooser_lon.append(updown(table, 8))
		chooser_lon.append(updown(table, 9))
		dialog.vbox.pack_start(table)
		
		#print "input target 2"
		[coord_lat, coord_lon] = self.target_position.to_dm_array()
		i = 0
		for val in coord_lat:
			chooser_lat[i].set_value(val)
			i = i + 1
			
		i = 0
		for val in coord_lon:
			chooser_lon[i].set_value(val)
			i = i + 1
		
		dialog.show_all()
		answer = dialog.run()
		dialog.destroy()
			
		lat_values = [ud.value for ud in chooser_lat]
		lon_values = [ud.value for ud in chooser_lon]
		self.target_position.from_dm_array(lat_values, lon_values)
		self.update_target_display();
		self.write_config()
		
	def read_gps(self):
		gps_position = self.gps_thread.get_position()
		gps_track = self.gps_thread.get_track()
		if (gps_position != None and gps_track != None):
			self.on_good_fix(gps_position, gps_track)
		else:
			self.on_no_fix()
		return True
		
	def on_good_fix(self, gps_position, gps_bearing):
		self.gps_position = gps_position
		self.gps_bearing = gps_bearing
		self.update_display()
		self.has_fix  = True
		self.draw_arrow()
		
	def on_no_fix(self):
		labelBearing.set_text("No Fix")
		labelLatLon.set_text(self.gps_thread.status)
		self.has_fix = False
		self.draw_arrow()
		
	def update_display(self):
		labelBearing.set_text("%d°" % self.gps_bearing)
		display_dist = self.gps_position.distance_to(self.target_position)
		if (display_dist > 100):
			xgc.line_width = 5
			xgc.line_style = gtk.gdk.LINE_ON_OFF_DASH
			progressbar.hide()
		else:
			progressbar.set_fraction(display_dist/100)
			
		if (display_dist > 1000):
			labelDist.set_text("%3.1fkm" % (display_dist / 1000))
		else:
			labelDist.set_text("%dm" % display_dist)
		[lat, lon] = self.gps_position.to_ddmm()
		labelLatLon.set_text("Aktuell: %2d° %06.3f / %2d° %06.3f" % (lat[0], lat[1], lon[0], lon[1]))
		
	def update_target_display(self):
		[lat, lon] = self.target_position.to_ddmm()
		labelTargetLatLon.set_text("Ziel: %2d° %06.3f / %2d° %06.3f" % (lat[0], lat[1], lon[0], lon[1]))
		
	
	def destroy(self, target):
		self.gps_thread.stopped = True
		gtk.main_quit()



class gps_reader():
	def __init__(self, gui):
		#Thread.__init__(self)
		self.gui = gui
		self.status = "verbinde..."
		self.connect();
		self.stopped = False
		
	#def run(self):
		#while (self.stopped == False):
		#	gps_position = self.get_position()
		#	gps_track = self.get_track()
		#	if (gps_position != None and gps_track != None):
		#		self.on_good_fix(gps_position, gps_track)
		#	else:
		#		self.on_no_fix()
		#	time.sleep(1)
	
	def connect(self):
		try:
			global gpsd_connection
			gpsd_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			gpsd_connection.connect(("127.0.0.1", 2947))
			self.status = "verbunden"
		except:
			self.status = "Fehler beim Verbinden"
			print "Could not connect"
			
			
			
	def get_position(self):
		try:
			gpsd_connection.send("%s\r\n" % 'p')
			pos = gpsd_connection.recv(8192)
			p = re.compile('P=(.*?)\s*$')
			match = p.search(pos)
			text = match.group(1)
			if (text == '?'):	
				self.status = "Kein GPS-Signal"			
				return None
			[lat, lon] = [float(ll) for ll in text.split(' ')]
			return coordinate(lat, lon)
		except:
			print "Fehler beim Auslesen der Daten"
			return None
		
		
	def get_track(self):
		try:
			gpsd_connection.send("%s\r\n" % 't')
			pos = gpsd_connection.recv(8192)
			p = re.compile('T=(.*?)\s*$')
			match = p.search(pos)
			text = match.group(1)
			if (text == '?'):			
				return None
			return float(text)
		except:
			print "Fehler beim Auslesen der Daten"
			return None	
		
	#def on_good_fix(self, gps_position, gps_track):
	#	gtk.gdk.threads_enter()
	#	self.gui.on_good_fix(gps_position, gps_track)
	#	gtk.gdk.threads_leave()
		
	#def on_no_fix(self):
	#	gtk.gdk.threads_enter()
	#	self.gui.on_no_fix()
	#	gtk.gdk.threads_leave()
		
	

if __name__ == "__main__":
	gtk.gdk.threads_init()
	gui = gui()

