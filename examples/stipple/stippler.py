#!/usr/bin/env python
"""
This is a Python script that stipples a bitmap.

Invoke it with a bitmap name and it will run interactively;
press any key to save the stipple locations to a file
(which can be loaded by stipple2flp.py)
"""

from math import cos, sin, ceil

import sys
import argparse
import json

import numpy as np
import scipy.ndimage

import pyglet
from OpenGL.GL import *

class Voronoi(pyglet.window.Window):
    """ This class implements the stippling strategy described in
        "Weighted Voronoi Stippling"
        Adrian Secord, NPAR 2002
    """
    config = pyglet.gl.Config(
            sample_buffers=1, samples=1, double_buffer=True,
            major_version=2, minor_version=1, depth_size=16)

    def __init__(self, img, stipples, cone_res=256):
        super(Voronoi, self).__init__(height=img.shape[0], width=img.shape[1],
                                      config=self.config, resizable=False)

        # Scatter stipples randomly in the OpenGL viewport
        # (they'll converge pretty quickly when left to their own devices)
        self.stipples = np.random.uniform(-1, 1, size=(stipples,2))

        self.img = img

        # Build the target color and depth textures and the FBO
        self.build_tex()
        self.fbo = glGenFramebuffers(1)

        # Meshgrid for fast sampling
        self.gy, self.gx = np.meshgrid(*[range(0, s) for s in self.img.shape],
                                       indexing='ij')

        self.build_vbo(cone_res)
        self.build_shaders()

        # Update the stipples at 60 FPS
        pyglet.clock.schedule_interval(lambda dt:
            self.update_stipples(self.render_to_tex()), 1/60.)


    def build_tex(self):
        """ Generate target textures that are the size of the target image
        """
        self.tex, self.depth = glGenTextures(2)
        for t in self.tex, self.depth:
            glBindTexture(GL_TEXTURE_2D, t)
            glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S,
                            GL_CLAMP)
            glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T,
                            GL_CLAMP)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)

        # Configure the image texture as RGB, 8-bit
        glBindTexture(GL_TEXTURE_2D, self.tex)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB,
                     self.img.shape[1], self.img.shape[0],
                     0, GL_RGB, GL_UNSIGNED_BYTE, None)

        # Configure the depth texture as a floating-point depth buffer
        glBindTexture(GL_TEXTURE_2D, self.depth)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_DEPTH_COMPONENT,
                     self.img.shape[1], self.img.shape[0],
                     0, GL_DEPTH_COMPONENT, GL_FLOAT, None)

    def build_vbo(self, cone_res):
        """ Generate the cone that's drawn for each sample point
        """
        fan = [[cos(a), sin(a), 1] for a in
               np.linspace(0, 2*np.pi, cone_res)]
        cone = np.vstack([[0, 0, -1]] + fan).astype(np.float32)
        self.cone_vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.cone_vbo)
        glBufferData(GL_ARRAY_BUFFER, cone.nbytes, cone, GL_STATIC_DRAW)
        self.cone_res = cone_res

    def render_to_tex(self):
        """ Renders the voronoi diagram to self.tex

            Returns an array that's the same size as self.img
            which contains cell occupancy indices (as numbers in
            the range 0 to number of stipples)
        """
        # Bind the framebuffer and set it for rendering
        glBindFramebuffer(GL_FRAMEBUFFER, self.fbo)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,
                               GL_TEXTURE_2D, self.tex, 0)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT,
                               GL_TEXTURE_2D, self.depth, 0)

        # Push into the stack and change the viewport window
        glPushAttrib(GL_VIEWPORT_BIT)
        glViewport(0, 0, self.img.shape[1], self.img.shape[0])

        # Render the voronoi cells into the framebuffer texture
        self.render_voronoi()

        # Get raw pixel values from the framebuffer
        raw = glReadPixels(0, 0, self.img.shape[1], self.img.shape[0],
                           GL_RGB, GL_UNSIGNED_BYTE)
        buf = np.fromstring(raw, np.uint8)

        # Switch back to screen framebuffer and pop viewport changes
        glPopAttrib()
        glBindFramebuffer(GL_FRAMEBUFFER, 0)

        # Convert from RGB to single-digit indices
        indices = buf[0::3] * 65536 + buf[1::3] * 256 + buf[2::3]

        # Pack into the shape of the image
        return indices.reshape(self.img.shape)

    def render_voronoi(self):
        """ Draws the current array of samples as cones
        """
        glClearColor(0, 0, 0, 0)
        glClearDepth(1)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glUseProgram(self.cone_program)

        color = glGetUniformLocation(self.cone_program, "color")
        offset = glGetUniformLocation(self.cone_program, "offset")
        pos = glGetAttribLocation(self.cone_program, "vertex_position")

        glEnableVertexAttribArray(pos)
        glBindBuffer(GL_ARRAY_BUFFER, self.cone_vbo)
        glVertexAttribPointer(pos, 3, GL_FLOAT, False, 12, ctypes.c_void_p(0))

        glEnable(GL_DEPTH_TEST)
        for i, s in enumerate(self.stipples):
            glUniform3f(offset, s[0], s[1], 0)
            glUniform3f(color, (i / 65536) / 255., ((i / 256) % 256) / 255., (i % 256) / 255.)
            glDrawArrays(GL_TRIANGLE_FAN, 0, self.cone_res + 1)

    def on_draw(self):
        self.render_voronoi()
        self.draw_stipples((1, 1, 1))

    def on_key_press(self, symbol, modifiers):
        self.close()

    def draw_stipples(self, color):
        """ Draws small circles at the location of each stipple
        """
        color_loc = glGetUniformLocation(self.cone_program, "color")
        offset = glGetUniformLocation(self.cone_program, "offset")

        pixels = (self.stipples + 1) / 2
        pixels[:,0] *= self.img.shape[1]
        pixels[:,1] *= self.img.shape[0]
        pixels = pixels.astype(np.int)

        glDisable(GL_DEPTH_TEST)
        for s, p in zip(self.stipples, pixels):
            weight = self.img[p[1], p[0]]
            glUniform3f(offset, s[0], s[1], 1.98 + 0.02 * weight)
            glUniform3f(color_loc, *color)
            glDrawArrays(GL_TRIANGLE_FAN, 0, self.cone_res + 1)

    def update_stipples(self, cells):
        """ Updates stipple locations from an image
                cells should be an image of the same size as self.img
                with pixel values representing which Voronoi cell that
                pixel falls into
        """
        indices = np.argsort(cells.flat)
        _, boundaries = np.unique(cells.flat[indices], return_index=True)

        gxs = np.split(self.gx.flat[indices], boundaries)[1:]
        gys = np.split(self.gy.flat[indices], boundaries)[1:]
        gws = np.split(1 - self.img.flat[indices], boundaries)[1:]

        w = self.img.shape[1] / 2.0
        h = self.img.shape[0] / 2.0

        for i, (gx, gy, gw) in enumerate(zip(gxs, gys, gws)):
            weight = np.sum(gw)
            if weight > 0:
                x = np.sum(gx * gw) / weight
                y = np.sum(gy * gw) / weight

                self.stipples[i,:] = [(x - w) / w, (y - h) / h]
            else:
                self.stipples[i,:] = np.random.uniform(-1, 1, size=2)


    def build_shaders(self):
        self.cone_program = glCreateProgram()
        vert = glCreateShader(GL_VERTEX_SHADER)
        frag = glCreateShader(GL_FRAGMENT_SHADER)

        glShaderSource(vert, """
        #version 120

        attribute vec3 vertex_position;
        uniform vec3 offset;

        void main()
        {
            gl_Position = vec4(vertex_position + offset, 1.0f);
        }
        """)

        glShaderSource(frag, """
        #version 120

        uniform vec3 color;

        void main()
        {
            gl_FragColor = vec4(color, 1.0f);
        }
        """)

        for s in [vert, frag]:
            glCompileShader(s)
            glAttachShader(self.cone_program, s)
        glLinkProgram(self.cone_program)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Stipple an image")
    parser.add_argument('-N', metavar='dots', type=int, default=500,
                        help='number of stipples')
    parser.add_argument('image', metavar='image', type=str,
                        help='source image file')
    parser.add_argument('output', metavar='output', type=str,
                        help='output file')
    args = parser.parse_args()

    img = scipy.ndimage.imread(args.image, mode='F')[::-1,:]
    img /= np.max(img)

    print("Press any key to save stipple positions")
    win = Voronoi(img, stipples=args.N)
    pyglet.app.run()

    stipples = (win.stipples + 1) / 2
    stipples[:,0] *= img.shape[1]
    stipples[:,1] *= img.shape[0]
    stipples = stipples.astype(int)

    # Add image weight to each sample
    stipples = np.hstack([stipples, img[stipples[:,1], stipples[:,0]].reshape(-1, 1)])

    json.dump({'width': img.shape[1],
               'height': img.shape[0],
               'stipples': stipples.tolist()}, open(args.output, 'wb'))
