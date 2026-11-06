#version 450
// One triangle over the whole viewport, for hdr_ui.frag (runtime/vk_hdr.c vk_hdr_ui_compose) and present_blit.frag
// (runtime/vk_blit.c vk_blit_record, which reads gl_FragCoord instead of uv).
layout(location = 0) out vec2 uv;

void main() {
    uv = vec2((gl_VertexIndex << 1) & 2, gl_VertexIndex & 2);
    gl_Position = vec4(uv * 2.0 - 1.0, 0.0, 1.0);
}
