# -*- coding: utf-8 -*-
'''
Created on 15 Sep 2010

@author: Mac Ryan

@file: Various classes needed to render the graphic part of the dashboard when
operating the software on a PC [On a free-runner thiese classes are unused].
'''

from lib import graphics
from math import radians
from operator import mul
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
        # Direction indicators
        self.north_sprite = NeedleSprite(0, "#FF0000")
        self.add_child(self.north_sprite)
        self.mnorth_sprite = NeedleSprite(1, "#00FF00")
        self.add_child(self.mnorth_sprite)
        self.wind_sprite = NeedleSprite(2, "#0000FF")
        self.add_child(self.wind_sprite)
        # Vector indicators
        self.gravitybox_sprite = VectorBoxSprite(0, "#FF0000")
        self.add_child(self.gravitybox_sprite)
        self.gravityvector_sprite = VectorSprite(self.gravitybox_sprite)
        self.add_child(self.gravityvector_sprite)
        self.magnetbox_sprite = VectorBoxSprite(1, "#00FF00")
        self.add_child(self.magnetbox_sprite)        
        self.magnetvector_sprite = VectorSprite(self.magnetbox_sprite)
        self.add_child(self.magnetvector_sprite)
        self.connect("on-enter-frame", self.on_enter_frame)
        
    def change_boat(self, boat):
        '''
        Hot-swap the boat being rendered on screen. 
        '''
        self.boat = boat

    def on_enter_frame(self, scene, context):
        zoom_factor = self.height / 384.0 * 3
        g = graphics.Graphics(context)
        g.fill_area(0, 0, self.width, self.height, WATER)
        for s in self.all_sprites():
            s.scale_x = zoom_factor
            s.scale_y = zoom_factor
            s.x = self.width / 2 - s.anchor_x * zoom_factor
            s.y = self.height / 2 - s.anchor_y * zoom_factor
        self.rudder_sprite.rotation = radians(-0.45 * self.boat.rudder_position)
        self.north_sprite.rotation = radians(self.boat.north)
        self.mnorth_sprite.rotation = radians(self.boat.magnetic_north)
        self.wind_sprite.rotation = radians(self.boat.relative_wind)
        self.magnetvector_sprite.vector = self.boat.get_magnetic_vector()
        self.gravityvector_sprite.vector = self.boat.get_gravity_vector()
        self.rudder_sprite.my_color, self.sail_sprite.my_color = \
            (COMPUTER_CONTROLLED if self.boat.pilot_mode == COMPUTER else "#000000",) * 2
        self.sail_sprite.my_opacity = self.boat.sail_position / 100.0
        delta = time() - self.boat.last_log_message_time
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
        
        
class NeedleSprite(graphics.Sprite):

    def __init__(self, offset=0, color="#000000"):
        graphics.Sprite.__init__(self, 2, 10)
        self.connect("on-render", self.on_render)
        self.anchor_x = -50
        self.anchor_y = 45 - offset*25
        self.my_color = color
    
    def on_render(self, sprite):
        self.graphics.clear()
        self.graphics.rectangle(-1, -10, 2, 10, 0)
        self.graphics.circle(0, 0, 2)
        self.graphics.fill(self.my_color)


class VectorBoxSprite(graphics.Sprite):

    def __init__(self, offset=0, color="#000000"):
        graphics.Sprite.__init__(self, 20, 20)
        self.connect("on-render", self.on_render)
        self.anchor_x = -75
        self.anchor_y = 45 - offset*25
        self.my_color = color
    
    def on_render(self, sprite):
        self.graphics.clear()
        self.graphics.set_line_style(1)
        self.graphics.rectangle(-10, -10, 20, 20)
        self.graphics.stroke_preserve(self.my_color, 1)


class VectorSprite(graphics.Sprite):

    def __init__(self, box_sprite):
        x, y = box_sprite.x, box_sprite.y
        self.init_x = x
        self.init_y = y
        graphics.Sprite.__init__(self, x, y)
        self.connect("on-render", self.on_render)
        self.anchor_x = box_sprite.anchor_x
        self.anchor_y = box_sprite.anchor_y
        self.my_color = box_sprite.my_color
        self.vector   = (0, 0, 0)
        self.vector_scale = x / 2.0 / 1000 # half of width of box by signal max value
    
    def on_render(self, sprite):
        self.graphics.clear()
        self.vector = map(lambda x : mul(x, self.vector_scale), self.vector)
        # X and Y get swapped beacuse of the hardware orientation relative
        # to the boat length... X is changed in sign because of teh upper
        # left corner of the screen being (0, 0) [not lower left]
        self.graphics.circle(self.vector[1], - self.vector[0], 1)
        col = self.my_color if self.vector[2] >= 0 else "#000000"
        self.graphics.fill(col)

