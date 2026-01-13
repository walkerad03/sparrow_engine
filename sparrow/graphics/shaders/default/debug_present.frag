// sparrow/graphics/shaders/default/debug_present.frag
#version 460

in vec2 v_uv;
out vec4 fragColor;

uniform sampler2D u_tex;

void main() {
    fragColor = texture(u_tex, v_uv);
}
