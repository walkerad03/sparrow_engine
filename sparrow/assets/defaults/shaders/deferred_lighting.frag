#version 460 core

in vec2 v_uv;
out vec4 o_color;

layout(binding=0)uniform sampler2D u_g_albedo;
layout(binding=1)uniform sampler2D u_g_normal;
layout(binding=2)uniform sampler2D u_g_orm;   // g = roughness, b = metallic
layout(binding=3)uniform sampler2D u_g_depth;

uniform mat4 u_inv_view_proj;
uniform vec3 u_camera_pos;

const int MAX_LIGHTS = 64;
uniform int   u_light_count;
uniform vec4  u_light_pos_radius[MAX_LIGHTS];
uniform vec4  u_light_color_intensity[MAX_LIGHTS];

layout(binding=10) uniform sampler2D u_sky_lut;
uniform float u_sky_max_mip;

const float PI = 3.14159265359;

// --- PBR HELPER FUNCTIONS ---

// 1. Normal Distribution Function (Trowbridge-Reitz GGX)
// Determines the size and shape of the specular highlight.
float DistributionGGX(vec3 N, vec3 H, float roughness) {
    float a = max(roughness, 0.02);
    a = a * a;
    float a2 = a * a;
    float NdotH = max(dot(N, H), 0.0);
    float NdotH2 = NdotH * NdotH;

    float num = a2;
    float denom = (NdotH2 * (a2 - 1.0) + 1.0);
    denom = PI * denom * denom;

    return num / max(denom, 1e-6);
}

// 2. Geometry Function (Schlick-GGX)
// Approximates self-shadowing (micro-facets blocking each other).
float GeometrySchlickGGX(float NdotV, float roughness) {
    float r = (roughness + 1.0);
    float k = (r * r) / 8.0;
    return NdotV / max(NdotV * (1.0 - k) + k, 1e-6);
}

// Combine geometry obstruction for both View and Light directions
float GeometrySmith(vec3 N, vec3 V, vec3 L, float roughness) {
    float NdotV = max(dot(N, V), 0.0);
    float NdotL = max(dot(N, L), 0.0);
    float ggxV = GeometrySchlickGGX(NdotV, roughness);
    float ggxL = GeometrySchlickGGX(NdotL, roughness);
    return ggxV * ggxL;
}

// 3. Fresnel Equation (Fresnel-Schlick)
// Calculates the ratio of surface reflection at different angles.
vec3 fresnelSchlick(float cosTheta, vec3 F0) {
    float ct = clamp(1.0 - cosTheta, 0.0, 1.0);
    return F0 + (1.0 - F0) * (ct * ct * ct * ct * ct);
}

// --- UTILS ---

vec3 reconstruct_ws(vec2 uv, float depth01) {
    vec4 ndc = vec4(uv * 2.0 - 1.0, depth01 * 2.0 - 1.0, 1.0);
    vec4 ws  = u_inv_view_proj * ndc;
    return ws.xyz / max(ws.w, 1e-6);
}

vec3 view_dir_from_uv(vec2 uv) {
    // Reconstruct a world-space view direction through the pixel by unprojecting a point on the far plane
    vec4 ndc = vec4(uv * 2.0 - 1.0, 1.0, 1.0);
    vec4 ws  = u_inv_view_proj * ndc;
    vec3 p   = ws.xyz / max(ws.w, 1e-6);
    return normalize(p - u_camera_pos);
}

vec2 dir_to_uv(vec3 d) {
    d = normalize(d);
    float u = 0.5 + atan(d.x, d.z) / (2.0 * PI);
    float v = 0.5 + asin(clamp(d.y, -1.0, 1.0)) / PI;
    return vec2(u, v);
}

vec3 env_radiance(vec3 dir, float mip) {
    vec2 uv = dir_to_uv(dir);
    return textureLod(u_sky_lut, uv, mip).rgb;
}

// cosine-weighted hemisphere sampling for diffuse IBL Monte Carlo (few taps)
vec3 sample_cosine_hemisphere(vec3 N, float u1, float u2) {
    float phi = 2.0 * PI * u1;
    float r   = sqrt(u2);
    float x = r * cos(phi);
    float y = r * sin(phi);
    float z = sqrt(max(0.0, 1.0 - u2));

    vec3 up = abs(N.y) < 0.999 ? vec3(0,1,0) : vec3(1,0,0);
    vec3 T  = normalize(cross(up, N));
    vec3 B  = cross(N, T);

    return normalize(T * x + B * y + N * z);
}

// cheap hash-based “random” from screen uv + tap index (no temporal stability needed for 1 spp)
float hash12(vec2 p) {
    vec3 p3  = fract(vec3(p.xyx) * 0.1031);
    p3 += dot(p3, p3.yzx + 33.33);
    return fract((p3.x + p3.y) * p3.z);
}

void main() {
    // 1. Sample G-Buffer
    vec3 albedo_srgb = texture(u_g_albedo, v_uv).rgb;
    vec3 albedo = pow(albedo_srgb, vec3(2.2)); // keep if you stored sRGB; remove if already linear

    vec3 n_enc = texture(u_g_normal, v_uv).xyz;
    vec3 N = normalize(n_enc * 2.0 - 1.0);

    vec3 orm = texture(u_g_orm, v_uv).xyz;
    float ao        = orm.r;
    float roughness = clamp(orm.g, 0.02, 1.0);
    float metallic  = clamp(orm.b, 0.0, 1.0);

    float depth01 = texture(u_g_depth, v_uv).r;

    // View ray direction for background
    vec3 Vray = view_dir_from_uv(v_uv);

    // Early out for background
    if (depth01 >= 0.999999) {
        o_color = vec4(env_radiance(Vray, 0.0), 1.0);
        return;
    }

    vec3 pos_ws = reconstruct_ws(v_uv, depth01);
    vec3 V = normalize(u_camera_pos - pos_ws);

    // 2. Calculate F0 (Base Reflectivity)
    // Dielectrics (plastic, wood) average 0.04.
    // Metals use their albedo color.
    vec3 F0 = mix(vec3(0.04), albedo, metallic);

    vec3 Lo = vec3(0.0);

    // 3. Lighting Loop
    // NOTE: u_light_color_intensity.rgb is "color", .w is intensity scale.
    //       We use inverse-square; radius is a hard cutoff only.
    for (int i = 0; i < u_light_count; ++i) {
        vec3  Lpos   = u_light_pos_radius[i].xyz;
        float radius = u_light_pos_radius[i].w;

        vec3  toL = Lpos - pos_ws;
        float dist2 = dot(toL, toL);
        float dist  = sqrt(dist2);

        if (dist <= 1e-4) continue;
        if (radius > 0.0 && dist > radius) continue;

        vec3 L = toL / dist;
        vec3 H = normalize(V + L);

        float NdotL = max(dot(N, L), 0.0);
        float NdotV = max(dot(N, V), 0.0);
        if (NdotL <= 0.0 || NdotV <= 0.0) continue;

        // Radiance at the shading point
        vec3 lightColor = u_light_color_intensity[i].rgb;
        float intensity = u_light_color_intensity[i].w;
        vec3 radiance = lightColor * intensity / max(dist2, 1e-6);

        float D = DistributionGGX(N, H, roughness);
        float G = GeometrySmith(N, V, L, roughness);
        vec3  F = fresnelSchlick(max(dot(H, V), 0.0), F0);

        vec3 spec = (D * G * F) / max(4.0 * NdotV * NdotL, 1e-6);

        vec3 kS = F;
        vec3 kD = (vec3(1.0) - kS) * (1.0 - metallic);
        vec3 diff = kD * (albedo / PI);

        Lo += (diff + spec) * radiance * NdotL;
    }

    // 4) Image-based lighting (replace hardcoded sun)
    //
    // IMPORTANT: This u_sky_lut is *radiance*. For diffuse we need irradiance:
    //   E(N) = ∫_hemisphere L(w) (N·w) dw
    // We'll approximate with a few cosine-weighted samples:
    //   with pdf = (N·w)/PI -> estimator simplifies to:
    //   E ≈ (PI / S) Σ L(w_i)
    // Then diffuse ambient = (albedo/PI) * E -> albedo * (1/S) Σ L(w_i)
    //
    // Specular IBL: very simplified "prefiltered env by mip" (no BRDF LUT split-sum).
    // This is not perfect, but is a big step up vs hardcoded directional sun.
    //
    const int DIFF_SAMPLES = 8;
    vec3 diff_sum = vec3(0.0);
    for (int s = 0; s < DIFF_SAMPLES; s++) {
        // deterministic per-pixel noise (stable in screen space)
        float u1 = hash12(v_uv * 1024.0 + float(s) * 17.0);
        float u2 = hash12(v_uv * 1024.0 + float(s) * 41.0);
        vec3 wi = sample_cosine_hemisphere(N, u1, u2);
        diff_sum += env_radiance(wi, 0.0);
    }
    vec3 diffuse_ibl = diff_sum / float(DIFF_SAMPLES); // see derivation above: albedo factor comes later


    // Specular IBL (prefilter by roughness using mip)
    vec3 R = reflect(-V, N);
    float mip = roughness * u_sky_max_mip;
    vec3 spec_env = env_radiance(R, mip);

    // Fresnel term for IBL uses NoV (common approximation)
    float NoV = max(dot(N, V), 0.0);
    vec3  F   = fresnelSchlick(NoV, F0);

    vec3 kS = F;
    vec3 kD = (vec3(1.0) - kS) * (1.0 - metallic);

    // Apply AO to diffuse ambient (common practice)
    vec3 ambient = (kD * albedo * diffuse_ibl) * ao;

    // Specular ambient (approx; without BRDF LUT this will be “hotter” than a full split-sum)
    vec3 spec_ambient = spec_env * kS;

    vec3 color = Lo + ambient + spec_ambient;

    // Output is HDR linear. Tonemap/exposure later.
    o_color = vec4(color, 1.0);
}