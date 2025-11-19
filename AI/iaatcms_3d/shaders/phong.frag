#version 330 core

in vec2 vTex;
in vec3 vNormal;
in vec3 vWorldPos;

out vec4 FragColor;

uniform sampler2D uTexture;
uniform vec3 uLightPos;
uniform vec3 uViewPos;
uniform vec3 uBaseColor;
uniform float uShininess;
uniform float uSpecularStrength;

vec3 calcPhong(vec3 albedo, vec3 normal, vec3 lightDir, vec3 viewDir) {
    vec3 ambient = 0.12 * albedo;

    float diff = max(dot(normal, lightDir), 0.0);
    vec3 diffuse = diff * albedo;

    vec3 reflectDir = reflect(-lightDir, normal);
    float spec = pow(max(dot(viewDir, reflectDir), 0.0), uShininess);
    vec3 specular = uSpecularStrength * spec * vec3(1.0);

    return ambient + diffuse + specular;
}

void main() {
    vec4 tex = texture(uTexture, vTex);
    vec3 albedo = tex.rgb * uBaseColor;

    vec3 lightDir = normalize(uLightPos - vWorldPos);
    vec3 viewDir = normalize(uViewPos - vWorldPos);

    vec3 color = calcPhong(albedo, normalize(vNormal), lightDir, viewDir);

    // runway glow effect near z = 0
    float glow = exp(-abs(vWorldPos.z) * 0.008) * 0.15;
    color += glow * vec3(1.0, 0.9, 0.4);

    FragColor = vec4(color, tex.a);
}
