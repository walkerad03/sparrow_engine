#version 460 core

uniform sampler2D u_texture;

in vec2 v_uv;
out vec4 fragColor;

void main() {
    vec3 color = texture(u_texture, v_uv).rgb;

    color = color / (1.0 + color);
    color = pow(color, vec3(1.0 / 2.2));

    fragColor = vec4(color, 1.0);
}
