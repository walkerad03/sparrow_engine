#version 460 core

in vec2 v_uv;
out vec4 o_color;

uniform sampler2D u_g_albedo;
uniform sampler2D u_g_normal;
uniform sampler2D u_g_orm;   // g = roughness, b = metallic
uniform sampler2D u_g_depth;

uniform mat4 u_inv_view_proj;
uniform vec3 u_camera_pos;

const int MAX_LIGHTS = 64;
uniform int   u_light_count;
uniform vec4  u_light_pos_radius[MAX_LIGHTS];
uniform vec4  u_light_color_intensity[MAX_LIGHTS];

uniform vec3 u_sun_direction;
layout(binding=10) uniform sampler2D u_sky_lut;

const float PI = 3.14159265359;

// --- PBR HELPER FUNCTIONS ---

// 1. Normal Distribution Function (Trowbridge-Reitz GGX)
// Determines the size and shape of the specular highlight.
float DistributionGGX(vec3 N, vec3 H, float roughness) {
    float a = roughness * roughness;
    float a2 = a * a;
    float NdotH = max(dot(N, H), 0.0);
    float NdotH2 = NdotH * NdotH;

    float num = a2;
    float denom = (NdotH2 * (a2 - 1.0) + 1.0);
    denom = PI * denom * denom;

    return num / max(denom, 0.000001);
}

// 2. Geometry Function (Schlick-GGX)
// Approximates self-shadowing (micro-facets blocking each other).
float GeometrySchlickGGX(float NdotV, float roughness) {
    float r = (roughness + 1.0);
    float k = (r * r) / 8.0;

    float num = NdotV;
    float denom = NdotV * (1.0 - k) + k;

    return num / max(denom, 0.000001);
}

// Combine geometry obstruction for both View and Light directions
float GeometrySmith(vec3 N, vec3 V, vec3 L, float roughness) {
    float NdotV = max(dot(N, V), 0.0);
    float NdotL = max(dot(N, L), 0.0);
    float ggx2 = GeometrySchlickGGX(NdotV, roughness);
    float ggx1 = GeometrySchlickGGX(NdotL, roughness);

    return ggx1 * ggx2;
}

// 3. Fresnel Equation (Fresnel-Schlick)
// Calculates the ratio of surface reflection at different angles.
vec3 fresnelSchlick(float cosTheta, vec3 F0) {
    return F0 + (1.0 - F0) * pow(clamp(1.0 - cosTheta, 0.0, 1.0), 5.0);
}

// --- UTILS ---

vec3 reconstruct_ws(vec2 uv, float depth01) {
    vec4 ndc = vec4(uv * 2.0 - 1.0, depth01 * 2.0 - 1.0, 1.0);
    vec4 ws  = u_inv_view_proj * ndc;
    return ws.xyz / max(ws.w, 1e-6);
}

vec2 dir_to_uv(vec3 dir) {
    // atan(z, x) gives longitude (-PI to PI)
    // asin(y) gives latitude (-PI/2 to PI/2)
    float y = clamp(dir.y, -1.0, 1.0);
    float u = 0.5 + atan(dir.x, dir.z) / (2.0 * PI);
    float v = 0.5 + asin(y) / PI;
    return vec2(u, v);
}

void main() {
    // 1. Sample G-Buffer
    vec4 albedo_sample = texture(u_g_albedo, v_uv);
    vec3 albedo = pow(albedo_sample.rgb, vec3(2.2)); // Gamma Correct to Linear space

    vec3 n_enc = texture(u_g_normal, v_uv).xyz;
    vec3 N = normalize(n_enc * 2.0 - 1.0);

    vec3 orm = texture(u_g_orm, v_uv).xyz;
    float ao = orm.r;
    float roughness = orm.g;
    float metallic = orm.b;

    float depth01 = texture(u_g_depth, v_uv).r;

    vec4 ndc = vec4(v_uv * 2.0 - 1.0, 1.0, 1.0);
    vec4 far_plane_ws = u_inv_view_proj * ndc;
    vec3 V_dir = normalize(far_plane_ws.xyz / far_plane_ws.w - u_camera_pos);

    // Early out for background
    if (depth01 >= 0.999999) {
        vec2 sky_uv = dir_to_uv(V_dir);
        vec3 sky_color = texture(u_sky_lut, sky_uv).rgb;
        o_color = vec4(sky_color, 1.0);
        return;
    }

    vec3 pos_ws = reconstruct_ws(v_uv, depth01);
    vec3 V = normalize(u_camera_pos - pos_ws);

    // 2. Calculate F0 (Base Reflectivity)
    // Dielectrics (plastic, wood) average 0.04. Metals use their albedo color.
    vec3 F0 = vec3(0.04); 
    F0 = mix(F0, albedo, metallic);

    vec3 Lo = vec3(0.0); // Total outgoing radiance

    // 3. Lighting Loop
    for(int i = 0; i < u_light_count; ++i) {
        vec3 Lpos = u_light_pos_radius[i].xyz;
        float radius = u_light_pos_radius[i].w;
        vec3 lightColor = u_light_color_intensity[i].rgb * u_light_color_intensity[i].w;

        vec3 toL = Lpos - pos_ws;
        float distance = length(toL);

        if(distance > radius || distance <= 1e-6) continue;

        // Attenuation (Soft Falloff)
        float x = 1.0 - (distance / radius);
        float attenuation = x * x; // Quadratic falloff approximation
        
        vec3 L = normalize(toL);
        vec3 H = normalize(V + L); // Halfway vector
        vec3 radiance = lightColor * attenuation;

        // --- PBR COOK-TORRANCE BRDF ---

        // D = Normal Distribution (GGX)
        float D = DistributionGGX(N, H, roughness);
        
        // G = Geometry Obstruction (Smith)
        float G = GeometrySmith(N, V, L, roughness);
        
        // F = Fresnel (Schlick)
        vec3 F = fresnelSchlick(max(dot(H, V), 0.0), F0);

        // Specular Term (Reflected Light)
        vec3 numerator = D * G * F;
        float NdotV = max(dot(N, V), 0.0);
        float NdotL = max(dot(N, L), 0.0);
        float denominator = 4.0 * NdotV * NdotL + 0.0001; // +0.0001 to prevent divide by zero
        vec3 specular = numerator / denominator;

        // Diffuse Term (Refracted Light)
        // kS is the ratio of light that reflects (Fresnel term)
        vec3 kS = F;
        
        // kD is the ratio of light that refracts (Diffuse)
        // Energy conservation: Diffuse + Specular = 1.0
        vec3 kD = vec3(1.0) - kS;
        
        // Metals absorb refracted light (no diffuse), so multiply kD by (1 - metallic)
        kD *= 1.0 - metallic;

        // Lambertian Diffuse: albedo / PI
        vec3 diffuse = kD * (albedo / PI);

        // Final Light Contribution
        Lo += (diffuse + specular) * radiance * NdotL;
    }

    // Sun shading

    vec3 L_sun = normalize(-u_sun_direction); // Direction FROM the sun
    vec3 H_sun = normalize(V + L_sun);
    float NdotL_sun = max(dot(N, L_sun), 0.0);

    vec3 sun_radiance = vec3(1.0) * 20.0;

    float D_sun = DistributionGGX(N, H_sun, roughness);
    float G_sun = GeometrySmith(N, V, L_sun, roughness);
    vec3 F_sun  = fresnelSchlick(max(dot(H_sun, V), 0.0), F0);

    vec3 spec_num_sun = D_sun * G_sun * F_sun;
    float spec_den_sun = 4.0 * max(dot(N, V), 0.0) * NdotL_sun + 0.0001;
    vec3 specular_sun = spec_num_sun / spec_den_sun;

    vec3 kS_sun = F_sun;
    vec3 kD_sun = (vec3(1.0) - kS_sun) * (1.0 - metallic);
    vec3 diffuse_sun = kD_sun * (albedo / PI);

    Lo += (diffuse_sun + specular_sun) * sun_radiance * NdotL_sun;
    
    vec3 color = Lo;

    o_color = vec4(color, 1.0);
}