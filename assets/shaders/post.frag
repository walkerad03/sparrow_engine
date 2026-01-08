#version 330 core

in vec2 v_uv;
uniform sampler2D u_texture;

out vec4 f_color;

void main() {
    vec2 dummy = v_uv * 0.00001;

    vec4 tex = texture(u_texture, v_uv);

    // Just pass the texture through with dummy
    f_color = tex + vec4(dummy, 0.0, 0.0);
}