#version 330 core

in vec2 v_uv;
uniform sampler2D u_texture;

out vec4 f_color;

void main() {
    // Just pass the texture through
    f_color = texture(u_texture, v_uv);
}