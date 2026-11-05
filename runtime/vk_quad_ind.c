// Indirect quads: NVN's DrawArraysIndirect with NVN_DRAW_PRIMITIVE_QUADS, whose vertex count the GPU wrote. Vulkan has
// no quads and the count cannot be read on the CPU, so a compute dispatch (shaders/quad_indirect.comp) turns the
// game's record {count, instances, first, base instance} into a VkDrawIndexedIndirectCommand over a fixed index list
// {0,1,2, 0,2,3} + 4 k, the way nxnative does it for Metal (dm/games/01002B00111A2000/README.md, Rendering: Age of
// Calamity's GPU-driven effects are indirect quads). Our own code.
//
// Converted commands go to a ring of RING entries in host-visible memory; with at most a few frames in flight and far
// fewer indirect quad draws a frame than RING, an entry is not reused while the GPU still reads it.
#include <string.h>

#include "host.h"
#include "quad_indirect_spv.h"
#include "vk.h"
#include "vk_exec.h"

#define MAX_QUADS 65536u   // indices for this many quads: 1.5 MiB of uint32
#define RING 16384u        // converted commands kept
#define CMD_BYTES 32u      // a 20-byte VkDrawIndexedIndirectCommand, padded

static struct {
    int tried, ok;
    PFN_vkCmdPushDescriptorSetKHR push;
    VkDescriptorSetLayout dsl;
    VkPipelineLayout layout;
    VkPipeline pipe;
    VkBuffer index, ring;
    VmaAllocation index_alloc, ring_alloc;
    VkDeviceSize sbuf_align;
    uint32_t next;
} Q;

static int buffer(VkCtx *c, VkDeviceSize size, VkBufferUsageFlags usage, VkBuffer *b, VmaAllocation *a, void **map) {
    VkBufferCreateInfo bi = {.sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO, .size = size, .usage = usage};
    VmaAllocationCreateInfo ai = {.usage = VMA_MEMORY_USAGE_AUTO_PREFER_HOST,
                                  .flags = VMA_ALLOCATION_CREATE_HOST_ACCESS_RANDOM_BIT | VMA_ALLOCATION_CREATE_MAPPED_BIT};
    VmaAllocationInfo info;
    if (vmaCreateBuffer(c->vma, &bi, &ai, b, a, &info) != VK_SUCCESS || !info.pMappedData) return 0;
    if (map) *map = info.pMappedData;
    return 1;
}

static int init(void) {
    Q.tried = 1;
    VkCtx *c = vk_ctx();
    if (!c) return 0;
    VkPhysicalDeviceProperties pp;
    vkGetPhysicalDeviceProperties(c->phys, &pp);
    Q.sbuf_align = pp.limits.minStorageBufferOffsetAlignment ? pp.limits.minStorageBufferOffsetAlignment : 4;
    Q.push = (PFN_vkCmdPushDescriptorSetKHR)vkGetDeviceProcAddr(c->device, "vkCmdPushDescriptorSetKHR");
    VkDescriptorSetLayoutBinding b[2] = {
        {.binding = 0, .descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, .descriptorCount = 1,
         .stageFlags = VK_SHADER_STAGE_COMPUTE_BIT},
        {.binding = 1, .descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, .descriptorCount = 1,
         .stageFlags = VK_SHADER_STAGE_COMPUTE_BIT}};
    VkDescriptorSetLayoutCreateInfo dci = {.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO,
                                           .flags = VK_DESCRIPTOR_SET_LAYOUT_CREATE_PUSH_DESCRIPTOR_BIT_KHR,
                                           .bindingCount = 2, .pBindings = b};
    VkPushConstantRange pr = {VK_SHADER_STAGE_COMPUTE_BIT, 0, 16};
    VkShaderModuleCreateInfo mi = {.sType = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO,
                                   .codeSize = sizeof quad_indirect_spv, .pCode = quad_indirect_spv};
    VkShaderModule m = VK_NULL_HANDLE;
    if (!Q.push || vkCreateDescriptorSetLayout(c->device, &dci, NULL, &Q.dsl) != VK_SUCCESS) return 0;
    VkPipelineLayoutCreateInfo li = {.sType = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO, .setLayoutCount = 1,
                                     .pSetLayouts = &Q.dsl, .pushConstantRangeCount = 1, .pPushConstantRanges = &pr};
    if (vkCreatePipelineLayout(c->device, &li, NULL, &Q.layout) != VK_SUCCESS ||
        vkCreateShaderModule(c->device, &mi, NULL, &m) != VK_SUCCESS)
        return 0;
    VkComputePipelineCreateInfo ci = {.sType = VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO,
                                      .stage = {.sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,
                                                .stage = VK_SHADER_STAGE_COMPUTE_BIT, .module = m, .pName = "main"},
                                      .layout = Q.layout};
    VkResult r = vkCreateComputePipelines(c->device, VK_NULL_HANDLE, 1, &ci, NULL, &Q.pipe);
    vkDestroyShaderModule(c->device, m, NULL);
    if (r != VK_SUCCESS) return 0;
    uint32_t *ix;
    if (!buffer(c, MAX_QUADS * 6ull * 4, VK_BUFFER_USAGE_INDEX_BUFFER_BIT, &Q.index, &Q.index_alloc, (void **)&ix) ||
        !buffer(c, (VkDeviceSize)RING * CMD_BYTES, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_INDIRECT_BUFFER_BIT,
                &Q.ring, &Q.ring_alloc, NULL))
        return 0;
    static const uint32_t k[6] = {0, 1, 2, 0, 2, 3};
    for (uint32_t q = 0; q < MAX_QUADS; q++)
        for (int j = 0; j < 6; j++) ix[6 * q + j] = 4 * q + k[j];
    vmaFlushAllocation(c->vma, Q.index_alloc, 0, VK_WHOLE_SIZE);
    rt_log("vk: indirect quads converted on the GPU (up to %u quads a draw)", MAX_QUADS);
    return Q.ok = 1;
}

// Records into cb (outside a render pass) the conversion of the record at src into a ring entry, and hands back the
// command's buffer and offset and the quad index buffer. 0 when the converter is not available.
int vk_quad_ind_convert(VkCommandBuffer cb, const VkMemSpan *src, VkBuffer *cmd, VkDeviceSize *cmd_off, VkBuffer *index) {
    if (!Q.tried) init();
    if (!Q.ok) return 0;
    VkDeviceSize base = src->offset & ~(Q.sbuf_align - 1);
    uint32_t slot = Q.next++ % RING;
    VkDescriptorBufferInfo in = {src->buffer, base, src->offset - base + 16};
    VkDescriptorBufferInfo out = {Q.ring, (VkDeviceSize)slot * CMD_BYTES, CMD_BYTES};
    VkWriteDescriptorSet w[2] = {
        {.sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET, .dstBinding = 0, .descriptorCount = 1,
         .descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, .pBufferInfo = &in},
        {.sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET, .dstBinding = 1, .descriptorCount = 1,
         .descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, .pBufferInfo = &out}};
    uint32_t pc[4] = {(uint32_t)((src->offset - base) / 4), 0, MAX_QUADS, 0};
    vkCmdBindPipeline(cb, VK_PIPELINE_BIND_POINT_COMPUTE, Q.pipe);
    Q.push(cb, VK_PIPELINE_BIND_POINT_COMPUTE, Q.layout, 0, 2, w);
    vkCmdPushConstants(cb, Q.layout, VK_SHADER_STAGE_COMPUTE_BIT, 0, sizeof pc, pc);
    vkCmdDispatch(cb, 1, 1, 1);
    *cmd = Q.ring, *cmd_off = (VkDeviceSize)slot * CMD_BYTES, *index = Q.index;
    return 1;
}
