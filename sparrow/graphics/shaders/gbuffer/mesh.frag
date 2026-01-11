#version 330 core

in vec2 v_uv;

uniform sampler2D u_albedo;

out vec4 out_color;

void main() {
    vec4 c = texture(u_albedo, v_uv);
    if (c.a < 0.01) discard;
    out_color = c;
}
