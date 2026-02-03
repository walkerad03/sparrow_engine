#version 460 core

in vec3 v_normal;
in vec2 v_uv;
in vec4 v_color;

out vec4 fragColor;

void main() {
    vec3 L = normalize(vec3(0.5, 1.0, 0.5));
    float NdotL = max(dot(normalize(v_normal), L), 0.1);

    vec3 uv_tint = vec3(v_uv, 0.0) * 0.0001;

    fragColor = vec4(v_color.rgb * NdotL + uv_tint, 1.0);
}
