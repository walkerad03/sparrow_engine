#version 460 core

uniform sampler2D u_albedo_tex;
uniform int u_has_albedo_tex;

in vec3 v_normal;
in vec2 v_uv;
in vec4 v_base_color;
in float v_roughness;
in float v_metallic;
in float v_emissive;

out vec4 fragColor;

void main() {
    vec3 N = normalize(v_normal);
    vec3 L = normalize(vec3(0.5, 1.0, 0.5));
    vec3 V = vec3(0.0, 0.0, 1.0);
    vec3 H = normalize(L + V);

    float NdotL = max(dot(N, L), 0.0);
    float NdotH = max(dot(N, H), 0.0);

    vec3 base_albedo = v_base_color.rgb;
    if (u_has_albedo_tex == 1) {
        base_albedo *= texture(u_albedo_tex, v_uv).rgb;
    }

    float roughness = clamp(v_roughness, 0.04, 1.0);
    float metallic = clamp(v_metallic, 0.0, 1.0);
    float emissive = max(v_emissive, 0.0);

    vec3 diffuse = base_albedo * (1.0 - metallic) * NdotL;
    float spec_power = mix(4.0, 128.0, 1.0 - roughness);
    float spec_strength = mix(0.04, 1.0, metallic);
    vec3 specular = vec3(pow(NdotH, spec_power) * spec_strength * NdotL);

    vec3 ambient = 0.03 * base_albedo;
    vec3 lit = ambient + diffuse + specular + base_albedo * emissive;
    fragColor = vec4(lit, v_base_color.a);
}
