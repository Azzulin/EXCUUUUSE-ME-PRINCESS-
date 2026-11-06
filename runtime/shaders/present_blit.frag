#version 450
// The present's picture into the swapchain image (runtime/vk_blit.c vk_blit_record), with hdr_fullscreen.vert over the
// viewport, which is the picture's rectangle in the window. The source is read through the view the present picked (an
// sRGB window texture through its UNORM twin: the bytes the game wrote). Each pixel centre maps to the source position
// vkCmdBlitImage with VK_FILTER_LINEAR samples (crop corner + offset * crop size / rectangle size, texel centres at
// +0.5) and is filtered bilinearly; with the sizes equal it takes its texel as it is.
layout(location = 0) out vec4 color;
layout(binding = 0) uniform sampler2D src;
layout(push_constant) uniform P {
    vec4 crop;      // x, y, w, h of the source rectangle, in texels
    vec4 rect;      // x, y, w, h of the picture's rectangle in the swapchain image, in pixels
    vec2 inv_size;  // 1 / the source's size
    int fetch;      // 1: the two sizes are equal, texel for texel
} pc;

void main() {
    vec2 p = gl_FragCoord.xy - pc.rect.xy;   // the pixel centre inside the rectangle (x + 0.5, y + 0.5)
    if (pc.fetch != 0) {
        color = vec4(texelFetch(src, ivec2(pc.crop.xy + floor(p)), 0).rgb, 1.0);
        return;
    }
    vec2 s = pc.crop.xy + p * pc.crop.zw / pc.rect.zw;
    color = vec4(texture(src, s * pc.inv_size).rgb, 1.0);
}
