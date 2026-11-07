// Taranis : la carte graphique de vtx, par Vulkan, sans aucune bibliothèque (ni crate, ni SDK : vulkan-1.dll, que le
// pilote installe, est chargée à l'exécution). Étape zéro, la sonde :
//   taranis                  la carte trouvée, puis le noyau de taranis_sonde.spv (écrit par taranis/spirv.py, le
//                            SPIR-V de vtx) lancé sur N fils ; chaque fil brasse son numéro en 64 tours ; le processeur
//                            refait le même brassage (un cœur, puis tous) : les mêmes mots, et les temps
//   taranis N                sur N fils (par défaut 2^24 : 16 777 216)
// Le calcul se fait dans la mémoire de la carte, puis une copie la ramène au processeur ; la carte chronomètre elle-même
// (les horodatages de Vulkan) son calcul et la copie, à part du lancement et de l'attente.
// Les structures et les nombres de Vulkan sont ceux de sa spécification (1.0) ; rien d'autre n'est supposé.
#![allow(non_snake_case, non_camel_case_types, clippy::upper_case_acronyms)]
use std::ffi::{c_char, c_void, CStr};
use std::ptr::{null, null_mut};

type Ptr = *mut c_void; // les objets « dispatchables » (instance, carte, appareil, file, commandes)
type H = u64; // les autres objets
type R = i32; // VkResult

const NOYAU: &[u8] = include_bytes!("../taranis_sonde.spv");
const TOURS: u32 = 64;
const LARGEUR: u32 = 64;

// ------------------------------------------------------------------ charger la bibliothèque Vulkan
#[cfg(windows)]
mod charge {
    use std::ffi::c_void;
    #[link(name = "kernel32")]
    extern "system" {
        fn LoadLibraryA(nom: *const u8) -> *mut c_void;
        fn GetProcAddress(m: *mut c_void, nom: *const u8) -> *mut c_void;
    }
    pub fn vk_get_instance_proc_addr() -> Option<*mut c_void> {
        unsafe {
            let m = LoadLibraryA(b"vulkan-1.dll\0".as_ptr());
            if m.is_null() {
                return None;
            }
            let f = GetProcAddress(m, b"vkGetInstanceProcAddr\0".as_ptr());
            if f.is_null() { None } else { Some(f) }
        }
    }
}
#[cfg(not(windows))]
mod charge {
    use std::ffi::c_void;
    extern "C" {
        fn dlopen(nom: *const u8, mode: i32) -> *mut c_void;
        fn dlsym(m: *mut c_void, nom: *const u8) -> *mut c_void;
    }
    pub fn vk_get_instance_proc_addr() -> Option<*mut c_void> {
        unsafe {
            let mut m = dlopen(b"libvulkan.so.1\0".as_ptr(), 2);
            if m.is_null() {
                m = dlopen(b"libvulkan.so\0".as_ptr(), 2);
            }
            if m.is_null() {
                return None;
            }
            let f = dlsym(m, b"vkGetInstanceProcAddr\0".as_ptr());
            if f.is_null() { None } else { Some(f) }
        }
    }
}

// ------------------------------------------------------------------ les structures de Vulkan (repr(C), comme en C)
#[repr(C)]
struct ApplicationInfo { sType: u32, pNext: *const c_void, pApplicationName: *const c_char, applicationVersion: u32,
    pEngineName: *const c_char, engineVersion: u32, apiVersion: u32 }
#[repr(C)]
struct InstanceCreateInfo { sType: u32, pNext: *const c_void, flags: u32, pApplicationInfo: *const ApplicationInfo,
    enabledLayerCount: u32, ppEnabledLayerNames: *const *const c_char, enabledExtensionCount: u32,
    ppEnabledExtensionNames: *const *const c_char }
#[repr(C)]
#[derive(Clone, Copy, Default)]
struct QueueFamilyProperties { queueFlags: u32, queueCount: u32, timestampValidBits: u32, w: u32, h: u32, d: u32 }
#[repr(C)]
struct DeviceQueueCreateInfo { sType: u32, pNext: *const c_void, flags: u32, queueFamilyIndex: u32, queueCount: u32,
    pQueuePriorities: *const f32 }
#[repr(C)]
struct DeviceCreateInfo { sType: u32, pNext: *const c_void, flags: u32, queueCreateInfoCount: u32,
    pQueueCreateInfos: *const DeviceQueueCreateInfo, enabledLayerCount: u32, ppEnabledLayerNames: *const *const c_char,
    enabledExtensionCount: u32, ppEnabledExtensionNames: *const *const c_char, pEnabledFeatures: *const c_void }
#[repr(C)]
struct BufferCreateInfo { sType: u32, pNext: *const c_void, flags: u32, size: u64, usage: u32, sharingMode: u32,
    queueFamilyIndexCount: u32, pQueueFamilyIndices: *const u32 }
#[repr(C)]
#[derive(Default)]
struct MemoryRequirements { size: u64, alignment: u64, memoryTypeBits: u32 }
#[repr(C)]
#[derive(Clone, Copy)]
struct MemoryType { propertyFlags: u32, heapIndex: u32 }
#[repr(C)]
#[derive(Clone, Copy)]
struct MemoryHeap { size: u64, flags: u32 }
#[repr(C)]
struct MemoryProperties { memoryTypeCount: u32, memoryTypes: [MemoryType; 32], memoryHeapCount: u32,
    memoryHeaps: [MemoryHeap; 16] }
#[repr(C)]
struct MemoryAllocateInfo { sType: u32, pNext: *const c_void, allocationSize: u64, memoryTypeIndex: u32 }
#[repr(C)]
struct ShaderModuleCreateInfo { sType: u32, pNext: *const c_void, flags: u32, codeSize: usize, pCode: *const u32 }
#[repr(C)]
struct DescriptorSetLayoutBinding { binding: u32, descriptorType: u32, descriptorCount: u32, stageFlags: u32,
    pImmutableSamplers: *const c_void }
#[repr(C)]
struct DescriptorSetLayoutCreateInfo { sType: u32, pNext: *const c_void, flags: u32, bindingCount: u32,
    pBindings: *const DescriptorSetLayoutBinding }
#[repr(C)]
struct PipelineLayoutCreateInfo { sType: u32, pNext: *const c_void, flags: u32, setLayoutCount: u32,
    pSetLayouts: *const H, pushConstantRangeCount: u32, pPushConstantRanges: *const c_void }
#[repr(C)]
struct PipelineShaderStageCreateInfo { sType: u32, pNext: *const c_void, flags: u32, stage: u32, module: H,
    pName: *const c_char, pSpecializationInfo: *const c_void }
#[repr(C)]
struct ComputePipelineCreateInfo { sType: u32, pNext: *const c_void, flags: u32, stage: PipelineShaderStageCreateInfo,
    layout: H, basePipelineHandle: H, basePipelineIndex: i32 }
#[repr(C)]
struct DescriptorPoolSize { ty: u32, descriptorCount: u32 }
#[repr(C)]
struct DescriptorPoolCreateInfo { sType: u32, pNext: *const c_void, flags: u32, maxSets: u32, poolSizeCount: u32,
    pPoolSizes: *const DescriptorPoolSize }
#[repr(C)]
struct DescriptorSetAllocateInfo { sType: u32, pNext: *const c_void, descriptorPool: H, descriptorSetCount: u32,
    pSetLayouts: *const H }
#[repr(C)]
struct DescriptorBufferInfo { buffer: H, offset: u64, range: u64 }
#[repr(C)]
struct WriteDescriptorSet { sType: u32, pNext: *const c_void, dstSet: H, dstBinding: u32, dstArrayElement: u32,
    descriptorCount: u32, descriptorType: u32, pImageInfo: *const c_void, pBufferInfo: *const DescriptorBufferInfo,
    pTexelBufferView: *const c_void }
#[repr(C)]
struct CommandPoolCreateInfo { sType: u32, pNext: *const c_void, flags: u32, queueFamilyIndex: u32 }
#[repr(C)]
struct CommandBufferAllocateInfo { sType: u32, pNext: *const c_void, commandPool: H, level: u32,
    commandBufferCount: u32 }
#[repr(C)]
struct CommandBufferBeginInfo { sType: u32, pNext: *const c_void, flags: u32, pInheritanceInfo: *const c_void }
#[repr(C)]
struct SubmitInfo { sType: u32, pNext: *const c_void, waitSemaphoreCount: u32, pWaitSemaphores: *const H,
    pWaitDstStageMask: *const u32, commandBufferCount: u32, pCommandBuffers: *const Ptr, signalSemaphoreCount: u32,
    pSignalSemaphores: *const H }
#[repr(C)]
struct QueryPoolCreateInfo { sType: u32, pNext: *const c_void, flags: u32, queryType: u32, queryCount: u32,
    pipelineStatistics: u32 }
#[repr(C)]
struct MemoryBarrier { sType: u32, pNext: *const c_void, srcAccessMask: u32, dstAccessMask: u32 }
#[repr(C)]
struct BufferCopy { srcOffset: u64, dstOffset: u64, size: u64 }
#[repr(C)]
struct FenceCreateInfo { sType: u32, pNext: *const c_void, flags: u32 }

// les nombres de la spécification
const ST_APPLICATION_INFO: u32 = 0;
const ST_INSTANCE_CREATE_INFO: u32 = 1;
const ST_DEVICE_QUEUE_CREATE_INFO: u32 = 2;
const ST_DEVICE_CREATE_INFO: u32 = 3;
const ST_SUBMIT_INFO: u32 = 4;
const ST_MEMORY_ALLOCATE_INFO: u32 = 5;
const ST_FENCE_CREATE_INFO: u32 = 8;
const ST_BUFFER_CREATE_INFO: u32 = 12;
const ST_SHADER_MODULE_CREATE_INFO: u32 = 16;
const ST_PIPELINE_SHADER_STAGE_CREATE_INFO: u32 = 18;
const ST_COMPUTE_PIPELINE_CREATE_INFO: u32 = 29;
const ST_PIPELINE_LAYOUT_CREATE_INFO: u32 = 30;
const ST_DESCRIPTOR_SET_LAYOUT_CREATE_INFO: u32 = 32;
const ST_DESCRIPTOR_POOL_CREATE_INFO: u32 = 33;
const ST_DESCRIPTOR_SET_ALLOCATE_INFO: u32 = 34;
const ST_WRITE_DESCRIPTOR_SET: u32 = 35;
const ST_COMMAND_POOL_CREATE_INFO: u32 = 39;
const ST_COMMAND_BUFFER_ALLOCATE_INFO: u32 = 40;
const ST_COMMAND_BUFFER_BEGIN_INFO: u32 = 42;
const ST_QUERY_POOL_CREATE_INFO: u32 = 11;
const ST_MEMORY_BARRIER: u32 = 46;
const QUERY_TIMESTAMP: u32 = 2;
const STAGE_TOP: u32 = 0x1;
const STAGE_COMPUTE_SHADER: u32 = 0x800;
const STAGE_TRANSFER: u32 = 0x1000;
const STAGE_BOTTOM: u32 = 0x2000;
const STAGE_HOST: u32 = 0x4000;
const ACCESS_SHADER_WRITE: u32 = 0x40;
const ACCESS_TRANSFER_READ: u32 = 0x800;
const ACCESS_TRANSFER_WRITE: u32 = 0x1000;
const ACCESS_HOST_READ: u32 = 0x2000;
const BUFFER_USAGE_TRANSFER_SRC: u32 = 0x1;
const BUFFER_USAGE_TRANSFER_DST: u32 = 0x2;
const MEM_DEVICE_LOCAL: u32 = 0x1;
const QUEUE_COMPUTE: u32 = 0x2;
const BUFFER_USAGE_STORAGE: u32 = 0x20;
const MEM_HOST_VISIBLE: u32 = 0x2;
const MEM_HOST_COHERENT: u32 = 0x4;
const DESCRIPTOR_STORAGE_BUFFER: u32 = 7;
const STAGE_COMPUTE: u32 = 0x20;
const BIND_POINT_COMPUTE: u32 = 1;
const API_1_0: u32 = 1 << 22;

// ------------------------------------------------------------------ les fonctions, prises par vkGetInstanceProcAddr
type FnGipa = unsafe extern "system" fn(Ptr, *const c_char) -> *mut c_void;

struct Vk {
    gipa: FnGipa,
    instance: Ptr,
}

macro_rules! vkfn {
    ($vk:expr, $nom:literal, $t:ty) => {{
        let f = ($vk.gipa)($vk.instance, concat!($nom, "\0").as_ptr() as *const c_char);
        if f.is_null() {
            return Err(format!("fonction Vulkan absente : {}", $nom));
        }
        std::mem::transmute::<*mut c_void, $t>(f)
    }};
}

/// un tampon et sa mémoire (du type voulu : dans la carte, ou visible du processeur)
unsafe fn tampon(vk: &Vk, dev: Ptr, mp: &MemoryProperties, taille: u64, usage: u32, voulu: u32) -> Result<(H, H), String> {
    let create_buffer = vkfn!(vk, "vkCreateBuffer", unsafe extern "system" fn(Ptr, *const BufferCreateInfo, *const c_void, *mut H) -> R);
    let reqs = vkfn!(vk, "vkGetBufferMemoryRequirements", unsafe extern "system" fn(Ptr, H, *mut MemoryRequirements));
    let alloc = vkfn!(vk, "vkAllocateMemory", unsafe extern "system" fn(Ptr, *const MemoryAllocateInfo, *const c_void, *mut H) -> R);
    let bind = vkfn!(vk, "vkBindBufferMemory", unsafe extern "system" fn(Ptr, H, H, u64) -> R);
    let bci = BufferCreateInfo { sType: ST_BUFFER_CREATE_INFO, pNext: null(), flags: 0, size: taille, usage,
        sharingMode: 0, queueFamilyIndexCount: 0, pQueueFamilyIndices: null() };
    let mut b: H = 0;
    verifie(create_buffer(dev, &bci, null(), &mut b), "vkCreateBuffer")?;
    let mut mr = MemoryRequirements::default();
    reqs(dev, b, &mut mr);
    let ty = (0..mp.memoryTypeCount)
        .find(|&k| mr.memoryTypeBits & (1 << k) != 0 && mp.memoryTypes[k as usize].propertyFlags & voulu == voulu)
        .ok_or(format!("aucune mémoire du type {:#x}", voulu))?;
    let mai = MemoryAllocateInfo { sType: ST_MEMORY_ALLOCATE_INFO, pNext: null(), allocationSize: mr.size, memoryTypeIndex: ty };
    let mut m: H = 0;
    verifie(alloc(dev, &mai, null(), &mut m), "vkAllocateMemory")?;
    verifie(bind(dev, b, m, 0), "vkBindBufferMemory")?;
    Ok((b, m))
}

fn verifie(r: R, quoi: &str) -> Result<(), String> {
    if r == 0 { Ok(()) } else { Err(format!("{} : VkResult {}", quoi, r)) }
}

fn brasser(i: u32) -> u32 {
    let mut x = i;
    for _ in 0..TOURS {
        x ^= x << 13;
        x ^= x >> 17;
        x ^= x << 5;
        x = x.wrapping_mul(0x9E37_79B1).wrapping_add(i);
    }
    x
}

fn type_carte(t: u32) -> &'static str {
    match t {
        1 => "intégrée",
        2 => "dédiée",
        3 => "virtuelle",
        4 => "processeur (logicielle)",
        _ => "autre",
    }
}

unsafe fn sonde(n: u32) -> Result<(), String> {
    let gipa: FnGipa = match charge::vk_get_instance_proc_addr() {
        Some(f) => std::mem::transmute::<*mut c_void, FnGipa>(f),
        None => return Err("pas de Vulkan sur cette machine (vulkan-1.dll introuvable : le pilote de la carte l'installe)".into()),
    };
    let mut vk = Vk { gipa, instance: null_mut() };

    // l'instance
    let nom = b"Vercintorix Taranis\0";
    let app = ApplicationInfo { sType: ST_APPLICATION_INFO, pNext: null(), pApplicationName: nom.as_ptr() as _,
        applicationVersion: 1, pEngineName: nom.as_ptr() as _, engineVersion: 1, apiVersion: API_1_0 };
    let ici = InstanceCreateInfo { sType: ST_INSTANCE_CREATE_INFO, pNext: null(), flags: 0, pApplicationInfo: &app,
        enabledLayerCount: 0, ppEnabledLayerNames: null(), enabledExtensionCount: 0, ppEnabledExtensionNames: null() };
    let create_instance = vkfn!(vk, "vkCreateInstance", unsafe extern "system" fn(*const InstanceCreateInfo, *const c_void, *mut Ptr) -> R);
    let mut instance: Ptr = null_mut();
    verifie(create_instance(&ici, null(), &mut instance), "vkCreateInstance")?;
    vk.instance = instance;

    // les cartes : la première dédiée, sinon la première
    let enum_pd = vkfn!(vk, "vkEnumeratePhysicalDevices", unsafe extern "system" fn(Ptr, *mut u32, *mut Ptr) -> R);
    let props = vkfn!(vk, "vkGetPhysicalDeviceProperties", unsafe extern "system" fn(Ptr, *mut u8));
    let mut nb = 0u32;
    verifie(enum_pd(instance, &mut nb, null_mut()), "vkEnumeratePhysicalDevices")?;
    if nb == 0 {
        return Err("Vulkan est là, mais aucune carte".into());
    }
    let mut cartes = vec![null_mut(); nb as usize];
    verifie(enum_pd(instance, &mut nb, cartes.as_mut_ptr()), "vkEnumeratePhysicalDevices")?;
    let mut choix = 0;
    let mut dediee = false;
    let mut p = vec![0u64; 160]; // VkPhysicalDeviceProperties : 824 octets
    for (k, &c) in cartes.iter().enumerate() {
        props(c, p.as_mut_ptr() as *mut u8);
        let b = p.as_ptr() as *const u8;
        let api = *(b as *const u32);
        let ty = *(b.add(16) as *const u32);
        let nom = CStr::from_ptr(b.add(20) as *const c_char).to_string_lossy().into_owned();
        println!("carte {} : {} ({}, Vulkan {}.{}.{})", k, nom, type_carte(ty), api >> 22, (api >> 12) & 1023, api & 4095);
        if ty == 2 && !dediee {
            choix = k;
            dediee = true;
        }
    }
    let carte = cartes[choix];
    props(carte, p.as_mut_ptr() as *mut u8);
    let b = p.as_ptr() as *const u8;
    // dans VkPhysicalDeviceLimits (à l'octet 296) : maxComputeWorkGroupCount[0] (+220), maxComputeWorkGroupInvocations
    // (+232), timestampPeriod (+424, en nanosecondes par tic)
    let groupes_max = *(b.add(296 + 220) as *const u32);
    let fils_max = *(b.add(296 + 232) as *const u32);
    let periode = *(b.add(296 + 424) as *const f32) as f64;
    println!("choisie : la carte {} ({} groupes au plus, {} fils par groupe au plus, un tic = {} ns)", choix, groupes_max, fils_max, periode);

    // une file qui calcule
    let qf = vkfn!(vk, "vkGetPhysicalDeviceQueueFamilyProperties", unsafe extern "system" fn(Ptr, *mut u32, *mut QueueFamilyProperties));
    let mut nq = 0u32;
    qf(carte, &mut nq, null_mut());
    let mut familles = vec![QueueFamilyProperties::default(); nq as usize];
    qf(carte, &mut nq, familles.as_mut_ptr());
    let famille = familles.iter().position(|f| f.queueFlags & QUEUE_COMPUTE != 0).ok_or("aucune file de calcul")? as u32;

    // l'appareil
    let prio = 1.0f32;
    let dq = DeviceQueueCreateInfo { sType: ST_DEVICE_QUEUE_CREATE_INFO, pNext: null(), flags: 0, queueFamilyIndex: famille,
        queueCount: 1, pQueuePriorities: &prio };
    let dci = DeviceCreateInfo { sType: ST_DEVICE_CREATE_INFO, pNext: null(), flags: 0, queueCreateInfoCount: 1,
        pQueueCreateInfos: &dq, enabledLayerCount: 0, ppEnabledLayerNames: null(), enabledExtensionCount: 0,
        ppEnabledExtensionNames: null(), pEnabledFeatures: null() };
    let create_device = vkfn!(vk, "vkCreateDevice", unsafe extern "system" fn(Ptr, *const DeviceCreateInfo, *const c_void, *mut Ptr) -> R);
    let mut dev: Ptr = null_mut();
    verifie(create_device(carte, &dci, null(), &mut dev), "vkCreateDevice")?;
    let get_queue = vkfn!(vk, "vkGetDeviceQueue", unsafe extern "system" fn(Ptr, u32, u32, *mut Ptr));
    let mut file: Ptr = null_mut();
    get_queue(dev, famille, 0, &mut file);

    // les tampons : n mots de 32 bits dans la carte (le calcul), et autant visibles du processeur (la copie)
    let taille = n as u64 * 4;
    let memprops = vkfn!(vk, "vkGetPhysicalDeviceMemoryProperties", unsafe extern "system" fn(Ptr, *mut MemoryProperties));
    let mut mp: MemoryProperties = std::mem::zeroed();
    memprops(carte, &mut mp);
    let (calcul, _) = tampon(&vk, dev, &mp, taille, BUFFER_USAGE_STORAGE | BUFFER_USAGE_TRANSFER_SRC, MEM_DEVICE_LOCAL)?;
    let (retour, memoire) = tampon(&vk, dev, &mp, taille, BUFFER_USAGE_TRANSFER_DST, MEM_HOST_VISIBLE | MEM_HOST_COHERENT)?;
    let map = vkfn!(vk, "vkMapMemory", unsafe extern "system" fn(Ptr, H, u64, u64, u32, *mut *mut c_void) -> R);
    let mut vue: *mut c_void = null_mut();
    verifie(map(dev, memoire, 0, taille, 0, &mut vue), "vkMapMemory")?;
    let mots = std::slice::from_raw_parts_mut(vue as *mut u32, n as usize);
    mots.fill(0);

    // le noyau
    if NOYAU.len() % 4 != 0 {
        return Err("taranis_sonde.spv : pas un nombre entier de mots".into());
    }
    let code: Vec<u32> = NOYAU.chunks(4).map(|c| u32::from_le_bytes([c[0], c[1], c[2], c[3]])).collect();
    let create_sm = vkfn!(vk, "vkCreateShaderModule", unsafe extern "system" fn(Ptr, *const ShaderModuleCreateInfo, *const c_void, *mut H) -> R);
    let smci = ShaderModuleCreateInfo { sType: ST_SHADER_MODULE_CREATE_INFO, pNext: null(), flags: 0,
        codeSize: code.len() * 4, pCode: code.as_ptr() };
    let mut module: H = 0;
    verifie(create_sm(dev, &smci, null(), &mut module), "vkCreateShaderModule")?;

    // ce que le noyau voit : un tampon de stockage, en liaison 0
    let liaison = DescriptorSetLayoutBinding { binding: 0, descriptorType: DESCRIPTOR_STORAGE_BUFFER, descriptorCount: 1,
        stageFlags: STAGE_COMPUTE, pImmutableSamplers: null() };
    let create_dsl = vkfn!(vk, "vkCreateDescriptorSetLayout", unsafe extern "system" fn(Ptr, *const DescriptorSetLayoutCreateInfo, *const c_void, *mut H) -> R);
    let dslci = DescriptorSetLayoutCreateInfo { sType: ST_DESCRIPTOR_SET_LAYOUT_CREATE_INFO, pNext: null(), flags: 0,
        bindingCount: 1, pBindings: &liaison };
    let mut dsl: H = 0;
    verifie(create_dsl(dev, &dslci, null(), &mut dsl), "vkCreateDescriptorSetLayout")?;
    let create_pl = vkfn!(vk, "vkCreatePipelineLayout", unsafe extern "system" fn(Ptr, *const PipelineLayoutCreateInfo, *const c_void, *mut H) -> R);
    let plci = PipelineLayoutCreateInfo { sType: ST_PIPELINE_LAYOUT_CREATE_INFO, pNext: null(), flags: 0, setLayoutCount: 1,
        pSetLayouts: &dsl, pushConstantRangeCount: 0, pPushConstantRanges: null() };
    let mut pl: H = 0;
    verifie(create_pl(dev, &plci, null(), &mut pl), "vkCreatePipelineLayout")?;
    let create_cp = vkfn!(vk, "vkCreateComputePipelines", unsafe extern "system" fn(Ptr, H, u32, *const ComputePipelineCreateInfo, *const c_void, *mut H) -> R);
    let cpci = ComputePipelineCreateInfo { sType: ST_COMPUTE_PIPELINE_CREATE_INFO, pNext: null(), flags: 0,
        stage: PipelineShaderStageCreateInfo { sType: ST_PIPELINE_SHADER_STAGE_CREATE_INFO, pNext: null(), flags: 0,
            stage: STAGE_COMPUTE, module, pName: b"main\0".as_ptr() as _, pSpecializationInfo: null() },
        layout: pl, basePipelineHandle: 0, basePipelineIndex: -1 };
    let mut pipeline: H = 0;
    verifie(create_cp(dev, 0, 1, &cpci, null(), &mut pipeline), "vkCreateComputePipelines (le SPIR-V refusé ?)")?;

    let taille_pool = DescriptorPoolSize { ty: DESCRIPTOR_STORAGE_BUFFER, descriptorCount: 1 };
    let create_dp = vkfn!(vk, "vkCreateDescriptorPool", unsafe extern "system" fn(Ptr, *const DescriptorPoolCreateInfo, *const c_void, *mut H) -> R);
    let dpci = DescriptorPoolCreateInfo { sType: ST_DESCRIPTOR_POOL_CREATE_INFO, pNext: null(), flags: 0, maxSets: 1,
        poolSizeCount: 1, pPoolSizes: &taille_pool };
    let mut dp: H = 0;
    verifie(create_dp(dev, &dpci, null(), &mut dp), "vkCreateDescriptorPool")?;
    let alloc_ds = vkfn!(vk, "vkAllocateDescriptorSets", unsafe extern "system" fn(Ptr, *const DescriptorSetAllocateInfo, *mut H) -> R);
    let dsai = DescriptorSetAllocateInfo { sType: ST_DESCRIPTOR_SET_ALLOCATE_INFO, pNext: null(), descriptorPool: dp,
        descriptorSetCount: 1, pSetLayouts: &dsl };
    let mut ds: H = 0;
    verifie(alloc_ds(dev, &dsai, &mut ds), "vkAllocateDescriptorSets")?;
    let dbi = DescriptorBufferInfo { buffer: calcul, offset: 0, range: taille };
    let wds = WriteDescriptorSet { sType: ST_WRITE_DESCRIPTOR_SET, pNext: null(), dstSet: ds, dstBinding: 0,
        dstArrayElement: 0, descriptorCount: 1, descriptorType: DESCRIPTOR_STORAGE_BUFFER, pImageInfo: null(),
        pBufferInfo: &dbi, pTexelBufferView: null() };
    let update_ds = vkfn!(vk, "vkUpdateDescriptorSets", unsafe extern "system" fn(Ptr, u32, *const WriteDescriptorSet, u32, *const c_void));
    update_ds(dev, 1, &wds, 0, null());

    // les commandes : lier, lancer n / 64 groupes
    let create_cpool = vkfn!(vk, "vkCreateCommandPool", unsafe extern "system" fn(Ptr, *const CommandPoolCreateInfo, *const c_void, *mut H) -> R);
    let cpi = CommandPoolCreateInfo { sType: ST_COMMAND_POOL_CREATE_INFO, pNext: null(), flags: 0, queueFamilyIndex: famille };
    let mut cpool: H = 0;
    verifie(create_cpool(dev, &cpi, null(), &mut cpool), "vkCreateCommandPool")?;
    let alloc_cb = vkfn!(vk, "vkAllocateCommandBuffers", unsafe extern "system" fn(Ptr, *const CommandBufferAllocateInfo, *mut Ptr) -> R);
    let cbai = CommandBufferAllocateInfo { sType: ST_COMMAND_BUFFER_ALLOCATE_INFO, pNext: null(), commandPool: cpool,
        level: 0, commandBufferCount: 1 };
    let mut cb: Ptr = null_mut();
    verifie(alloc_cb(dev, &cbai, &mut cb), "vkAllocateCommandBuffers")?;
    let begin = vkfn!(vk, "vkBeginCommandBuffer", unsafe extern "system" fn(Ptr, *const CommandBufferBeginInfo) -> R);
    let bind_p = vkfn!(vk, "vkCmdBindPipeline", unsafe extern "system" fn(Ptr, u32, H));
    let bind_ds = vkfn!(vk, "vkCmdBindDescriptorSets", unsafe extern "system" fn(Ptr, u32, H, u32, u32, *const H, u32, *const u32));
    let dispatch = vkfn!(vk, "vkCmdDispatch", unsafe extern "system" fn(Ptr, u32, u32, u32));
    let end = vkfn!(vk, "vkEndCommandBuffer", unsafe extern "system" fn(Ptr) -> R);
    let cbbi = CommandBufferBeginInfo { sType: ST_COMMAND_BUFFER_BEGIN_INFO, pNext: null(), flags: 0, pInheritanceInfo: null() };
    let create_qp = vkfn!(vk, "vkCreateQueryPool", unsafe extern "system" fn(Ptr, *const QueryPoolCreateInfo, *const c_void, *mut H) -> R);
    let reset_qp = vkfn!(vk, "vkCmdResetQueryPool", unsafe extern "system" fn(Ptr, H, u32, u32));
    let stamp = vkfn!(vk, "vkCmdWriteTimestamp", unsafe extern "system" fn(Ptr, u32, H, u32));
    let barrier = vkfn!(vk, "vkCmdPipelineBarrier", unsafe extern "system" fn(Ptr, u32, u32, u32, u32, *const MemoryBarrier, u32, *const c_void, u32, *const c_void));
    let copy = vkfn!(vk, "vkCmdCopyBuffer", unsafe extern "system" fn(Ptr, H, H, u32, *const BufferCopy));
    let results = vkfn!(vk, "vkGetQueryPoolResults", unsafe extern "system" fn(Ptr, H, u32, u32, usize, *mut c_void, u64, u32) -> R);
    let qpci = QueryPoolCreateInfo { sType: ST_QUERY_POOL_CREATE_INFO, pNext: null(), flags: 0, queryType: QUERY_TIMESTAMP,
        queryCount: 3, pipelineStatistics: 0 };
    let mut qp: H = 0;
    verifie(create_qp(dev, &qpci, null(), &mut qp), "vkCreateQueryPool")?;
    let horloge = familles[famille as usize].timestampValidBits > 0;
    verifie(begin(cb, &cbbi), "vkBeginCommandBuffer")?;
    reset_qp(cb, qp, 0, 3);
    bind_p(cb, BIND_POINT_COMPUTE, pipeline);
    bind_ds(cb, BIND_POINT_COMPUTE, pl, 0, 1, &ds, 0, null());
    stamp(cb, STAGE_TOP, qp, 0);
    dispatch(cb, n / LARGEUR, 1, 1);
    stamp(cb, STAGE_BOTTOM, qp, 1);
    let b1 = MemoryBarrier { sType: ST_MEMORY_BARRIER, pNext: null(), srcAccessMask: ACCESS_SHADER_WRITE, dstAccessMask: ACCESS_TRANSFER_READ };
    barrier(cb, STAGE_COMPUTE_SHADER, STAGE_TRANSFER, 0, 1, &b1, 0, null(), 0, null());
    let region = BufferCopy { srcOffset: 0, dstOffset: 0, size: taille };
    copy(cb, calcul, retour, 1, &region);
    stamp(cb, STAGE_BOTTOM, qp, 2);
    let b2 = MemoryBarrier { sType: ST_MEMORY_BARRIER, pNext: null(), srcAccessMask: ACCESS_TRANSFER_WRITE, dstAccessMask: ACCESS_HOST_READ };
    barrier(cb, STAGE_TRANSFER, STAGE_HOST, 0, 1, &b2, 0, null(), 0, null());
    verifie(end(cb), "vkEndCommandBuffer")?;

    let create_fence = vkfn!(vk, "vkCreateFence", unsafe extern "system" fn(Ptr, *const FenceCreateInfo, *const c_void, *mut H) -> R);
    let wait = vkfn!(vk, "vkWaitForFences", unsafe extern "system" fn(Ptr, u32, *const H, u32, u64) -> R);
    let reset = vkfn!(vk, "vkResetFences", unsafe extern "system" fn(Ptr, u32, *const H) -> R);
    let submit = vkfn!(vk, "vkQueueSubmit", unsafe extern "system" fn(Ptr, u32, *const SubmitInfo, H) -> R);
    let fci = FenceCreateInfo { sType: ST_FENCE_CREATE_INFO, pNext: null(), flags: 0 };
    let mut fence: H = 0;
    verifie(create_fence(dev, &fci, null(), &mut fence), "vkCreateFence")?;
    let si = SubmitInfo { sType: ST_SUBMIT_INFO, pNext: null(), waitSemaphoreCount: 0, pWaitSemaphores: null(),
        pWaitDstStageMask: null(), commandBufferCount: 1, pCommandBuffers: &cb, signalSemaphoreCount: 0,
        pSignalSemaphores: null() };

    // une première fois (la carte se réveille, le noyau est traduit), puis cinq mesurées : la meilleure
    let mut meilleur = f64::MAX;
    let (mut t_calcul, mut t_copie) = (f64::MAX, f64::MAX);
    for k in 0..6 {
        let t = std::time::Instant::now();
        verifie(submit(file, 1, &si, fence), "vkQueueSubmit")?;
        verifie(wait(dev, 1, &fence, 1, 10_000_000_000), "vkWaitForFences")?;
        let s = t.elapsed().as_secs_f64();
        verifie(reset(dev, 1, &fence), "vkResetFences")?;
        if horloge {
            let mut tics = [0u64; 3];
            verifie(results(dev, qp, 0, 3, 24, tics.as_mut_ptr() as *mut c_void, 8, 1 | 2), "vkGetQueryPoolResults")?;
            let c = (tics[1].wrapping_sub(tics[0])) as f64 * periode * 1e-9;
            let r = (tics[2].wrapping_sub(tics[1])) as f64 * periode * 1e-9;
            if k > 0 {
                t_calcul = t_calcul.min(c);
                t_copie = t_copie.min(r);
            }
        }
        if k == 0 {
            println!("carte : premier lancement {:.2} ms (lancement, calcul, copie, attente)", s * 1e3);
        } else if s < meilleur {
            meilleur = s;
        }
    }

    // le processeur : un cœur, puis tous ; et la comparaison mot à mot
    let t = std::time::Instant::now();
    let mut ecarts = 0usize;
    let mut premier_ecart = None;
    for i in 0..n {
        if mots[i as usize] != brasser(i) {
            ecarts += 1;
            if premier_ecart.is_none() {
                premier_ecart = Some(i);
            }
        }
    }
    let un_coeur = t.elapsed().as_secs_f64();
    let coeurs = std::thread::available_parallelism().map(|c| c.get()).unwrap_or(1);
    let t = std::time::Instant::now();
    let tranche = (n as usize + coeurs - 1) / coeurs;
    let somme: u64 = std::thread::scope(|sc| {
        let fils: Vec<_> = (0..coeurs).map(|c| sc.spawn(move || {
            let a = (c * tranche).min(n as usize) as u32;
            let b = ((c + 1) * tranche).min(n as usize) as u32;
            (a..b).map(|i| brasser(i) as u64).sum::<u64>()
        })).collect();
        fils.into_iter().map(|f| f.join().unwrap()).sum()
    });
    let tous = t.elapsed().as_secs_f64();
    let somme_carte: u64 = mots.iter().map(|&v| v as u64).sum();

    let ops = n as f64 * TOURS as f64 * 8.0;
    println!("{} fils, {} tours de brassage chacun ({:.1} milliards d'opérations sur 32 bits)", n, TOURS, ops / 1e9);
    println!("carte, tout compris  : {:8.2} ms   (lancement, calcul, copie vers le processeur, attente)", meilleur * 1e3);
    if horloge {
        println!("carte, le calcul     : {:8.2} ms   ({:.0} milliards d'opérations par seconde)", t_calcul * 1e3, ops / t_calcul / 1e9);
        println!("carte, la copie      : {:8.2} ms   ({:.1} Go/s vers le processeur)", t_copie * 1e3, taille as f64 / t_copie / 1e9);
        println!("CALCUL_MS {:.3}", t_calcul * 1e3);
    }
    println!("processeur, 1 cœur   : {:8.2} ms (en vérifiant)", un_coeur * 1e3);
    println!("processeur, {} cœurs : {:8.2} ms", coeurs, tous * 1e3);
    let ref_carte = if horloge { t_calcul } else { meilleur };
    println!("la carte (son calcul) va {:.0} fois plus vite que tous les cœurs, {:.0} fois plus vite qu'un cœur", tous / ref_carte, un_coeur / ref_carte);
    println!("SOMME {}", somme_carte);
    if ecarts == 0 && somme == somme_carte {
        println!("la carte et le processeur : les mêmes {} mots", n);
        Ok(())
    } else {
        Err(format!("{} mots différents (le premier : t[{}] = {} au lieu de {})", ecarts, premier_ecart.unwrap_or(0),
            mots[premier_ecart.unwrap_or(0) as usize], brasser(premier_ecart.unwrap_or(0))))
    }
}

fn main() {
    let n: u32 = std::env::args().nth(1).and_then(|a| a.parse().ok()).unwrap_or(1 << 24);
    let n = (n / LARGEUR).max(1) * LARGEUR;
    println!("Taranis, la sonde : le SPIR-V de vtx sur la carte graphique, par Vulkan, sans bibliothèque");
    match unsafe { sonde(n) } {
        Ok(()) => println!("sonde : tout est conforme"),
        Err(e) => {
            println!("sonde : ÉCHEC : {}", e);
            std::process::exit(1);
        }
    }
}
