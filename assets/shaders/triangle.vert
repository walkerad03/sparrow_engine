#version 330 core

in vec2 in_vert;

void main() {
    // Pass the position directly to OpenGL
    gl_Position = vec4(in_vert, 0.0, 1.0);
}