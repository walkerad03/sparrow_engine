#version 460 core

in vec2 v_uv;
out vec4 frag_color;

layout (binding = 0) uniform sampler2D u_hdr;

void main() {
    // Sample the HDR texture directly.
    frag_color = texture(u_hdr, v_uv);
}
