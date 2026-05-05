#version 460 core

uniform sampler2D u_albedo_tex;
uniform int u_has_albedo_tex;

uniform sampler2D u_shadow_map;
uniform int u_has_shadows;

uniform vec3 u_sun_dir;
uniform vec3 u_sun_color;
uniform vec3 u_cam_pos;

in vec3 v_world_pos;
in vec4 v_light_space_pos;
in vec3 v_normal;
in vec2 v_uv;
in vec4 v_base_color;
in float v_roughness;
in float v_metallic;
in float v_emissive;

out vec4 fragColor;

float calculate_shadow(vec4 light_space_pos, float bias) {
    // Perspective division
    vec3 proj_coords = light_space_pos.xyz / light_space_pos.w;
    // Transform to [0,1] range
    proj_coords = proj_coords * 0.5 + 0.5;

    // Check bounds: if outside light volume, it's not in shadow
    if (proj_coords.x < 0.0 || proj_coords.x > 1.0 ||
        proj_coords.y < 0.0 || proj_coords.y > 1.0 ||
        proj_coords.z > 1.0)
    {
        return 0.0;
    }

    float closest_depth = texture(u_shadow_map, proj_coords.xy).r;
    float current_depth = proj_coords.z;

    // Improved bias: much smaller base bias, but we'll also use NdotL
    // to scale it slightly.
    float shadow = current_depth - bias > closest_depth ? 1.0 : 0.0;
    return shadow;
}

void main() {
    vec3 N = normalize(v_normal);
    vec3 L = normalize(-u_sun_dir); // Light direction is from surface to light
    vec3 V = normalize(u_cam_pos - v_world_pos);
    vec3 H = normalize(L + V);

    float NdotL = max(dot(N, L), 0.0);
    float NdotH = max(dot(N, H), 0.0);

    float shadow = 0.0;
    if (u_has_shadows == 1) {
        // Very small depth bias now that we have normal bias
        float bias = 0.0001;
        shadow = calculate_shadow(v_light_space_pos, bias);
    }    vec3 base_albedo = v_base_color.rgb;
    if (u_has_albedo_tex == 1) {
        base_albedo *= texture(u_albedo_tex, v_uv).rgb;
    }

    float roughness = clamp(v_roughness, 0.04, 1.0);
    float metallic = clamp(v_metallic, 0.0, 1.0);
    float emissive = max(v_emissive, 0.0);

    vec3 diffuse = base_albedo * (1.0 - metallic) * NdotL * u_sun_color * (1.0 - shadow);
    float spec_power = mix(4.0, 128.0, 1.0 - roughness);
    float spec_strength = mix(0.04, 1.0, metallic);
    vec3 specular = vec3(pow(NdotH, spec_power) * spec_strength * NdotL) * u_sun_color * (1.0 - shadow);

    vec3 ambient = 0.03 * base_albedo;
    vec3 lit = ambient + diffuse + specular + base_albedo * emissive;
    fragColor = vec4(lit, v_base_color.a);
}
