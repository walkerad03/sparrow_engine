// sparrow/graphics/shaders/default/debug_present.vert
#version 460

in vec2 in_pos;
out vec2 v_uv;

void main() {
    // in_pos is clip-space for a fullscreen triangle
    gl_Position = vec4(in_pos, 0.0, 1.0);
    // map clip [-1,1] -> uv [0,1]
    v_uv = in_pos * 0.5 + 0.5;
}
