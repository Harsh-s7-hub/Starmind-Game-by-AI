#version 330 core

layout(location = 0) in vec3 aPos;
layout(location = 1) in vec2 aTex;
layout(location = 2) in vec3 aNormal;

uniform mat4 uModel;
uniform mat4 uView;
uniform mat4 uProj;
uniform mat3 uNormalMat;

out vec2 vTex;
out vec3 vNormal;
out vec3 vWorldPos;

void main() {
    vec4 world = uModel * vec4(aPos, 1.0);
    gl_Position = uProj * uView * world;

    vWorldPos = world.xyz;
    vTex = aTex;
    vNormal = normalize(uNormalMat * aNormal);
}
