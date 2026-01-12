#version 460 core

in vec2 v_uv;
in vec3 v_world_pos;

uniform sampler2D u_albedo;

layout (location = 0) out vec4 out_albedo;
layout (location = 1) out vec4 out_normal; // match your RGBA normal attachment (f16) :contentReference[oaicite:3]{index=3}

vec3  encodeNormal(vec3 n) {
    return n * 0.5 + 0.5;
}

void main() {
    vec4 c = texture(u_albedo, v_uv);
    if (c.a < 0.01) discard;
    
    out_albedo = c;

    vec3 dx = dFdx(v_world_pos);
    vec3 dy = dFdy(v_world_pos);
    vec3 n = normalize(cross(dx, dy));

    out_normal = vec4(encodeNormal(n), 1.0);
}
