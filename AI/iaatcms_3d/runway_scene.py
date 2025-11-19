# runway_scene.py
# ------------------------------------------------------------
# Creates the ground/runway surface for the 3D airport.
# This is a large textured quad rendered with triangles.
# ------------------------------------------------------------

from OpenGL.GL import *
import numpy as np
import ctypes


def create_ground_plane(size_x=200.0, size_y=200.0, repeat=10):
    """
    Creates a huge textured quad for the ground / runway.
    repeat: controls how many times the texture repeats.
    """

    # Vertex data layout:
    #  position (3 floats) | texcoords (2 floats)

    vertices = [
        # x,        y,   z,        u,        v
        -size_x,   0.0, -size_y,   0.0,        0.0,
         size_x,   0.0, -size_y,   repeat,     0.0,
         size_x,   0.0,  size_y,   repeat,     repeat,
        -size_x,   0.0,  size_y,   0.0,        repeat,
    ]

    indices = [
        0, 1, 2,
        0, 2, 3
    ]

    vertices = (GLfloat * len(vertices))(*vertices)
    indices = (GLuint * len(indices))(*indices)

    # Generate OpenGL objects
    vao = glGenVertexArrays(1)
    vbo = glGenBuffers(1)
    ebo = glGenBuffers(1)

    glBindVertexArray(vao)

    # Vertex buffer
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, vertices, GL_STATIC_DRAW)

    # Index buffer
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo)
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices, GL_STATIC_DRAW)

    # Position attribute (location = 0)
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(
        0, 3, GL_FLOAT, GL_FALSE,
        5 * 4, ctypes.c_void_p(0)
    )

    # Texcoord attribute (location = 1)
    glEnableVertexAttribArray(1)
    glVertexAttribPointer(
        1, 2, GL_FLOAT, GL_FALSE,
        5 * 4, ctypes.c_void_p(3 * 4)
    )

    glBindVertexArray(0)

    return vao, vbo, ebo, len(indices)
