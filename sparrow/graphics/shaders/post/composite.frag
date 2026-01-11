#version 330 core

in vec2 v_uv;

uniform sampler2D u_diffuse;
uniform sampler2D u_lighting;

out vec4 out_color;

void main() {
    vec4 albedo = texture(u_diffuse, v_uv);
    vec4 lighting = texture(u_lighting, v_uv);
    
    out_color = albedo * lighting;
}
