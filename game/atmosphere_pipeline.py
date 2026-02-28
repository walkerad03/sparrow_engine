from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import moderngl
import numpy as np

from sparrow.assets import AssetHandle, AssetServer, DefaultMeshes
from sparrow.graphics.graph import (
    FramebufferDesc,
    PassBuildInfo,
    PassExecutionContext,
    PassResourceUse,
    RenderPass,
    RenderServices,
    TextureDesc,
)
from sparrow.graphics.graph.builder import RenderGraphBuilder
from sparrow.graphics.passes.clear import ClearPass
from sparrow.graphics.passes.tonemap import TonemapPass
from sparrow.graphics.utils import create_fullscreen_triangle, pack_mat4
from sparrow.graphics.utils.ids import PassId, ResourceId
from sparrow.graphics.utils.uniforms import set_uniform

PLANET_RADIUS = 1200.0
TERRAIN_MAX_ELEVATION = 14.0
TERRAIN_HEIGHT_SCALE = TERRAIN_MAX_ELEVATION / PLANET_RADIUS
WATER_LEVEL = 1.0
ATMOSPHERE_RADIUS = 1518.83

PLANET_TERRAIN_VERTEX_SHADER = """
#version 460 core

uniform mat4 u_view_proj;
uniform mat4 u_model;
uniform float u_height_scale;

layout (location = 0) in vec3 in_pos;
layout (location = 1) in vec3 in_normal;
layout (location = 2) in vec2 in_uv;

out vec3 v_world_pos;
out vec3 v_base_n;
out vec2 v_uv;

float hash13(vec3 p) {
    p = fract(p * 0.3183099 + 0.1);
    p *= 17.0;
    return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
}

float noise3(vec3 p) {
    vec3 i = floor(p);
    vec3 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);

    float n000 = hash13(i + vec3(0.0, 0.0, 0.0));
    float n100 = hash13(i + vec3(1.0, 0.0, 0.0));
    float n010 = hash13(i + vec3(0.0, 1.0, 0.0));
    float n110 = hash13(i + vec3(1.0, 1.0, 0.0));
    float n001 = hash13(i + vec3(0.0, 0.0, 1.0));
    float n101 = hash13(i + vec3(1.0, 0.0, 1.0));
    float n011 = hash13(i + vec3(0.0, 1.0, 1.0));
    float n111 = hash13(i + vec3(1.0, 1.0, 1.0));

    float nx00 = mix(n000, n100, f.x);
    float nx10 = mix(n010, n110, f.x);
    float nx01 = mix(n001, n101, f.x);
    float nx11 = mix(n011, n111, f.x);
    float nxy0 = mix(nx00, nx10, f.y);
    float nxy1 = mix(nx01, nx11, f.y);
    return mix(nxy0, nxy1, f.z);
}

float fbm(vec3 p) {
    float v = 0.0;
    float a = 0.5;
    for (int i = 0; i < 5; i++) {
        v += a * noise3(p);
        p = p * 2.03 + vec3(17.1, 31.7, 11.3);
        a *= 0.5;
    }
    return v;
}

float ridged(vec3 p) {
    float v = 0.0;
    float a = 0.6;
    for (int i = 0; i < 4; i++) {
        float n = noise3(p) * 2.0 - 1.0;
        n = 1.0 - abs(n);
        v += n * n * a;
        p = p * 2.11 + vec3(9.2, 5.4, 13.3);
        a *= 0.5;
    }
    return v;
}

float terrain_height(vec3 n) {
    float continents = fbm(n * 2.4);
    float mountain_mask = smoothstep(0.50, 0.76, continents);
    float mountain = ridged(n * 9.0) * mountain_mask;
    float detail = fbm(n * 26.0) * 0.14;

    float h = (continents - 0.52) * 1.4 + mountain * 0.95 + detail - 0.08;
    return clamp(h, -0.55, 1.2);
}

void main() {
    vec3 base_n = normalize(in_pos + in_normal * 1e-7);
    float h = terrain_height(base_n);
    vec3 pos_local = base_n * (1.0 + h * u_height_scale);
    vec4 world_pos = u_model * vec4(pos_local, 1.0);

    v_world_pos = world_pos.xyz;
    v_base_n = base_n;
    v_uv = in_uv;

    gl_Position = u_view_proj * world_pos;
}
"""

PLANET_TERRAIN_FRAGMENT_SHADER = """
#version 460 core

uniform mat4 u_model;
uniform vec3 u_sun_dir;
uniform vec3 u_camera_pos;
uniform float u_height_scale;

in vec3 v_world_pos;
in vec3 v_base_n;
in vec2 v_uv;

out vec4 fragColor;

float hash13(vec3 p) {
    p = fract(p * 0.3183099 + 0.1);
    p *= 17.0;
    return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
}

float noise3(vec3 p) {
    vec3 i = floor(p);
    vec3 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);

    float n000 = hash13(i + vec3(0.0, 0.0, 0.0));
    float n100 = hash13(i + vec3(1.0, 0.0, 0.0));
    float n010 = hash13(i + vec3(0.0, 1.0, 0.0));
    float n110 = hash13(i + vec3(1.0, 1.0, 0.0));
    float n001 = hash13(i + vec3(0.0, 0.0, 1.0));
    float n101 = hash13(i + vec3(1.0, 0.0, 1.0));
    float n011 = hash13(i + vec3(0.0, 1.0, 1.0));
    float n111 = hash13(i + vec3(1.0, 1.0, 1.0));

    float nx00 = mix(n000, n100, f.x);
    float nx10 = mix(n010, n110, f.x);
    float nx01 = mix(n001, n101, f.x);
    float nx11 = mix(n011, n111, f.x);
    float nxy0 = mix(nx00, nx10, f.y);
    float nxy1 = mix(nx01, nx11, f.y);
    return mix(nxy0, nxy1, f.z);
}

float fbm(vec3 p) {
    float v = 0.0;
    float a = 0.5;
    for (int i = 0; i < 5; i++) {
        v += a * noise3(p);
        p = p * 2.03 + vec3(17.1, 31.7, 11.3);
        a *= 0.5;
    }
    return v;
}

float ridged(vec3 p) {
    float v = 0.0;
    float a = 0.6;
    for (int i = 0; i < 4; i++) {
        float n = noise3(p) * 2.0 - 1.0;
        n = 1.0 - abs(n);
        v += n * n * a;
        p = p * 2.11 + vec3(9.2, 5.4, 13.3);
        a *= 0.5;
    }
    return v;
}

float terrain_height(vec3 n) {
    float continents = fbm(n * 2.4);
    float mountain_mask = smoothstep(0.50, 0.76, continents);
    float mountain = ridged(n * 9.0) * mountain_mask;
    float detail = fbm(n * 26.0) * 0.14;

    float h = (continents - 0.52) * 1.4 + mountain * 0.95 + detail - 0.08;
    return clamp(h, -0.55, 1.2);
}

vec3 orthogonal(vec3 n) {
    return normalize(
        abs(n.z) < 0.999 ? cross(n, vec3(0.0, 0.0, 1.0)) : cross(n, vec3(0.0, 1.0, 0.0))
    );
}

void main() {
    vec3 n0 = normalize(v_base_n);
    vec3 t = orthogonal(n0);
    vec3 b = normalize(cross(n0, t));

    float eps = 0.0014;
    vec3 n_t = normalize(n0 + t * eps);
    vec3 n_b = normalize(n0 + b * eps);

    float h0 = terrain_height(n0);
    float ht = terrain_height(n_t);
    float hb = terrain_height(n_b);

    vec3 p0 = n0 * (1.0 + h0 * u_height_scale);
    vec3 pt = n_t * (1.0 + ht * u_height_scale);
    vec3 pb = n_b * (1.0 + hb * u_height_scale);

    vec3 n_local = normalize(cross(pt - p0, pb - p0));
    if (dot(n_local, n0) < 0.0) {
        n_local = -n_local;
    }

    vec3 n = normalize(mat3(u_model) * n_local);
    vec3 v = normalize(u_camera_pos - v_world_pos);
    vec3 l = normalize(u_sun_dir);

    float h = h0 + sin(v_uv.x * 12.0) * sin(v_uv.y * 10.0) * 0.01;
    float above_sea = smoothstep(0.0, 0.04, h);
    float coast = smoothstep(-0.01, 0.03, h) * (1.0 - smoothstep(0.03, 0.08, h));
    float mountain = smoothstep(0.30, 0.82, h);
    float latitude = abs(n0.y);
    float dryness = fbm(n0 * 7.0 + vec3(2.0, -1.0, 0.5));

    vec3 sand = vec3(0.49, 0.44, 0.28);
    vec3 soil = vec3(0.26, 0.22, 0.17);
    vec3 forest = vec3(0.08, 0.23, 0.09);
    vec3 scrub = vec3(0.24, 0.28, 0.18);
    vec3 rock = vec3(0.43, 0.42, 0.39);

    vec3 lowland = mix(forest, scrub, smoothstep(0.48, 0.72, dryness));
    vec3 albedo = mix(sand, lowland, above_sea);
    albedo = mix(albedo, soil, coast);
    albedo = mix(albedo, rock, mountain);

    float snow = smoothstep(0.74, 0.96, latitude + h * 0.35);
    albedo = mix(albedo, vec3(0.91, 0.93, 0.95), snow);

    float ndotl = max(dot(n, l), 0.0);
    vec3 half_vec = normalize(l + v);
    float spec = pow(max(dot(n, half_vec), 0.0), 96.0) * ndotl * 0.03;

    vec3 color = albedo * ndotl + vec3(spec);
    fragColor = vec4(max(color, 0.0), 1.0);
}
"""

PLANET_WATER_VERTEX_SHADER = """
#version 460 core

uniform mat4 u_view_proj;
uniform mat4 u_model;
uniform float u_water_level;

layout (location = 0) in vec3 in_pos;
layout (location = 1) in vec3 in_normal;
layout (location = 2) in vec2 in_uv;

out vec3 v_world_pos;
out vec3 v_base_n;
out vec2 v_uv;

void main() {
    vec3 base_n = normalize(in_pos + in_normal * 1e-7);
    vec3 local_pos = base_n * (u_water_level + 0.00045);
    vec4 world_pos = u_model * vec4(local_pos, 1.0);

    v_world_pos = world_pos.xyz;
    v_base_n = base_n;
    v_uv = in_uv;

    gl_Position = u_view_proj * world_pos;
}
"""

PLANET_WATER_FRAGMENT_SHADER = """
#version 460 core

uniform mat4 u_model;
uniform vec3 u_sun_dir;
uniform vec3 u_camera_pos;
uniform float u_time;
uniform float u_height_scale;

in vec3 v_world_pos;
in vec3 v_base_n;
in vec2 v_uv;

out vec4 fragColor;

const float PI = 3.14159265359;

float hash13(vec3 p) {
    p = fract(p * 0.3183099 + 0.1);
    p *= 17.0;
    return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
}

float noise3(vec3 p) {
    vec3 i = floor(p);
    vec3 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);

    float n000 = hash13(i + vec3(0.0, 0.0, 0.0));
    float n100 = hash13(i + vec3(1.0, 0.0, 0.0));
    float n010 = hash13(i + vec3(0.0, 1.0, 0.0));
    float n110 = hash13(i + vec3(1.0, 1.0, 0.0));
    float n001 = hash13(i + vec3(0.0, 0.0, 1.0));
    float n101 = hash13(i + vec3(1.0, 0.0, 1.0));
    float n011 = hash13(i + vec3(0.0, 1.0, 1.0));
    float n111 = hash13(i + vec3(1.0, 1.0, 1.0));

    float nx00 = mix(n000, n100, f.x);
    float nx10 = mix(n010, n110, f.x);
    float nx01 = mix(n001, n101, f.x);
    float nx11 = mix(n011, n111, f.x);
    float nxy0 = mix(nx00, nx10, f.y);
    float nxy1 = mix(nx01, nx11, f.y);
    return mix(nxy0, nxy1, f.z);
}

float fbm(vec3 p) {
    float v = 0.0;
    float a = 0.5;
    for (int i = 0; i < 5; i++) {
        v += a * noise3(p);
        p = p * 2.03 + vec3(17.1, 31.7, 11.3);
        a *= 0.5;
    }
    return v;
}

float terrain_height(vec3 n) {
    float continents = fbm(n * 2.4);
    float mountain_mask = smoothstep(0.50, 0.76, continents);
    float mountain = fbm(n * 9.0) * mountain_mask;
    float detail = fbm(n * 26.0) * 0.14;

    float h = (continents - 0.52) * 1.4 + mountain * 0.95 + detail - 0.08;
    return clamp(h, -0.55, 1.2);
}

vec3 orthogonal(vec3 n) {
    return normalize(
        abs(n.z) < 0.999 ? cross(n, vec3(0.0, 0.0, 1.0)) : cross(n, vec3(0.0, 1.0, 0.0))
    );
}

float wave_height(vec3 n, float time_s) {
    float lon = atan(n.z, n.x);
    float lat = asin(clamp(n.y, -1.0, 1.0));
    vec2 uv = vec2(lon, lat);

    float p1 = sin(dot(uv, vec2(21.0, -16.0)) + time_s * 1.8);
    float p2 = sin(dot(uv, vec2(-37.0, 25.0)) - time_s * 1.2);
    float p3 = sin(dot(uv, vec2(77.0, 63.0)) + time_s * 2.7);
    float n1 = fbm(n * 80.0 + vec3(0.0, time_s * 0.30, 0.0));
    float n2 = fbm(n * 170.0 + vec3(time_s * 0.75, 0.0, -time_s * 0.4));

    return p1 * 0.35 + p2 * 0.22 + p3 * 0.10 + (n1 - 0.5) * 0.55 + (n2 - 0.5) * 0.28;
}

void main() {
    vec3 n0 = normalize(v_base_n);
    vec3 t = orthogonal(n0);
    vec3 b = normalize(cross(n0, t));

    float time_s = u_time * 0.22;
    float eps = 0.0012;

    float w0 = wave_height(n0, time_s);
    float wt = wave_height(normalize(n0 + t * eps), time_s);
    float wb = wave_height(normalize(n0 + b * eps), time_s);

    float wave_amp = 0.048 + sin(v_uv.x * 18.0 + v_uv.y * 15.0) * 0.003;
    vec3 n_local = normalize(
        n0 + t * (w0 - wt) * wave_amp + b * (w0 - wb) * wave_amp
    );
    vec3 n = normalize(mat3(u_model) * n_local);

    vec3 v = normalize(u_camera_pos - v_world_pos);
    vec3 l = normalize(u_sun_dir);
    vec3 h = normalize(l + v);

    float ndotl = max(dot(n, l), 0.0);
    float ndotv = max(dot(n, v), 0.0);
    float ndoth = max(dot(n, h), 0.0);
    float vdoth = max(dot(v, h), 0.0);

    float roughness = mix(0.03, 0.10, clamp(abs(w0), 0.0, 1.0));
    float alpha = roughness * roughness;
    float alpha2 = alpha * alpha;
    float denom = ndoth * ndoth * (alpha2 - 1.0) + 1.0;
    float D = alpha2 / max(PI * denom * denom, 1e-6);

    float k = (roughness + 1.0) * (roughness + 1.0) / 8.0;
    float Gv = ndotv / max(ndotv * (1.0 - k) + k, 1e-6);
    float Gl = ndotl / max(ndotl * (1.0 - k) + k, 1e-6);
    float G = Gv * Gl;

    float F0 = 0.0204;
    float F = F0 + (1.0 - F0) * pow(1.0 - vdoth, 5.0);
    float specular = (D * G * F) / max(4.0 * ndotv * ndotl, 1e-6);

    float terrain_h = terrain_height(n0) * u_height_scale;
    float depth = clamp((-terrain_h) / max(u_height_scale * 0.9, 1e-6), 0.0, 1.0);
    vec3 shallow = vec3(0.07, 0.29, 0.36);
    vec3 deep = vec3(0.01, 0.08, 0.16);
    vec3 body = mix(shallow, deep, depth);

    vec3 reflected_sky = vec3(0.02, 0.05, 0.11);
    vec3 subsurface = body * (0.16 + 0.84 * ndotl);
    vec3 fresnel_mix = mix(subsurface, reflected_sky, F);

    float sun_glitter = pow(max(dot(reflect(-l, n), v), 0.0), 550.0) * 1.8;
    vec3 color = fresnel_mix + vec3(specular * 4.4 + sun_glitter);

    fragColor = vec4(max(color, 0.0), 1.0);
}
"""

ATMOSPHERE_VERTEX_SHADER = """
#version 460 core

layout (location = 0) in vec2 in_pos;

out vec2 v_uv;

void main() {
    v_uv = in_pos * 0.5 + 0.5;
    gl_Position = vec4(in_pos, 0.0, 1.0);
}
"""

ATMOSPHERE_FRAGMENT_SHADER = """
#version 460 core

const float PI = 3.14159265359;
const int VIEW_SAMPLES = 40;
const int LIGHT_SAMPLES = 20;

uniform sampler2D u_scene_color;
uniform sampler2D u_scene_depth;

uniform mat4 u_inv_view_proj;
uniform vec3 u_camera_pos;

uniform vec3 u_planet_center;
uniform float u_planet_radius;
uniform float u_atmosphere_radius;

uniform vec3 u_beta_rayleigh;
uniform vec3 u_beta_mie;
uniform float u_rayleigh_scale_height;
uniform float u_mie_scale_height;
uniform float u_mie_g;

uniform vec3 u_sun_dir;
uniform float u_sun_intensity;
uniform vec3 u_space_color;

in vec2 v_uv;
out vec4 fragColor;

struct ScatterResult {
    vec3 inscatter;
    vec3 transmittance;
};

float hash12(vec2 p) {
    vec3 p3 = fract(vec3(p.xyx) * 0.1031);
    p3 += dot(p3, p3.yzx + 33.33);
    return fract((p3.x + p3.y) * p3.z);
}

vec2 hash22(vec2 p) {
    return vec2(
        hash12(p + vec2(17.13, 11.97)),
        hash12(p + vec2(41.71, 29.53))
    );
}

vec3 star_layer(vec2 uv, float scale, float threshold, float seed) {
    vec2 grid = uv * scale;
    vec2 cell = floor(grid);
    vec2 f = fract(grid) - 0.5;

    float presence = hash12(cell + vec2(seed, seed * 1.37));
    if (presence < threshold) {
        return vec3(0.0);
    }

    vec2 jitter = hash22(cell + vec2(seed * 2.17, seed * 0.91)) - 0.5;
    float d = length(f - jitter * 0.7);

    float sharpness = mix(45.0, 80.0, hash12(cell + vec2(seed * 3.11, 2.0)));
    float core = exp(-d * sharpness);
    float halo = exp(-d * 8.0) * 0.12;

    float brightness = (presence - threshold) / max(1.0 - threshold, 1e-4);
    brightness = pow(brightness, 2.2);

    float color_pick = hash12(cell + vec2(seed * 5.53, seed * 7.91));
    vec3 cool = vec3(0.68, 0.76, 1.0);
    vec3 warm = vec3(1.0, 0.84, 0.70);
    vec3 neutral = vec3(0.94, 0.95, 1.0);
    vec3 tint = mix(cool, warm, color_pick);
    tint = mix(tint, neutral, 0.35);

    return tint * (core + halo) * brightness * 0.55;
}

vec3 starfield(vec3 rd) {
    float lon = atan(rd.z, rd.x) / (2.0 * PI) + 0.5;
    float lat = asin(clamp(rd.y, -1.0, 1.0)) / PI + 0.5;
    vec2 uv = vec2(lon, lat);

    vec3 stars = vec3(0.0);
    stars += star_layer(uv, 480.0, 0.9972, 13.1);
    stars += star_layer(uv, 900.0, 0.9986, 29.7);
    return stars;
}

bool ray_sphere(
    vec3 ro,
    vec3 rd,
    vec3 sphere_center,
    float radius,
    out float t0,
    out float t1
) {
    vec3 oc = ro - sphere_center;
    float b = dot(oc, rd);
    float c = dot(oc, oc) - radius * radius;
    float h = b * b - c;
    if (h < 0.0) {
        t0 = 0.0;
        t1 = 0.0;
        return false;
    }
    h = sqrt(h);
    t0 = -b - h;
    t1 = -b + h;
    return true;
}

vec2 sample_density(vec3 world_pos) {
    float altitude = max(length(world_pos - u_planet_center) - u_planet_radius, 0.0);
    float rayleigh = exp(-altitude / u_rayleigh_scale_height);
    float mie = exp(-altitude / u_mie_scale_height);
    return vec2(rayleigh, mie);
}

vec2 march_optical_depth(
    vec3 ro,
    vec3 rd,
    float t_start,
    float t_end,
    float jitter
) {
    float segment_length = max(t_end - t_start, 0.0);
    if (segment_length <= 0.0) {
        return vec2(0.0);
    }

    float step_len = segment_length / float(LIGHT_SAMPLES);
    vec2 optical_depth = vec2(0.0);

    for (int i = 0; i < LIGHT_SAMPLES; i++) {
        float t = t_start + (float(i) + jitter) * step_len;
        vec3 sample_pos = ro + rd * t;
        float altitude = length(sample_pos - u_planet_center) - u_planet_radius;
        if (altitude < 0.0) {
            break;
        }

        optical_depth += sample_density(sample_pos) * step_len;
    }

    return optical_depth;
}

float phase_rayleigh(float mu) {
    return 3.0 / (16.0 * PI) * (1.0 + mu * mu);
}

float phase_mie(float mu, float g) {
    float g2 = g * g;
    float denom = pow(max(1.0 + g2 - 2.0 * g * mu, 1e-4), 1.5);
    return (3.0 / (8.0 * PI)) * ((1.0 - g2) * (1.0 + mu * mu)) / ((2.0 + g2) * denom);
}

ScatterResult integrate_scattering(
    vec3 ro,
    vec3 rd,
    float t_start,
    float t_end,
    float jitter
) {
    ScatterResult result;
    result.inscatter = vec3(0.0);
    result.transmittance = vec3(1.0);

    float segment_length = max(t_end - t_start, 0.0);
    if (segment_length <= 0.0) {
        return result;
    }

    float step_len = segment_length / float(VIEW_SAMPLES);
    vec2 view_optical_depth = vec2(0.0);
    float mu = dot(-rd, u_sun_dir);

    float rayleigh_phase = phase_rayleigh(mu);
    float mie_phase = phase_mie(mu, u_mie_g);

    for (int i = 0; i < VIEW_SAMPLES; i++) {
        float t = t_start + (float(i) + jitter) * step_len;
        vec3 sample_pos = ro + rd * t;

        float altitude = length(sample_pos - u_planet_center) - u_planet_radius;
        if (altitude < 0.0) {
            break;
        }

        vec2 density = sample_density(sample_pos);
        view_optical_depth += density * step_len;

        float sun_t0;
        float sun_t1;
        if (!ray_sphere(
            sample_pos,
            u_sun_dir,
            u_planet_center,
            u_atmosphere_radius,
            sun_t0,
            sun_t1
        )) {
            continue;
        }

        float blocked_t0;
        float blocked_t1;
        if (
            ray_sphere(
                sample_pos + u_sun_dir * 0.01,
                u_sun_dir,
                u_planet_center,
                u_planet_radius,
                blocked_t0,
                blocked_t1
            )
            && blocked_t1 > 0.0
        ) {
            continue;
        }

        vec2 sun_optical_depth = march_optical_depth(
            sample_pos,
            u_sun_dir,
            max(sun_t0, 0.0),
            sun_t1,
            fract(jitter + 0.37)
        );

        vec3 tau = u_beta_rayleigh * (view_optical_depth.x + sun_optical_depth.x)
            + u_beta_mie * (view_optical_depth.y + sun_optical_depth.y);
        vec3 attenuation = exp(-tau);

        vec3 scatter_step = density.x * u_beta_rayleigh * rayleigh_phase
            + density.y * u_beta_mie * mie_phase;
        result.inscatter += attenuation * scatter_step * step_len;
    }

    vec3 total_tau = u_beta_rayleigh * view_optical_depth.x
        + u_beta_mie * view_optical_depth.y;
    result.transmittance = exp(-total_tau);
    return result;
}

void main() {
    vec2 ndc = v_uv * 2.0 - 1.0;
    vec4 far_point = u_inv_view_proj * vec4(ndc, 1.0, 1.0);
    far_point /= far_point.w;

    vec3 ro = u_camera_pos;
    vec3 rd = normalize(far_point.xyz - ro);
    float planet_t0;
    float planet_t1;
    bool planet_blocks_view = ray_sphere(
            ro,
            rd,
            u_planet_center,
            u_planet_radius,
            planet_t0,
            planet_t1
        )
        && planet_t1 > 0.0;

    vec3 scene_color = texture(u_scene_color, v_uv).rgb;
    vec3 stars = starfield(rd);
    float depth = texture(u_scene_depth, v_uv).r;
    bool has_scene = depth < 0.999999;

    float atmo_t0;
    float atmo_t1;
    if (
        !ray_sphere(
            ro,
            rd,
            u_planet_center,
            u_atmosphere_radius,
            atmo_t0,
            atmo_t1
        )
    ) {
        float sun_visibility = (planet_blocks_view || has_scene) ? 0.0 : 1.0;
        float sun_disc = pow(max(dot(rd, u_sun_dir), 0.0), 2200.0);
        sun_disc *= sun_visibility;
        vec3 bg = has_scene
            ? scene_color
            : (scene_color + u_space_color + stars);
        bg += vec3(40.0, 25.0, 12.0) * sun_disc;
        fragColor = vec4(max(bg, 0.0), 1.0);
        return;
    }

    float t_start = max(atmo_t0, 0.0);
    float t_end = atmo_t1;

    if (has_scene) {
        vec4 scene_world_h = u_inv_view_proj * vec4(ndc, depth * 2.0 - 1.0, 1.0);
        scene_world_h /= scene_world_h.w;
        float t_scene = length(scene_world_h.xyz - ro);
        t_end = min(t_end, t_scene);
    }

    if (t_end <= t_start) {
        fragColor = vec4(scene_color, 1.0);
        return;
    }

    float jitter = hash12(v_uv * vec2(1919.0, 1079.0));
    ScatterResult scatter = integrate_scattering(ro, rd, t_start, t_end, jitter);

    vec3 base = has_scene
        ? scene_color
        : (scene_color + u_space_color + stars);
    vec3 color = base * scatter.transmittance + scatter.inscatter * u_sun_intensity;

    float sun_visibility = (planet_blocks_view || has_scene) ? 0.0 : 1.0;
    float sun_disc = pow(max(dot(rd, u_sun_dir), 0.0), 2200.0);
    color += vec3(40.0, 25.0, 12.0) * sun_disc * scatter.transmittance * sun_visibility;

    fragColor = vec4(max(color, 0.0), 1.0);
}
"""


def _sun_direction(time_s: float) -> tuple[float, float, float]:
    _ = time_s
    sun_dir = np.array([0.94, 0.32, 0.12], dtype="f4")
    sun_dir /= np.linalg.norm(sun_dir)
    return (float(sun_dir[0]), float(sun_dir[1]), float(sun_dir[2]))


@dataclass
class PlanetTerrainPass(RenderPass):
    target: Optional[ResourceId] = None

    _program: moderngl.Program | None = None
    _asset_server: AssetServer | None = None
    _mesh_handle: AssetHandle | None = None
    _model_matrix: np.ndarray | None = None

    def build(self) -> PassBuildInfo:
        writes = [PassResourceUse(self.target, "write")] if self.target else []
        return PassBuildInfo(pass_id=self.pass_id, reads=[], writes=writes)

    def on_compile(
        self, ctx: moderngl.Context, services: RenderServices
    ) -> None:
        self._asset_server = services.gpu_resources.asset_server
        self._mesh_handle = self._asset_server.load(DefaultMeshes.SPHERE)
        self._program = ctx.program(
            vertex_shader=PLANET_TERRAIN_VERTEX_SHADER,
            fragment_shader=PLANET_TERRAIN_FRAGMENT_SHADER,
        )

        model = np.eye(4, dtype="f4")
        model[0, 0] = PLANET_RADIUS
        model[1, 1] = PLANET_RADIUS
        model[2, 2] = PLANET_RADIUS
        self._model_matrix = model

    def on_destroy(self) -> None:
        if self._program:
            self._program.release()
            self._program = None

    def execute(self, ctx: PassExecutionContext) -> None:
        if (
            not self._program
            or not self._asset_server
            or not self._mesh_handle
            or self._model_matrix is None
        ):
            return

        if self.target:
            ctx.graph_resources[self.target].use()
        else:
            ctx.gl.screen.use()

        ctx.gl.enable(moderngl.DEPTH_TEST | moderngl.CULL_FACE)
        ctx.gl.disable(moderngl.BLEND)

        gpu_mesh = ctx.gpu_resources.get_mesh(self._mesh_handle.id)
        if not gpu_mesh:
            return

        set_uniform(
            self._program,
            "u_view_proj",
            pack_mat4(ctx.frame.camera.view_proj.T),
        )
        set_uniform(self._program, "u_model", pack_mat4(self._model_matrix.T))
        set_uniform(self._program, "u_height_scale", TERRAIN_HEIGHT_SCALE)
        set_uniform(self._program, "u_sun_dir", _sun_direction(ctx.frame.time))
        set_uniform(
            self._program,
            "u_camera_pos",
            tuple(float(v) for v in ctx.frame.camera.position),
        )

        vao = gpu_mesh.get_default_vao(self._program)
        vao.render()


@dataclass
class PlanetWaterPass(RenderPass):
    target: Optional[ResourceId] = None

    _program: moderngl.Program | None = None
    _asset_server: AssetServer | None = None
    _mesh_handle: AssetHandle | None = None
    _model_matrix: np.ndarray | None = None

    def build(self) -> PassBuildInfo:
        writes = [PassResourceUse(self.target, "write")] if self.target else []
        return PassBuildInfo(pass_id=self.pass_id, reads=[], writes=writes)

    def on_compile(
        self, ctx: moderngl.Context, services: RenderServices
    ) -> None:
        self._asset_server = services.gpu_resources.asset_server
        self._mesh_handle = self._asset_server.load(DefaultMeshes.SPHERE)
        self._program = ctx.program(
            vertex_shader=PLANET_WATER_VERTEX_SHADER,
            fragment_shader=PLANET_WATER_FRAGMENT_SHADER,
        )

        model = np.eye(4, dtype="f4")
        model[0, 0] = PLANET_RADIUS
        model[1, 1] = PLANET_RADIUS
        model[2, 2] = PLANET_RADIUS
        self._model_matrix = model

    def on_destroy(self) -> None:
        if self._program:
            self._program.release()
            self._program = None

    def execute(self, ctx: PassExecutionContext) -> None:
        if (
            not self._program
            or not self._asset_server
            or not self._mesh_handle
            or self._model_matrix is None
        ):
            return

        if self.target:
            ctx.graph_resources[self.target].use()
        else:
            ctx.gl.screen.use()

        ctx.gl.enable(moderngl.DEPTH_TEST | moderngl.CULL_FACE)
        ctx.gl.disable(moderngl.BLEND)

        gpu_mesh = ctx.gpu_resources.get_mesh(self._mesh_handle.id)
        if not gpu_mesh:
            return

        set_uniform(
            self._program,
            "u_view_proj",
            pack_mat4(ctx.frame.camera.view_proj.T),
        )
        set_uniform(self._program, "u_model", pack_mat4(self._model_matrix.T))
        set_uniform(self._program, "u_water_level", WATER_LEVEL)
        set_uniform(self._program, "u_time", ctx.frame.time)
        set_uniform(self._program, "u_height_scale", TERRAIN_HEIGHT_SCALE)
        set_uniform(self._program, "u_sun_dir", _sun_direction(ctx.frame.time))
        set_uniform(
            self._program,
            "u_camera_pos",
            tuple(float(v) for v in ctx.frame.camera.position),
        )

        vao = gpu_mesh.get_default_vao(self._program)
        vao.render()


@dataclass
class PlanetAtmospherePass(RenderPass):
    scene_color: ResourceId
    scene_depth: ResourceId
    target: Optional[ResourceId] = None

    _program: moderngl.Program | None = None
    _triangle_buffer: moderngl.Buffer | None = None
    _vao: moderngl.VertexArray | None = None

    def build(self) -> PassBuildInfo:
        reads = [
            PassResourceUse(self.scene_color, "read"),
            PassResourceUse(self.scene_depth, "read"),
        ]
        writes = [PassResourceUse(self.target, "write")] if self.target else []
        return PassBuildInfo(pass_id=self.pass_id, reads=reads, writes=writes)

    def on_compile(
        self, ctx: moderngl.Context, services: RenderServices
    ) -> None:
        self._program = ctx.program(
            vertex_shader=ATMOSPHERE_VERTEX_SHADER,
            fragment_shader=ATMOSPHERE_FRAGMENT_SHADER,
        )
        self._triangle_buffer = create_fullscreen_triangle(ctx)

    def on_destroy(self) -> None:
        if self._vao:
            self._vao.release()
            self._vao = None
        if self._triangle_buffer:
            self._triangle_buffer.release()
            self._triangle_buffer = None
        if self._program:
            self._program.release()
            self._program = None

    def execute(self, ctx: PassExecutionContext) -> None:
        if not self._program or not self._triangle_buffer:
            return

        if not self._vao:
            self._vao = ctx.gl.vertex_array(
                self._program,
                [(self._triangle_buffer, "2f", "in_pos")],
            )

        if self.target:
            ctx.graph_resources[self.target].use()
        else:
            ctx.gl.screen.use()

        ctx.gl.disable(
            moderngl.DEPTH_TEST | moderngl.CULL_FACE | moderngl.BLEND
        )

        inv_view_proj = np.linalg.inv(ctx.frame.camera.view_proj).astype("f4")

        scene_color = ctx.graph_resources[self.scene_color]
        scene_depth = ctx.graph_resources[self.scene_depth]
        scene_color.use(location=0)
        scene_depth.use(location=1)

        set_uniform(self._program, "u_scene_color", 0)
        set_uniform(self._program, "u_scene_depth", 1)
        set_uniform(
            self._program,
            "u_inv_view_proj",
            pack_mat4(inv_view_proj.T),
        )
        set_uniform(
            self._program,
            "u_camera_pos",
            tuple(float(v) for v in ctx.frame.camera.position),
        )
        set_uniform(self._program, "u_planet_center", (0.0, 0.0, 0.0))
        set_uniform(self._program, "u_planet_radius", PLANET_RADIUS)
        set_uniform(self._program, "u_atmosphere_radius", ATMOSPHERE_RADIUS)
        set_uniform(
            self._program,
            "u_beta_rayleigh",
            (0.0308, 0.0719, 0.1757),
        )
        set_uniform(self._program, "u_beta_mie", (0.021, 0.021, 0.021))
        set_uniform(self._program, "u_rayleigh_scale_height", 1.5068)
        set_uniform(self._program, "u_mie_scale_height", 0.2260)
        set_uniform(self._program, "u_mie_g", 0.76)
        set_uniform(self._program, "u_sun_dir", _sun_direction(ctx.frame.time))
        set_uniform(self._program, "u_sun_intensity", 40.0)
        set_uniform(self._program, "u_space_color", (0.0, 0.0, 0.0))

        self._vao.render(mode=moderngl.TRIANGLES)


def build_atmosphere_pipeline(builder: RenderGraphBuilder) -> None:
    builder.define_texture(
        ResourceId("surface_hdr"),
        desc=TextureDesc(
            components=4,
            dtype="f2",
        ),
    )

    builder.define_texture(
        ResourceId("composite_hdr"),
        desc=TextureDesc(
            components=4,
            dtype="f2",
        ),
    )

    builder.define_texture(
        ResourceId("depth_stencil"),
        desc=TextureDesc(
            components=1,
            dtype="f4",
            is_depth=True,
        ),
    )

    builder.define_framebuffer(
        ResourceId("surface_fbo"),
        FramebufferDesc(
            color_attachments=[ResourceId("surface_hdr")],
            depth_attachment=ResourceId("depth_stencil"),
        ),
    )

    builder.define_framebuffer(
        ResourceId("composite_fbo"),
        FramebufferDesc(
            color_attachments=[ResourceId("composite_hdr")],
            depth_attachment=None,
        ),
    )

    builder.add_pass(
        ClearPass(
            pass_id=PassId("clear_surface"),
            target=ResourceId("surface_fbo"),
            color=(0.0, 0.0, 0.0, 1.0),
        )
    )

    builder.add_pass(
        PlanetTerrainPass(
            pass_id=PassId("planet_terrain"),
            target=ResourceId("surface_fbo"),
        )
    )

    builder.add_pass(
        PlanetWaterPass(
            pass_id=PassId("planet_water"),
            target=ResourceId("surface_fbo"),
        )
    )

    builder.add_pass(
        PlanetAtmospherePass(
            pass_id=PassId("planet_atmosphere"),
            scene_color=ResourceId("surface_hdr"),
            scene_depth=ResourceId("depth_stencil"),
            target=ResourceId("composite_fbo"),
        )
    )

    builder.add_pass(
        TonemapPass(
            pass_id=PassId("tonemap"),
            input_texture=ResourceId("composite_hdr"),
            target=None,
        )
    )
