#version 460 core

out vec4 fragColor;

uniform vec4 u_base_color;
uniform vec3 u_light_color;
uniform vec3 u_light_pos;
uniform vec3 u_camera_pos;

in vec3 v_frag_pos;
in vec3 v_normal;

float ambientStrength = 0.1;
float specularStrength = 0.5;

void main() {

    vec3 ambient = ambientStrength * u_light_color;

    vec3 norm = normalize(v_normal);
    vec3 light_dir = normalize(u_light_pos - v_frag_pos);
    float diff = max(dot(norm, light_dir), 0.0);
    vec3 diffuse = diff * u_light_color;

    vec3 view_dir = normalize(u_camera_pos - v_frag_pos);
    vec3 reflect_dir = reflect(-light_dir, norm);
    float spec = pow(max(dot(view_dir, reflect_dir), 0.0), 32);
    vec3 specular = specularStrength * spec * u_light_color;

    vec3 result = (ambient + diffuse + specular) * u_base_color.rgb;
    fragColor = vec4(result, 1.0);
}
