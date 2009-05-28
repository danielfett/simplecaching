import gobject
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


class Coordinate():
	def __init__(self, lat, lon):
		self.lat = lat
		self.lon = lon
		
	def from_d(self, lat, lon):
		self.lat = lat
		self.lon = lon
		
	def from_dm(self, latdd, latmm, londd, lonmm):
		self.lat = latdd + (latmm/60)
		self.lon = londd + (lonmm/60)
		
	def from_dm_array(self, lat, lon):
		self.from_dm(lat[0]*10 + lat[1],
			float(str(lat[2]) + str(lat[3]) + "." + str(lat[4]) + str(lat[5]) + str(lat[6])),
			lon[0] * 100 + lon[1] * 10 + lon[2],
			float(str(lon[3]) + str(lon[4]) + "." + str(lon[5]) + str(lon[6]) + str(lon[7])))

	def from_d_array(self, lat, lon):
		self.lat = float("%d%d.%d%d%d%d%d" % tuple(lat))
		self.lon = float("%d%d%d.%d%d%d%d%d" % tuple(lon))
			
	def to_dm_array(self):
		[[lat_d, lat_m],[lon_d, lon_m]] = self.to_dm()
		
		p = re.compile('^(\d?)(\d)(\d) (\d)(\d)\.(\d)(\d)(\d)$')
		d_lat = p.search("%02d %06.3f" % (lat_d, lat_m))
		d_lon = p.search("%03d %06.3f" % (lon_d, lon_m))
		return [
			[d_lat.group(i) for i in range (2, 9)],
			[d_lon.group(i) for i in range (1, 9)]
			]

	def to_d_array(self):

		p = re.compile('^(\d?)(\d)(\d).(\d)(\d)(\d)(\d)(\d)$')
		d_lat = p.search("%08.5f" % self.lat)
		d_lon = p.search("%09.5f" % self.lon)
		return [
			[d_lat.group(i) for i in range (2, 7)],
			[d_lon.group(i) for i in range (1, 7)]
			]
		
	def to_dm(self):
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

	def get_lat(self, format):
		if format == Gui.FORMAT_D:
			return "%8.5f°" % self.lat
		elif format == Gui.FORMAT_DM:
			return "%2d° %06.3f" % (int(math.floor(self.lat)), (self.lat - math.floor(self.lat)) * 60)

	def get_lon(self, format):
		if format == Gui.FORMAT_D:
			return "%9.5f°" % self.lon
		elif format == Gui.FORMAT_DM:
			return "%3d° %06.3f" % (int(math.floor(self.lon)), (self.lon - math.floor(self.lon)) * 60)

	def distance_to (self, target):
		R = 6371*1000;
		dlat = math.radians(target.lat-self.lat);
		dlon = math.radians(target.lon-self.lon); 
		a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(self.lat)) * math.cos(math.radians(target.lat)) * math.sin(dlon/2) * math.sin(dlon/2); 
		c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a)); 
		return R * c;
		
		
		
class Updown():
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

class Updown_Rows():
	def __init__(self, format, coord):
		self.format = format
		if format == Gui.FORMAT_DM:
			[init_lat, init_lon] = coord.to_dm_array()
		elif format == Gui.FORMAT_D:
			[init_lat, init_lon] = coord.to_d_array()
		[self.table_lat, self.chooser_lat] = self.generate_table(False, init_lat)
		[self.table_lon, self.chooser_lon] = self.generate_table(True, init_lon)

	def get_value(self):
		coord = Coordinate(0,0)
		lat_values = [ud.value for ud in self.chooser_lat]
		lon_values = [ud.value for ud in self.chooser_lon]
		if self.format == Gui.FORMAT_DM:
			coord.from_dm_array(lat_values, lon_values)
		elif self.format == Gui.FORMAT_D:
			coord.from_d_array(lat_values, lon_values)
		return coord

	def generate_table(self, is_long, initial_value):
		interrupt = {}
		if self.format == Gui.FORMAT_DM and not is_long:
			num = 7
			interrupt[2] =  "°"
			interrupt[5] = ","
		elif self.format == Gui.FORMAT_DM and is_long:
			num = 8
			interrupt[3] = "°"
			interrupt[6] = ","
		elif self.format == Gui.FORMAT_D and not is_long:
			num = 6
			interrupt[2] = ","
		elif self.format == Gui.FORMAT_D and is_long:
			num = 7
			interrupt[3] = ","

		table = gtk.Table(3, 9, False)
		chooser = []
		cn = 0
		for i in range(num + len(interrupt)):
			if i in interrupt:
				table.attach(gtk.Label(interrupt[i]), i, i+1, 1, 2)
			else:
				ud = Updown(table, i)
				if cn < len(initial_value):
					ud.set_value(initial_value[cn])
				chooser.append(ud)
				cn = cn + 1

		return [table, chooser]

		

class Gui():
	FORMAT_D = 0
	FORMAT_DM = 1
    
	def __init__(self):
		# Setting up some variables
		self.drawing_area_configured = False
		self.status = "?"
		self.has_fix = False
		self.format = self.FORMAT_DM
		self.gps_position = Coordinate(0, 0)
		self.target_position = Coordinate(0, 0)
		self.gps_bearing = 0.0
		self.gps_altitude = 0.0
		self.gps_speed = 0.0
		self.gps_sats = 0

        # Initialize Window
		self.window = gtk.Window()
		self.window.connect ("destroy", self.destroy)
		self.window.set_title('Simple Geocaching Tool for Linux')

		table = gtk.Table(6, 3, False)
		self.window.add(table)
		
		global labelLatLon
		labelLatLon = gtk.Label("?")
		table.attach(labelLatLon, 0, 3 ,3 ,4)
		
		global labelTargetLatLon
		labelTargetLatLon = gtk.Label("-")
		table.attach(labelTargetLatLon, 0, 3 ,4 ,5)
		
		global progressbar
		progressbar = gtk.ProgressBar()
		table.attach(progressbar, 0, 3, 0, 1)

		global labelAltitude
		labelAltitude = gtk.Label("Höhe")
		table.attach(labelAltitude, 0, 1, 1, 2)

		global labelDist
		labelDist = gtk.Label("Dist")
		table.attach(labelDist, 1, 2, 1, 2)

		global labelBearing
		labelBearing = gtk.Label("Richtg")
		table.attach(labelBearing, 2, 3, 1, 2)
		
		global buttonChange 
		buttonChange = gtk.Button("ändern")
		table.attach(buttonChange, 2, 3, 5, 6)
		buttonChange.connect('clicked', self.input_target)

		global buttonSwitch
		buttonSwitch = gtk.Button("dm/d")
		table.attach(buttonSwitch, 1, 2, 5, 6)
		buttonSwitch.connect('clicked', self.switch_display)
		
		labelDist.modify_font(pango.FontDescription("sans 10"))
		labelBearing.modify_font(pango.FontDescription("sans 8"))
		labelAltitude.modify_font(pango.FontDescription("sans 8"))
		buttonChange.child.modify_font(pango.FontDescription("sans 10"))
		buttonSwitch.child.modify_font(pango.FontDescription("sans 10"))
		
		global drawing_area
		drawing_area = gtk.DrawingArea()
		drawing_area.set_size_request(470, 380)
		drawing_area.show()
		drawing_area.connect("expose_event", self.expose_event)
		drawing_area.connect("configure_event", self.configure_event)
		drawing_area.set_events(gtk.gdk.EXPOSURE_MASK)
		table.attach(drawing_area, 0,3, 2, 3)
		#drawable = drawing_area.window
		
		self.window.show_all()	
		self.read_config()
		self.update_display()
		self.update_target_display()
		self.gps_thread = Gps_reader(self)
		gobject.timeout_add(500, self.read_gps)
		gtk.main()
		
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
			xgc.set_rgb_fg_color(gtk.gdk.color_parse("red"))
			pixmap.draw_line(xgc, x, y, width, height)
			xgc.set_rgb_fg_color(gtk.gdk.color_parse("red"))
			pixmap.draw_line(xgc, x, height, width, y)
			
		
		widget.window.draw_drawable(widget.get_style().fg_gc[gtk.STATE_NORMAL],
			pixmap, 0, 0, 0, 0, width, height)
		return True

	def get_arrow_transformed(self, x, y, width, height, angle):
		u = 1.0/3.0 # Offset to center of arrow, calculated as 2-x = sqrt(1^2+(x+1)^2)
		arrow = [(0, -2+u), (1, +1+u), (0,0+u), (-1, 1+u)]
		multiply = height / (2*(2-u))
		offset_x = width / 2 
		offset_y = height / 2 
		s = math.sin(math.radians(angle))
		c = math.cos(math.radians(angle))
		arrow_transformed = []
		for (x, y) in arrow:
			arrow_transformed.append((int(round(x * multiply * c + offset_x - y * multiply * s)),
				int(round(y * multiply * c + offset_y + x * multiply * s))))
		return arrow_transformed
		
	def read_config(self):
		config = ConfigParser.ConfigParser()
		config.read(os.path.expanduser('~/.simplecaching.conf'))
		try:
			target_lat = config.get("saved","last_target_lat",0)
			target_lon = config.get("saved", "last_target_lon",0)
		except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
			target_lat = 49.34567
			target_lon = 6.2345
		
		self.target_position = Coordinate(float(target_lat), float(target_lon))
		
	def write_config(self):
		config = ConfigParser.ConfigParser()
		config.add_section("saved")
		config.set("saved", "last_target_lat", "%8.5f" % self.target_position.lat)
		config.set("saved", "last_target_lon", "%9.5f" % self.target_position.lon)
		config.write(open(os.path.expanduser('~/.simplecaching.conf'),'w'))
		
	def input_target(self, target):
		udr = Updown_Rows(self.format, self.target_position)

		dialog = gtk.Dialog("Result", None, gtk.DIALOG_MODAL, (gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))
		dialog.vbox.pack_start(gtk.Label("Latitude:"))
		dialog.vbox.pack_start(udr.table_lat)
		dialog.vbox.pack_start(gtk.Label("\nLongitude:"))
		dialog.vbox.pack_start(udr.table_lon)
		dialog.show_all()
		dialog.run()
		dialog.destroy()
		self.target_position = udr.get_value()
		self.update_target_display();
		self.write_config()

	def switch_display(self, target):
		if self.format == self.FORMAT_D:
			self.format = self.FORMAT_DM
		elif self.format == self.FORMAT_DM:
			self.format = self.FORMAT_D

		self.update_display()
		self.update_target_display()

	def read_gps(self):
		#gps_position = self.gps_thread.get_position()
		#gps_track = self.gps_thread.get_track()
		gps_data = self.gps_thread.get_data()
		if (gps_data['position'] != None):
			self.gps_position = gps_data['position']
			self.gps_bearing = gps_data['bearing']
			self.gps_altitude = gps_data['altitude']
			self.gps_speed = gps_data['speed']
			self.gps_sats = gps_data['sats']
			self.on_good_fix()
		else:
			self.gps_sats = gps_data['sats']
			self.on_no_fix()
		return True
		
	def on_good_fix(self):
		self.update_display()
		self.has_fix  = True
		self.draw_arrow()
		self.update_progressbar()
		
	def on_no_fix(self):
		labelBearing.set_text("No Fix")
		labelLatLon.set_text(self.gps_thread.status)
		self.has_fix = False
		self.draw_arrow()
		self.update_progressbar()
		
	def update_display(self):
		labelBearing.set_text("%d°" % self.gps_bearing)
		display_dist = self.gps_position.distance_to(self.target_position)
			
		if (display_dist > 1000):
			labelDist.set_text("%3dkm" % (display_dist / 1000))
		else:
			labelDist.set_text("%3dm" % display_dist)

		labelAltitude.set_text("%3dm" % self.gps_altitude)
		labelLatLon.set_text("Aktuell: %s / %s" % (self.gps_position.get_lat(self.format), self.gps_position.get_lon(self.format)))

	def update_progressbar(self):
		progressbar.set_fraction(float(self.gps_sats)/12.0)
		progressbar.set_text("Satelliten: %d/12" % self.gps_sats)
		
	def update_target_display(self):
		labelTargetLatLon.set_text("Ziel: %s / %s" % (self.target_position.get_lat(self.format), self.target_position.get_lon(self.format)))
		
	
	def destroy(self, target):
		self.gps_thread.stopped = True
		gtk.main_quit()



class Gps_reader():
	def __init__(self, gui):
		#Thread.__init__(self)
		self.gui = gui
		self.status = "verbinde..."
		self.connect();
		self.stopped = False
		
	
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
			return Coordinate(lat, lon)
		except:
			#print "Fehler beim Auslesen der Daten"
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
			#print "Fehler beim Auslesen der Daten"
			return None	

	def get_data(self):
		try:
			gpsd_connection.send("%s\r\n" % 'o')
			data = gpsd_connection.recv(8192)
			gpsd_connection.send("%s\r\n" % 'q')
			quality_data = gpsd_connection.recv(8192)
			try:
				match = re.compile('Q=([^ ]+)\s').search(quality_data)
				sats = match.group(1)
				if sats == '?':
					sats = 0
			except:
				# Number of satellites could not be determined
				sats = 0
				
			if data.strip() == "GPSD,O=?":
				self.status = "Kein GPS-Signal"
				return {
					'position': None,
					'altitude': None,
					'bearing': None,
					'speed': None,
					'sats': int(sats)
				}
			
			# example output:
			# GPSD,O=- 1243530779.000 ? 49.736876 6.686998 271.49 1.20 1.61 49.8566 0.050 -0.175 ? ? ? 3
			# or
			# GPSD,O=?
			try:
				[tag, timestamp, time_error, lat, lon, alt, err_hor, err_vert, track, speed, delta_alt, err_track, err_speed, err_delta_alt, mode] = data.split(' ')
			except:
				print "GPSD Output: \n%s\n  -- cannot be parsed." % data
				self.status = "GPSD-Ausgabe konnte nicht gelesen werden."
				
			return {
				'position': Coordinate(float(lat), float(lon)),
				'altitude': float(alt),
				'bearing': float(track),
				'speed': float(speed),
				'sats': int(sats)
			}
		except:
			#print "Fehler beim Auslesen der Daten."
			return {
				'position': None,
				'altitude': None,
				'bearing': None,
				'speed': None,
				'sats': 0
			}

		
	

if __name__ == "__main__":
	gtk.gdk.threads_init()
	gui = Gui()

