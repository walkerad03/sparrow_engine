#version 460 core

out vec4 frag_color;

in vec3 v_world_pos;
in vec3 v_normal;

uniform vec3 u_cam_pos;
uniform vec4 u_base_color;
uniform float u_roughness;
uniform float u_metalness;

uniform int u_light_count;
uniform vec4 u_light_pos_radius[64];
uniform vec4 u_light_color_intensity[64];


const float PI = 3.14159265359;

// Normal dist function (Trowbridge-Reitz GGX)
float DistributionGGX(vec3 N, vec3 H, float roughness) {
    float a = roughness * roughness;
    float a2 = a * a;
    float NdotH = max(dot(N, H), 0.0);
    float NdotH2 = NdotH * NdotH;

    float num = a2;
    float denom = (NdotH2 * (a2 - 1.0) + 1.0);
    denom = PI * denom * denom;

    return num / denom;
}

// Geometry Function (Schlick-GGX)
float GeometrySchlickGGX(float NdotV, float roughness) {
    float r = (roughness + 1.0);
    float k = (r * r) / 8.0;

    float num = NdotV;
    float denom = NdotV * (1.0 - k) + k;

    return num / denom;
}

// Smith's method for Geometry shadowing/masking
float GeometrySmith(vec3 N, vec3 V, vec3 L, float roughness) {
    float NdotV = max(dot(N, V), 0.0);
    float NdotL = max(dot(N, L), 0.0);
    float ggx2 = GeometrySchlickGGX(NdotV, roughness);
    float ggx1 = GeometrySchlickGGX(NdotL, roughness);

    return ggx1 * ggx2;
}

// Fresnel Equation (Schlick's approximation)
vec3 fresnelSchlick(float cosTheta, vec3 F0) {
    return F0 + (1.0 - F0) * pow(clamp(1.0 - cosTheta, 0.0, 1.0), 5.0);
}

void main() {
    vec3 N = normalize(v_normal);
    vec3 V = normalize(u_cam_pos - v_world_pos);
    vec3 albedo = pow(u_base_color.rgb, vec3(2.2));

    vec3 F0 = vec3(0.04); 
    F0 = mix(F0, albedo, u_metalness);

    vec3 Lo = vec3(0.0);
    for(int i = 0; i < u_light_count; ++i) {
        vec3 L = normalize(u_light_pos_radius[i].xyz - v_world_pos);
        vec3 H = normalize(V + L);
        float dist = length(u_light_pos_radius[i].xyz - v_world_pos);
        float attenuation = pow(clamp(1.0 - pow(dist / u_light_pos_radius[i].w, 4.0), 0.0, 1.0), 2.0) / (dist * dist + 1.0);
        vec3 radiance = u_light_color_intensity[i].rgb * u_light_color_intensity[i].w * attenuation;

        float NDF = DistributionGGX(N, H, u_roughness);
        float G   = GeometrySmith(N, V, L, u_roughness);    
        vec3 F    = fresnelSchlick(max(dot(H, V), 0.0), F0);

        vec3 numerator    = NDF * G * F; 
        float denominator = 4.0 * max(dot(N, V), 0.0) * max(dot(N, L), 0.0) + 0.0001; // + 0.0001 to prevent divide by zero
        vec3 specular = numerator / denominator;

        vec3 kS = F;
        vec3 kD = vec3(1.0) - kS;

        kD *= 1.0 - u_metalness;

        float NdotL = max(dot(N, L), 0.0);
        Lo += (kD * albedo / PI + specular) * radiance * NdotL;
    }

    vec3 ambient = vec3(0.01) * albedo;
    vec3 color = ambient + Lo;

    frag_color = vec4(color, u_base_color.a);
}