"""Vulkan runtime and GPU availability detection utilities."""
from __future__ import annotations

import ctypes
import os


def is_vulkan_supported() -> tuple[bool, str]:
    """Check if Vulkan runtime is available and has at least one physical device.

    Returns:
        tuple[bool, str]: (is_supported, description_or_reason)
    """
    if os.name != "nt":
        return False, "Plataforma não suportada para checagem rápida de Vulkan"

    try:
        vk = ctypes.CDLL("vulkan-1.dll")
    except Exception as e:
        return False, f"vulkan-1.dll não encontrada ou inacessível ({e})"

    class VkInstanceCreateInfo(ctypes.Structure):
        _fields_ = [
            ("sType", ctypes.c_int),
            ("pNext", ctypes.c_void_p),
            ("flags", ctypes.c_uint32),
            ("pApplicationInfo", ctypes.c_void_p),
            ("enabledLayerCount", ctypes.c_uint32),
            ("ppEnabledLayerNames", ctypes.c_void_p),
            ("enabledExtensionCount", ctypes.c_uint32),
            ("ppEnabledExtensionNames", ctypes.c_void_p),
        ]

    create_info = VkInstanceCreateInfo()
    create_info.sType = 1  # VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO
    instance = ctypes.c_void_p()

    try:
        vkCreateInstance = vk.vkCreateInstance
        vkCreateInstance.argtypes = [
            ctypes.POINTER(VkInstanceCreateInfo),
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        vkCreateInstance.restype = ctypes.c_int
        res = vkCreateInstance(ctypes.byref(create_info), None, ctypes.byref(instance))
        if res != 0:
            return False, f"Falha ao criar instância Vulkan (código {res})"

        device_count = ctypes.c_uint32(0)
        vkEnumeratePhysicalDevices = vk.vkEnumeratePhysicalDevices
        vkEnumeratePhysicalDevices.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.c_void_p,
        ]
        vkEnumeratePhysicalDevices.restype = ctypes.c_int
        enum_res = vkEnumeratePhysicalDevices(instance, ctypes.byref(device_count), None)

        vkDestroyInstance = getattr(vk, "vkDestroyInstance", None)
        if vkDestroyInstance:
            vkDestroyInstance.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
            vkDestroyInstance(instance, None)

        if enum_res == 0 and device_count.value > 0:
            return True, f"Vulkan ativo com {device_count.value} dispositivo(s) compatível(is)"
        return False, f"Nenhuma GPU compatível com Vulkan encontrada (dispositivos: {device_count.value})"
    except Exception as e:
        return False, f"Erro inesperado ao consultar Vulkan: {e}"
