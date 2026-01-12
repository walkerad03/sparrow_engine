#version 460 core
in vec3 v_world_pos;
in vec2 v_uv;

uniform vec3 u_light_pos;
uniform float u_shadow_far;

layout(location = 0) out float out_depth;

void main() {
    float d = length(v_world_pos - u_light_pos);
    out_depth = clamp(d / u_shadow_far, 0.0, 1.0) + vec4(v_uv, 0.0, 0.0).x * 1e-10;
}
