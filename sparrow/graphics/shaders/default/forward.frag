#version 460 core

out vec4 fragColor;

uniform vec4 u_base_color;

void main() {
    fragColor = u_base_color + vec4(1.0f, 0.5f, 0.2f, 1.0f);
}
