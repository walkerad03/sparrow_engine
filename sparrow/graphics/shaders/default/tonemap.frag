#version 460 core

in vec2 v_uv;
out vec4 frag_color;

uniform sampler2D u_hdr;

vec3 tonemap_reinhard(vec3 x) {
    return x / (1.0 + x);
}

void main() {
    vec3 hdr = texture(u_hdr, v_uv).rgb;

    vec3 mapped = tonemap_reinhard(hdr);

    mapped = pow(mapped, vec3(1.0 / 2.2));

    frag_color = vec4(mapped, 1.0);
}
