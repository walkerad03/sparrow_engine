#version 330 core

in vec2 v_uv;

uniform sampler2D u_albedo;
uniform vec4 u_color; // Ambient Color (e.g. Dark Blue)

out vec4 f_color;

void main() {
    vec4 albedo = texture(u_albedo, v_uv);
    
    // Just multiply texture color by ambient brightness
    f_color = albedo * u_color;
}