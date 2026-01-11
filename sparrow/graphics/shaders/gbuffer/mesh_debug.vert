#version 330 core
in vec3 in_pos;
in vec3 in_uv;
void main() {
    vec3 dummy = in_uv * 0.00000001;
    gl_Position = vec4(in_pos.xy * 0.2, 0.0, 1.0) + vec4(dummy, 0.0);
}
