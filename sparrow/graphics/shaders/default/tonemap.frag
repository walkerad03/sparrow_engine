#version 460 core

in vec2 v_uv;
out vec4 frag_color;

uniform sampler2D u_hdr;

vec3 tonemap_reinhard(vec3 x) {
    return x / (1.0 + x);
}

mat3 ACESInputMat =
{
    {0.59719, 0.35458, 0.04823},
    {0.07600, 0.90834, 0.01566},
    {0.02840, 0.13383, 0.83777}
};

mat3 ACESOutputMat =
{
    { 1.60475, -0.53108, -0.07367},
    {-0.10208,  1.10813, -0.00605},
    {-0.00327, -0.07276,  1.07602}
};

vec3 RRTAndODTFit(vec3 v)
{
    vec3 a = v * (v + 0.0245786f) - 0.000090537f;
    vec3 b = v * (0.983729f * v + 0.4329510f) + 0.238081f;
    return a / b;
}

vec3 tonemap_aces(vec3 x) {
    x = ACESInputMat * x;
    x = RRTAndODTFit(x);
    x = ACESOutputMat * x;
    return clamp(x, 0.0, 1.0);
}


void main() {
    vec3 hdr = texture(u_hdr, v_uv).rgb;

    float maxRadiance = 1e4;
    float lum = dot(hdr, vec3(0.2126, 0.7152, 0.0722));
    
    if (lum > maxRadiance) {
        hdr *= maxRadiance / lum;
    }

    vec3 exposed = hdr * 32.0;

    vec3 mapped = tonemap_reinhard(exposed);

    mapped = max(mapped, vec3(0.0));
    mapped = pow(mapped, vec3(1.0 / 2.2));

    frag_color = vec4(mapped, 1.0);
}
