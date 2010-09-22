# -*- coding: utf-8 -*-
'''
Created on 15 Sep 2010

@author: Mac Ryan

Various classes needed to render the graphic part of the dashboard.
'''

from lib import graphics
from math import radians
from commons import *

class Scene(graphics.Scene):

    '''
    Provide the Scene (subclass of gtk.drawingArea) for the control panel.
    '''

    def __init__(self, boat):
        graphics.Scene.__init__(self, framerate=40)
        # The Boat Object
        self.boat = boat
        # The Boat Drawing
        boat_shape = [(0, 40), (0, 100), (60, 100), (60, 40), (30, 0)]
        self.boat_sprite = graphics.Polygon(boat_shape, line_width=1, stroke="#000")
        self.boat_sprite.anchor_x = 30
        self.boat_sprite.anchor_y = 60
        self.add_child(self.boat_sprite)
        # The Ping Beat Drawing
        self.pingbeat_sprite = PingBeatSprite()
        self.add_child(self.pingbeat_sprite)
        # The Rudder Drawing
        self.rudder_sprite = RudderSprite()
        self.add_child(self.rudder_sprite)
        # The Sail Drawing
        self.sail_sprite = SailSprite()
        self.add_child(self.sail_sprite)
        self.connect("on-enter-frame", self.on_enter_frame)

    def on_enter_frame(self, scene, context):
        g = graphics.Graphics(context)
        g.fill_area(0, 0, self.width, self.height, WATER)
        zoom_factor = self.height / 384.0 * 3
        for s in self.all_sprites():
            s.scale_x = zoom_factor
            s.scale_y = zoom_factor
            s.x = self.width / 2 - s.anchor_x * zoom_factor
            s.y = self.height / 2 - s.anchor_y * zoom_factor
        self.rudder_sprite.rotation = radians(-0.45 * self.boat.rudder_position)
        self.rudder_sprite.my_color, self.sail_sprite.my_color = \
            (COMPUTER_CONTROLLED if self.boat.pilot_mode == COMPUTER else "#000000",) * 2
        self.sail_sprite.my_opacity = self.boat.sail_position / 100.0
        delta = time() - self.boat.last_ping_time
        self.pingbeat_sprite.alpha = 0 if delta > 1 else 1 - delta % 1

    def redraw(self):
        graphics.Scene.redraw(self)
        return True     # Not to stop the GObject timeout call.


class PingBeatSprite(graphics.Sprite):
    
    def __init__(self):
        graphics.Sprite.__init__(self, 4, 4)
        self.connect("on-render", self.on_render)
        self.anchor_x = 30
        self.anchor_y = 55
        self.alpha = 1
    
    def on_render(self, sprite):
        self.graphics.clear()
        self.graphics.circle(2, 2, 2)
        self.alpha = self.alpha - 0.01 if self.alpha < 0 else self.alpha
        self.graphics.fill(COMPUTER_CONTROLLED, self.alpha)


class SailSprite(graphics.Sprite):
    
    def __init__(self):
        graphics.Sprite.__init__(self, 20, 20)
        self.connect("on-render", self.on_render)
        self.anchor_x = 10
        self.anchor_y = 20
    
    def on_render(self, sprite):
        self.graphics.clear()
        self.graphics.set_line_style(1)
        self.graphics.circle(10, 10, 10)
        self.graphics.stroke_preserve(self.my_color, 1)
        self.graphics.fill(self.my_color, self.my_opacity)


class RudderSprite(graphics.Sprite):
    
    def __init__(self):
        graphics.Sprite.__init__(self, 4, 30, pivot_x=2, pivot_y=8)
        self.connect("on-render", self.on_render)
        self.anchor_x = 2
        self.anchor_y = -30
    
    def on_render(self, sprite):
        self.graphics.clear()
        self.graphics.rectangle(0, 0, 4, 30, 2)
        self.graphics.fill(self.my_color)
