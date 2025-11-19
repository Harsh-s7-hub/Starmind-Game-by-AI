# graphics3d.py
# --------------------------------------------------------------------
# Handles:
#   - Loading shader files (phong.vert + phong.frag)
#   - Creating OpenGL textures from pygame surfaces
#   - Perspective projection matrix
#   - View matrix (camera)
# --------------------------------------------------------------------

import os
import numpy as np
from math import radians, tan
from OpenGL.GL import *
from shader_utils import link_program


# -----------------------------------------------------------
# Load shaders from files
# -----------------------------------------------------------

def compile_shaders_from_files(shader_folder="shaders"):
    """Reads phong.vert and phong.frag from /shaders folder and compiles them."""
    vert_path = os.path.join(shader_folder, "phong.vert")
    frag_path = os.path.join(shader_folder, "phong.frag")

    with open(vert_path, "r") as f:
        vertex_src = f.read()

    with open(frag_path, "r") as f:
        fragment_src = f.read()

    program = link_program(vertex_src, fragment_src)
    return program


# -----------------------------------------------------------
# Perspective projection matrix (OpenGL uses column-major)
# -----------------------------------------------------------

def perspective(fov_deg, aspect, near, far):
    """Create a perspective projection matrix (column-major)."""
    f = 1.0 / tan(radians(fov_deg) / 2)
    m = np.zeros((4, 4), dtype=np.float32)

    m[0, 0] = f / aspect
    m[1, 1] = f
    m[2, 2] = (far + near) / (near - far)
    m[2, 3] = (2 * far * near) / (near - far)
    m[3, 2] = -1.0

    return m.T.flatten()   # Column-major for OpenGL


# -----------------------------------------------------------
# View matrix (lookAt)
# -----------------------------------------------------------

def look_at(eye, target, up=(0, 1, 0)):
    """Create a view matrix just like glm::lookAt."""
    eye = np.array(eye, dtype=np.float32)
    target = np.array(target, dtype=np.float32)
    up = np.array(up, dtype=np.float32)

    f = target - eye
    f = f / np.linalg.norm(f)

    u = up / np.linalg.norm(up)
    s = np.cross(f, u)
    s = s / np.linalg.norm(s)
    u = np.cross(s, f)

    m = np.identity(4, dtype=np.float32)
    m[0, :3] = s
    m[1, :3] = u
    m[2, :3] = -f

    t = np.identity(4, dtype=np.float32)
    t[:3, 3] = -eye

    view = m @ t
    return view.T.flatten()  # Column-major


# -----------------------------------------------------------
# Texture helper — convert pygame image to GL texture
# -----------------------------------------------------------

def create_texture_from_surface(surface):
    """
    Takes a pygame surface and turns it into a full OpenGL texture (with mipmaps).
    """
    data = surface.get_buffer().raw
    width, height = surface.get_size()

    tex = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex)
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1)

    glTexImage2D(
        GL_TEXTURE_2D, 0, GL_RGBA,
        width, height, 0,
        GL_RGBA, GL_UNSIGNED_BYTE, data
    )

    glGenerateMipmap(GL_TEXTURE_2D)

    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    glBindTexture(GL_TEXTURE_2D, 0)
    return tex
