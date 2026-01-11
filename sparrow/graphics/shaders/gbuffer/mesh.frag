#version 330 core

in vec2 v_uv;

uniform sampler2D u_albedo;

layout (location = 0) out vec4 out_albedo;
layout (location = 1) out vec3 out_normal;

void main() {
    vec4 c = texture(u_albedo, v_uv);
    if (c.a < 0.01) discard;
    out_albedo = c;

    out_normal = vec3(0.0, 0.0, 1.0);
}
