# shader_utils.py
# --------------------------------------------------------------
# Helper functions for compiling + linking GLSL shaders in OpenGL
# --------------------------------------------------------------

from OpenGL.GL import *
import ctypes

def compile_shader(source, shader_type):
    """Compile a single GLSL shader (vertex or fragment)."""
    shader = glCreateShader(shader_type)
    glShaderSource(shader, source)
    glCompileShader(shader)

    # Check compile status
    status = glGetShaderiv(shader, GL_COMPILE_STATUS)
    if not status:
        error_log = glGetShaderInfoLog(shader).decode()
        raise RuntimeError(f"Shader compilation error:\n{error_log}")
    return shader


def link_program(vertex_source, fragment_source):
    """Link a vertex + fragment shader into a GPU program."""
    vs = compile_shader(vertex_source, GL_VERTEX_SHADER)
    fs = compile_shader(fragment_source, GL_FRAGMENT_SHADER)

    program = glCreateProgram()
    glAttachShader(program, vs)
    glAttachShader(program, fs)
    glLinkProgram(program)

    # Check linking status
    status = glGetProgramiv(program, GL_LINK_STATUS)
    if not status:
        error_log = glGetProgramInfoLog(program).decode()
        raise RuntimeError(f"Program link error:\n{error_log}")

    # Cleanup individual shaders (not needed after linking)
    glDeleteShader(vs)
    glDeleteShader(fs)

    return program


def set_uniform_mat4(program, name, matrix4):
    """Send a 4x4 matrix to a shader uniform."""
    loc = glGetUniformLocation(program, name)
    if loc == -1:
        return
    glUniformMatrix4fv(loc, 1, GL_FALSE, (ctypes.c_float * len(matrix4))(*matrix4))
