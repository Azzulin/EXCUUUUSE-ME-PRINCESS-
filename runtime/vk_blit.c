// The present's picture into the swapchain image (gfx_present.c present_image): one draw over the picture's rectangle
// that reads the source through an image view, in place of vkCmdBlitImage. A view picks the format the source is read
// as, which a blit cannot: the game's window texture is RGBA8_SRGB (NVN 0x38) and the Switch sends its bytes to the
// display as they are, so the present reads it through its UNORM twin and writes those bytes into the UNORM swapchain
// (the blit decoded sRGB to linear and wrote the linear values: a darker, oversaturated window). The filter is the
// blit's VK_FILTER_LINEAR at the same source position for each pixel centre, texel for texel when the sizes match
// (shaders/present_blit.frag). The bars beside or above and below the picture are the pass's clear to black. Cost: the
// blit's, one read of the source and one write of the swapchain image.
//
// The source view of slot s is destroyed when slot s records again (present_image has waited for that slot's fence).
// The pipeline is made for the swapchain's format, again when that changes.
#include "vk.h"

#include <string.h>

#include "hdr_fullscreen_spv.h"
#include "host.h"
#include "present_blit_spv.h"

#define SLOTS 8

static struct {
    int tried, ok, failed;
    PFN_vkCmdPushDescriptorSetKHR push;
    VkDescriptorSetLayout dsl;
    VkPipelineLayout layout;
    VkSampler sampler;
    VkPipeline pipe;               // for pipe_fmt
    VkFormat pipe_fmt;
    VkImageView src_view[SLOTS];   // the source view each slot's last frame read
} B;

static int init(VkCtx *c) {
    B.tried = 1;
    B.push = (PFN_vkCmdPushDescriptorSetKHR)vkGetDeviceProcAddr(c->device, "vkCmdPushDescriptorSetKHR");
    VkDescriptorSetLayoutBinding b = {.binding = 0, .descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER,
                                      .descriptorCount = 1, .stageFlags = VK_SHADER_STAGE_FRAGMENT_BIT};
    VkDescriptorSetLayoutCreateInfo dci = {.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO,
                                           .flags = VK_DESCRIPTOR_SET_LAYOUT_CREATE_PUSH_DESCRIPTOR_BIT_KHR,
                                           .bindingCount = 1, .pBindings = &b};
    VkPushConstantRange pr = {VK_SHADER_STAGE_FRAGMENT_BIT, 0, 48};
    VkPipelineLayoutCreateInfo li = {.sType = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO, .setLayoutCount = 1,
                                     .pSetLayouts = &B.dsl, .pushConstantRangeCount = 1, .pPushConstantRanges = &pr};
    VkSamplerCreateInfo si = {.sType = VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO, .magFilter = VK_FILTER_LINEAR,
                              .minFilter = VK_FILTER_LINEAR, .mipmapMode = VK_SAMPLER_MIPMAP_MODE_NEAREST,
                              .addressModeU = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE,
                              .addressModeV = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE,
                              .addressModeW = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE, .maxLod = 0};
    if (!B.push || vkCreateDescriptorSetLayout(c->device, &dci, NULL, &B.dsl) != VK_SUCCESS ||
        vkCreatePipelineLayout(c->device, &li, NULL, &B.layout) != VK_SUCCESS ||
        vkCreateSampler(c->device, &si, NULL, &B.sampler) != VK_SUCCESS) {
        rt_log("vk: the present's draw is off (no layout or sampler); the picture is blitted");
        return 0;
    }
    return B.ok = 1;
}

static VkShaderModule module(VkCtx *c, const uint32_t *code, size_t size) {
    VkShaderModuleCreateInfo mi = {.sType = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO, .codeSize = size, .pCode = code};
    VkShaderModule m = VK_NULL_HANDLE;
    return vkCreateShaderModule(c->device, &mi, NULL, &m) == VK_SUCCESS ? m : VK_NULL_HANDLE;
}

static int pipeline(VkCtx *c, VkFormat fmt) {
    if (B.pipe && B.pipe_fmt == fmt) return 1;
    if (B.failed) return 0;
    if (B.pipe) {   // another swapchain format: earlier presents may still use the old pipeline
        vk_queue_lock();
        vkDeviceWaitIdle(c->device);
        vk_queue_unlock();
        vkDestroyPipeline(c->device, B.pipe, NULL);
        B.pipe = VK_NULL_HANDLE;
    }
    VkShaderModule vs = module(c, hdr_fullscreen_spv, sizeof hdr_fullscreen_spv),
                   fs = module(c, present_blit_spv, sizeof present_blit_spv);
    VkPipelineShaderStageCreateInfo st[2] = {
        {.sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO, .stage = VK_SHADER_STAGE_VERTEX_BIT, .module = vs,
         .pName = "main"},
        {.sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO, .stage = VK_SHADER_STAGE_FRAGMENT_BIT, .module = fs,
         .pName = "main"}};
    VkPipelineVertexInputStateCreateInfo vi = {.sType = VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO};
    VkPipelineInputAssemblyStateCreateInfo ia = {.sType = VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO,
                                                 .topology = VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST};
    VkPipelineViewportStateCreateInfo vp = {.sType = VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO,
                                            .viewportCount = 1, .scissorCount = 1};
    VkPipelineRasterizationStateCreateInfo rs = {.sType = VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO,
                                                 .polygonMode = VK_POLYGON_MODE_FILL, .cullMode = VK_CULL_MODE_NONE,
                                                 .lineWidth = 1.0f};
    VkPipelineMultisampleStateCreateInfo ms = {.sType = VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO,
                                               .rasterizationSamples = VK_SAMPLE_COUNT_1_BIT};
    VkPipelineColorBlendAttachmentState ba = {.colorWriteMask = 0xf};
    VkPipelineColorBlendStateCreateInfo cb = {.sType = VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO,
                                              .attachmentCount = 1, .pAttachments = &ba};
    VkDynamicState dyn[2] = {VK_DYNAMIC_STATE_VIEWPORT, VK_DYNAMIC_STATE_SCISSOR};
    VkPipelineDynamicStateCreateInfo ds = {.sType = VK_STRUCTURE_TYPE_PIPELINE_DYNAMIC_STATE_CREATE_INFO,
                                           .dynamicStateCount = 2, .pDynamicStates = dyn};
    VkPipelineRenderingCreateInfo ri = {.sType = VK_STRUCTURE_TYPE_PIPELINE_RENDERING_CREATE_INFO,
                                        .colorAttachmentCount = 1, .pColorAttachmentFormats = &fmt};
    VkGraphicsPipelineCreateInfo gi = {.sType = VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO, .pNext = &ri,
                                       .stageCount = 2, .pStages = st, .pVertexInputState = &vi,
                                       .pInputAssemblyState = &ia, .pViewportState = &vp, .pRasterizationState = &rs,
                                       .pMultisampleState = &ms, .pColorBlendState = &cb, .pDynamicState = &ds,
                                       .layout = B.layout};
    VkResult r = vs && fs ? vkCreateGraphicsPipelines(c->device, VK_NULL_HANDLE, 1, &gi, NULL, &B.pipe) : VK_ERROR_UNKNOWN;
    if (vs) vkDestroyShaderModule(c->device, vs, NULL);
    if (fs) vkDestroyShaderModule(c->device, fs, NULL);
    if (r != VK_SUCCESS) {
        B.pipe = VK_NULL_HANDLE;
        B.failed = 1;   // not tried again every frame
        rt_log("vk: the present's draw pipeline could not be created (%d); the picture is blitted (an sRGB picture "
               "then shows decoded)", (int)r);
        return 0;
    }
    B.pipe_fmt = fmt;
    rt_log("vk: the present draws the picture through a view (swapchain format %d)", (int)fmt);
    return 1;
}

static void barrier(VkCommandBuffer cb, VkImage img, VkImageLayout from, VkImageLayout to, VkPipelineStageFlags2 ss,
                    VkAccessFlags2 sa, VkPipelineStageFlags2 ds, VkAccessFlags2 da) {
    VkImageMemoryBarrier2 b = {.sType = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER_2, .srcStageMask = ss, .srcAccessMask = sa,
                               .dstStageMask = ds, .dstAccessMask = da, .oldLayout = from, .newLayout = to,
                               .srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED,
                               .dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED, .image = img,
                               .subresourceRange = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1}};
    VkDependencyInfo d = {.sType = VK_STRUCTURE_TYPE_DEPENDENCY_INFO, .imageMemoryBarrierCount = 1,
                          .pImageMemoryBarriers = &b};
    vkCmdPipelineBarrier2(cb, &d);
}

int vk_blit_record(VkCommandBuffer cb, unsigned slot, VkImage src, VkFormat fmt, int sw, int sh, const int crop[4],
                   VkImage dst, VkImageView dst_view, VkFormat dst_fmt, uint32_t dw, uint32_t dh, const int out[4]) {
    VkCtx *c = vk_ctx();
    if (!B.tried) init(c);
    if (!B.ok || !dst_view || sw <= 0 || sh <= 0 || out[2] <= 0 || out[3] <= 0 || !pipeline(c, dst_fmt)) return 0;
    slot %= SLOTS;
    if (B.src_view[slot]) vkDestroyImageView(c->device, B.src_view[slot], NULL);
    VkImageViewCreateInfo vi = {.sType = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO, .image = src,
                                .viewType = VK_IMAGE_VIEW_TYPE_2D, .format = fmt,
                                .subresourceRange = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1}};
    if (vkCreateImageView(c->device, &vi, NULL, &B.src_view[slot]) != VK_SUCCESS) {
        B.src_view[slot] = VK_NULL_HANDLE;
        return 0;
    }
    const VkPipelineStageFlags2 FS = VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT,
                                CA = VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT,
                                ALL = VK_PIPELINE_STAGE_2_ALL_COMMANDS_BIT;
    // the source's writes (the game's submissions, or the present's own compute passes) become visible to the draw;
    // the swapchain image's old content goes (the acquire semaphore is waited for at the attachment output stage)
    barrier(cb, src, VK_IMAGE_LAYOUT_GENERAL, VK_IMAGE_LAYOUT_GENERAL, ALL, VK_ACCESS_2_MEMORY_WRITE_BIT, FS,
            VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);
    barrier(cb, dst, VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL, CA, 0, CA,
            VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT);
    int bars = out[0] != 0 || out[1] != 0 || (uint32_t)out[2] != dw || (uint32_t)out[3] != dh;
    VkRenderingAttachmentInfo ca = {.sType = VK_STRUCTURE_TYPE_RENDERING_ATTACHMENT_INFO, .imageView = dst_view,
                                    .imageLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL,
                                    .loadOp = bars ? VK_ATTACHMENT_LOAD_OP_CLEAR : VK_ATTACHMENT_LOAD_OP_DONT_CARE,
                                    .storeOp = VK_ATTACHMENT_STORE_OP_STORE,
                                    .clearValue = {.color = {.float32 = {0, 0, 0, 1}}}};
    VkRenderingInfo ri = {.sType = VK_STRUCTURE_TYPE_RENDERING_INFO, .renderArea = {{0, 0}, {dw, dh}}, .layerCount = 1,
                          .colorAttachmentCount = 1, .pColorAttachments = &ca};
    vkCmdBeginRendering(cb, &ri);
    vkCmdBindPipeline(cb, VK_PIPELINE_BIND_POINT_GRAPHICS, B.pipe);
    VkViewport v = {(float)out[0], (float)out[1], (float)out[2], (float)out[3], 0, 1};
    VkRect2D s = {{out[0], out[1]}, {(uint32_t)out[2], (uint32_t)out[3]}};
    vkCmdSetViewport(cb, 0, 1, &v);
    vkCmdSetScissor(cb, 0, 1, &s);
    VkDescriptorImageInfo ii = {B.sampler, B.src_view[slot], VK_IMAGE_LAYOUT_GENERAL};
    VkWriteDescriptorSet wr = {.sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET, .dstBinding = 0, .descriptorCount = 1,
                               .descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, .pImageInfo = &ii};
    rec_push(B.push, cb, VK_PIPELINE_BIND_POINT_GRAPHICS, B.layout, 0, 1, &wr);
    struct { float crop[4], rect[4], inv_size[2]; int32_t fetch, pad; } pc = {
        {(float)crop[0], (float)crop[1], (float)crop[2], (float)crop[3]},
        {(float)out[0], (float)out[1], (float)out[2], (float)out[3]},
        {1.0f / (float)sw, 1.0f / (float)sh}, crop[2] == out[2] && crop[3] == out[3], 0};
    vkCmdPushConstants(cb, B.layout, VK_SHADER_STAGE_FRAGMENT_BIT, 0, sizeof pc, &pc);
    vkCmdDraw(cb, 3, 1, 0, 0);
    vkCmdEndRendering(cb);
    // later submissions that write the source wait for the draw's read
    barrier(cb, src, VK_IMAGE_LAYOUT_GENERAL, VK_IMAGE_LAYOUT_GENERAL, FS, 0, ALL, 0);
    return 1;
}

void vk_blit_release(void) {
    VkCtx *c = vk_ctx();
    if (!c || !B.tried) return;
    for (int i = 0; i < SLOTS; i++)
        if (B.src_view[i]) vkDestroyImageView(c->device, B.src_view[i], NULL);
    if (B.pipe) vkDestroyPipeline(c->device, B.pipe, NULL);
    if (B.sampler) vkDestroySampler(c->device, B.sampler, NULL);
    if (B.layout) vkDestroyPipelineLayout(c->device, B.layout, NULL);
    if (B.dsl) vkDestroyDescriptorSetLayout(c->device, B.dsl, NULL);
    memset(&B, 0, sizeof B);
}
