# aircraft.py
# -----------------------------------------------------------------
# Loads a basic Wavefront OBJ model:
#   - supports v (vertex), vt (texcoords), f (faces)
# Converts the OBJ into OpenGL VAO (VBO for positions + UVs)
# -----------------------------------------------------------------

from OpenGL.GL import *
import numpy as np


# ---------------------------------------------------------------
# OBJ LOADER (SIMPLE)
# ---------------------------------------------------------------

def load_obj_simple(path):
    """
    Minimal OBJ loader.
    Supports:
        v x y z
        vt u v
        f v/vt v/vt v/vt

    Returns:
        positions (flat GLfloat array)
        texcoords (flat GLfloat array)
        vertex_count (int)
    """

    verts = []
    texs = []
    faces = []

    with open(path, "r") as f:
        for ln in f:
            ln = ln.strip()

            # skip empty lines
            if not ln:
                continue

            if ln.startswith("v "):
                _, x, y, z = ln.split()
                verts.append([float(x), float(y), float(z)])

            elif ln.startswith("vt "):
                parts = ln.split()
                u, v = float(parts[1]), float(parts[2])
                texs.append([u, v])

            elif ln.startswith("f "):
                parts = ln.split()[1:]
                face = []

                for p in parts:
                    # format: v/vt
                    if "/" in p:
                        v_i, t_i = p.split("/")[:2]
                        v_i = int(v_i) - 1
                        t_i = int(t_i) - 1
                        face.append((v_i, t_i))
                    else:
                        # no TexCoord provided → use zero
                        v_i = int(p) - 1
                        face.append((v_i, None))

                faces.append(face)

    # --- Build flattened arrays suitable for GL draw ---
    flat_positions = []
    flat_texcoords = []

    for face in faces:
        # triangulate polygons
        if len(face) < 3:
            continue

        for i in range(1, len(face) - 1):
            tri = [face[0], face[i], face[i + 1]]

            for v_i, t_i in tri:
                # position
                flat_positions.extend(verts[v_i])

                # texcoords
                if t_i is not None and t_i < len(texs):
                    flat_texcoords.extend(texs[t_i])
                else:
                    flat_texcoords.extend([0.0, 0.0])

    # Convert to GL arrays
    pos_arr = (GLfloat * len(flat_positions))(*flat_positions)
    uv_arr = (GLfloat * len(flat_texcoords))(*flat_texcoords)

    vertex_count = len(flat_positions) // 3
    return pos_arr, uv_arr, vertex_count


# ---------------------------------------------------------------
# CREATE VAO/VBO FOR THE AIRPLANE MODEL
# ---------------------------------------------------------------

def create_vao(positions, texcoords, vertex_count):
    vao = glGenVertexArrays(1)
    vbos = glGenBuffers(2)

    glBindVertexArray(vao)

    # Positions → VBO 0
    glBindBuffer(GL_ARRAY_BUFFER, vbos[0])
    glBufferData(GL_ARRAY_BUFFER, positions, GL_STATIC_DRAW)
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)

    # Texcoords → VBO 1
    glBindBuffer(GL_ARRAY_BUFFER, vbos[1])
    glBufferData(GL_ARRAY_BUFFER, texcoords, GL_STATIC_DRAW)
    glEnableVertexAttribArray(1)
    glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 0, None)

    glBindBuffer(GL_ARRAY_BUFFER, 0)
    glBindVertexArray(0)

    return vao, vbos, vertex_count
