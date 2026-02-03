#version 460 core
out vec4 fragColor;

in vec3 v_frag_pos;
in vec3 v_normal;

struct Material {
    vec3 albedo;
    float roughness;
    float metallic;
};

uniform Material u_material;

uniform vec3 u_light_color;
uniform vec3 u_light_pos;
uniform vec3 u_camera_pos;

layout(binding = 5) uniform sampler2D u_sky_lut;

const float PI = 3.14159265359;

float DistributionGXX(vec3 N, vec3 H, float roughness) {
    float a = roughness * roughness;
    float a2 = a*a;
    float NdotH = max(dot(N, H), 0.0);
    float NdotH2 = NdotH*NdotH;

    float num = a2;
    float denom = (NdotH2 * (a2 - 1.0) + 1.0);
    denom = PI * denom * denom;

    return num / max(denom, 0.0000001);
}


float GeometrySchlickGGX(float NdotV, float roughness) {
    float r = (roughness + 1.0);
    float k = (r*r) / 8.0;

    float num   = NdotV;
    float denom = NdotV * (1.0 - k) + k;

    return num / denom;
}

float GeometrySmith(vec3 N, vec3 V, vec3 L, float roughness) {
    float NdotV = max(dot(N, V), 0.0);
    float NdotL = max(dot(N, L), 0.0);
    float ggx2  = GeometrySchlickGGX(NdotV, roughness);
    float ggx1  = GeometrySchlickGGX(NdotL, roughness);

    return ggx1 * ggx2;
}

vec3 fresnelSchlick(float cosTheta, vec3 F0) {
    return F0 + (1.0 - F0) * pow(clamp(1.0 - cosTheta, 0.0, 1.0), 5.0);
}

// void main() {
//     vec3 N = normalize(v_normal);
//     vec3 V = normalize(u_camera_pos - v_frag_pos);

//     vec3 F0 = vec3(0.04);
//     F0 = mix(F0, u_material.albedo, u_material.metallic);

//     vec3 L = normalize(u_light_pos - v_frag_pos);
//     vec3 H = normalize(V + L);

//     float distance = length(u_light_pos - v_frag_pos);
//     float attenuation = 1.0 / (distance * distance);
//     vec3 radiance = u_light_color * attenuation;

//     float NDF = DistributionGXX(N, H, u_material.roughness);
//     float G = GeometrySmith(N, V, L, u_material.roughness);
//     vec3 F = fresnelSchlick(max(dot(H, V), 0.0), F0);

//     vec3 numerator = NDF * G * F;
//     float denominator = 4.0 * max(dot(N, V), 0.0) * max(dot(N, L), 0.0) + 0.0001;
//     vec3 specular = numerator / denominator;

//     vec3 kS = F;
//     vec3 kD = vec3(1.0) - kS;
//     kD *= 1.0 - u_material.metallic;

//     float NdotL = max(dot(N, L), 0.0);

//     vec3 Lo = (kD * u_material.albedo / PI + specular) * radiance * NdotL;

//     vec3 ambient = vec3(0.03) * u_material.albedo;

//     vec3 color = ambient + Lo;

//     fragColor = vec4(color, 1.0);
// }

void main() {
    vec3 N = normalize(v_normal);
    vec3 L = normalize(u_light_pos - v_frag_pos);

    float numColorSteps = 4.0;

    float diffuse = max(dot(N, L), 0.0);

    float diffuseToon = max(ceil(diffuse * numColorSteps) / numColorSteps, 0.0);

    vec3 ambient = vec3(0.1) * u_material.albedo;

    vec3 lightColor = u_light_color;
    vec3 objectColor = u_material.albedo;

    vec3 color = ambient + (diffuseToon * lightColor * objectColor);

    fragColor = vec4(color, 1.0);
}
