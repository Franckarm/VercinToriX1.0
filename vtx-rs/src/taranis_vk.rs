// Taranis pour les programmes forgés : la carte graphique, par Vulkan, sans bibliothèque (vulkan-1.dll chargée à
// l'exécution). La forge (forge/forge128.py) écrit le SPIR-V d'une boucle en segments (taranis/noyau_vtx.py) et
// l'appelle par lancer() : la fenêtre de l'étage 2 (des mots de 64 bits) montée dans la mémoire de la carte, les
// paramètres, un fil par tour de boucle, puis la fenêtre redescendue. La carte est prise une fois (la première dédiée) ;
// VTX_CARTE=0 la laisse de côté (la boucle reste aux cylindres) ; VTX_TARANIS=1 dit ce que fait la carte.
#![allow(non_snake_case, non_camel_case_types, dead_code, clippy::upper_case_acronyms)]
use std::ffi::{c_char, c_void, CStr};
use std::ptr::{null, null_mut};

type Ptr = *mut c_void;
type H = u64;
type R = i32;

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
const MEM_HOST_CACHED: u32 = 0x8;
const QUEUE_COMPUTE: u32 = 0x2;
const BUFFER_USAGE_STORAGE: u32 = 0x20;
const MEM_HOST_VISIBLE: u32 = 0x2;
const MEM_HOST_COHERENT: u32 = 0x4;
const DESCRIPTOR_STORAGE_BUFFER: u32 = 7;
const STAGE_COMPUTE: u32 = 0x20;
const BIND_POINT_COMPUTE: u32 = 1;
const API_1_0: u32 = 1 << 22;


const ACCESS_SHADER_READ: u32 = 0x20;
const LARGEUR: u64 = 64;


type FnGipa = unsafe extern "system" fn(Ptr, *const c_char) -> *mut c_void;

macro_rules! vkfn {
    ($c:expr, $nom:literal, $t:ty) => {{
        let f = ($c.gipa)($c.instance, concat!($nom, "\0").as_ptr() as *const c_char);
        if f.is_null() {
            return Err(format!("fonction Vulkan absente : {}", $nom));
        }
        std::mem::transmute::<*mut c_void, $t>(f)
    }};
}

fn verifie(r: R, quoi: &str) -> Result<(), String> {
    if r == 0 { Ok(()) } else { Err(format!("{} : VkResult {}", quoi, r)) }
}

pub struct Carte {
    gipa: FnGipa,
    instance: Ptr,
    pd: Ptr,
    dev: Ptr,
    file: Ptr,
    famille: u32,
    mp: MemoryProperties,
    groupes_max: u64,
    stockage_max: u64,
    pub nom: String,
    /// 0.817 : la carte fait les entiers de 64 bits elle-même (shaderInt64, demandé à la création)
    pub int64: bool,
    dsl: H,
    pl: H,
    pipelines: Vec<(usize, H)>,
    // 0.816 : le mode pages (cinq liaisons : les pages, les paramètres, la table, les marques, les auteurs)
    dsl5: H,
    pl5: H,
    cpool: H,
    cb: Ptr,
    fence: H,
}

static mut CARTE: Option<Box<Carte>> = None;
static INIT: std::sync::Once = std::sync::Once::new();

pub fn bavard() -> bool {
    std::env::var("VTX_TARANIS").map(|v| v != "0").unwrap_or(false)
}

/// la carte (prise la première fois) ; None : pas de carte, pas d'entiers de 64 bits, ou VTX_CARTE=0
pub fn carte() -> Option<&'static mut Carte> {
    if std::env::var("VTX_CARTE").map(|v| v == "0").unwrap_or(false) {
        return None;
    }
    unsafe {
        INIT.call_once(|| match prendre() {
            Ok(c) => {
                if bavard() {
                    eprintln!("taranis : la carte {}", c.nom);
                }
                CARTE = Some(Box::new(c));
            }
            Err(e) => {
                if bavard() {
                    eprintln!("taranis : pas de carte ({})", e);
                }
            }
        });
        (*std::ptr::addr_of_mut!(CARTE)).as_deref_mut()
    }
}

unsafe fn prendre() -> Result<Carte, String> {
    let gipa: FnGipa = match charge::vk_get_instance_proc_addr() {
        Some(f) => std::mem::transmute::<*mut c_void, FnGipa>(f),
        None => return Err("vulkan-1.dll introuvable".into()),
    };
    let mut c = Carte { gipa, instance: null_mut(), pd: null_mut(), dev: null_mut(), file: null_mut(), famille: 0,
        mp: std::mem::zeroed(), groupes_max: 65535, stockage_max: 1 << 27, nom: String::new(), int64: false, dsl: 0, pl: 0,
        pipelines: Vec::new(), dsl5: 0, pl5: 0, cpool: 0, cb: null_mut(), fence: 0 };
    let nom = b"Vercintorix Taranis\0";
    let app = ApplicationInfo { sType: ST_APPLICATION_INFO, pNext: null(), pApplicationName: nom.as_ptr() as _,
        applicationVersion: 1, pEngineName: nom.as_ptr() as _, engineVersion: 1, apiVersion: API_1_0 };
    let ici = InstanceCreateInfo { sType: ST_INSTANCE_CREATE_INFO, pNext: null(), flags: 0, pApplicationInfo: &app,
        enabledLayerCount: 0, ppEnabledLayerNames: null(), enabledExtensionCount: 0, ppEnabledExtensionNames: null() };
    let create_instance = vkfn!(c, "vkCreateInstance", unsafe extern "system" fn(*const InstanceCreateInfo, *const c_void, *mut Ptr) -> R);
    verifie(create_instance(&ici, null(), &mut c.instance), "vkCreateInstance")?;
    let enum_pd = vkfn!(c, "vkEnumeratePhysicalDevices", unsafe extern "system" fn(Ptr, *mut u32, *mut Ptr) -> R);
    let props = vkfn!(c, "vkGetPhysicalDeviceProperties", unsafe extern "system" fn(Ptr, *mut u8));
    let feats = vkfn!(c, "vkGetPhysicalDeviceFeatures", unsafe extern "system" fn(Ptr, *mut u32));
    let mut nb = 0u32;
    verifie(enum_pd(c.instance, &mut nb, null_mut()), "vkEnumeratePhysicalDevices")?;
    if nb == 0 {
        return Err("aucune carte".into());
    }
    let mut cartes = vec![null_mut(); nb as usize];
    verifie(enum_pd(c.instance, &mut nb, cartes.as_mut_ptr()), "vkEnumeratePhysicalDevices")?;
    let mut p = vec![0u64; 160];
    let mut choix = 0;
    for (k, &pd) in cartes.iter().enumerate() {
        props(pd, p.as_mut_ptr() as *mut u8);
        if *((p.as_ptr() as *const u8).add(16) as *const u32) == 2 {
            choix = k;
            break;
        }
    }
    c.pd = cartes[choix];
    props(c.pd, p.as_mut_ptr() as *mut u8);
    let b = p.as_ptr() as *const u8;
    c.nom = CStr::from_ptr(b.add(20) as *const c_char).to_string_lossy().into_owned();
    c.groupes_max = *(b.add(296 + 220) as *const u32) as u64;
    c.stockage_max = *(b.add(296 + 28) as *const u32) as u64;
    // les noyaux de vtx calculent les entiers de 64 bits en deux mots de 32 bits : aucune option de la carte n'est
    // nécessaire ; 0.817 : si la carte sait faire les entiers de 64 bits (shaderInt64, la 41e option de
    // VkPhysicalDeviceFeatures), elle est demandée (les noyaux en pages la prennent alors)
    let mut offertes = [0u32; 55];
    feats(c.pd, offertes.as_mut_ptr());
    let mut voulu = [0u32; 55];
    if offertes[40] != 0 && std::env::var("VTX_INT64").map_or(true, |v| v != "0") {
        voulu[40] = 1;
        c.int64 = true;
    }
    let qf = vkfn!(c, "vkGetPhysicalDeviceQueueFamilyProperties", unsafe extern "system" fn(Ptr, *mut u32, *mut QueueFamilyProperties));
    let mut nq = 0u32;
    qf(c.pd, &mut nq, null_mut());
    let mut familles = vec![QueueFamilyProperties::default(); nq as usize];
    qf(c.pd, &mut nq, familles.as_mut_ptr());
    c.famille = familles.iter().position(|f| f.queueFlags & QUEUE_COMPUTE != 0).ok_or("aucune file de calcul")? as u32;
    let prio = 1.0f32;
    let dq = DeviceQueueCreateInfo { sType: ST_DEVICE_QUEUE_CREATE_INFO, pNext: null(), flags: 0, queueFamilyIndex: c.famille,
        queueCount: 1, pQueuePriorities: &prio };
    let dci = DeviceCreateInfo { sType: ST_DEVICE_CREATE_INFO, pNext: null(), flags: 0, queueCreateInfoCount: 1,
        pQueueCreateInfos: &dq, enabledLayerCount: 0, ppEnabledLayerNames: null(), enabledExtensionCount: 0,
        ppEnabledExtensionNames: null(), pEnabledFeatures: voulu.as_ptr() as *const c_void };
    let create_device = vkfn!(c, "vkCreateDevice", unsafe extern "system" fn(Ptr, *const DeviceCreateInfo, *const c_void, *mut Ptr) -> R);
    verifie(create_device(c.pd, &dci, null(), &mut c.dev), "vkCreateDevice")?;
    let get_queue = vkfn!(c, "vkGetDeviceQueue", unsafe extern "system" fn(Ptr, u32, u32, *mut Ptr));
    get_queue(c.dev, c.famille, 0, &mut c.file);
    let memprops = vkfn!(c, "vkGetPhysicalDeviceMemoryProperties", unsafe extern "system" fn(Ptr, *mut MemoryProperties));
    memprops(c.pd, &mut c.mp);
    // deux tampons de stockage (la fenêtre, les paramètres), une mise en page pour tous les noyaux
    let liaisons = [
        DescriptorSetLayoutBinding { binding: 0, descriptorType: DESCRIPTOR_STORAGE_BUFFER, descriptorCount: 1,
            stageFlags: STAGE_COMPUTE, pImmutableSamplers: null() },
        DescriptorSetLayoutBinding { binding: 1, descriptorType: DESCRIPTOR_STORAGE_BUFFER, descriptorCount: 1,
            stageFlags: STAGE_COMPUTE, pImmutableSamplers: null() },
    ];
    let create_dsl = vkfn!(c, "vkCreateDescriptorSetLayout", unsafe extern "system" fn(Ptr, *const DescriptorSetLayoutCreateInfo, *const c_void, *mut H) -> R);
    let dslci = DescriptorSetLayoutCreateInfo { sType: ST_DESCRIPTOR_SET_LAYOUT_CREATE_INFO, pNext: null(), flags: 0,
        bindingCount: 2, pBindings: liaisons.as_ptr() };
    verifie(create_dsl(c.dev, &dslci, null(), &mut c.dsl), "vkCreateDescriptorSetLayout")?;
    let create_pl = vkfn!(c, "vkCreatePipelineLayout", unsafe extern "system" fn(Ptr, *const PipelineLayoutCreateInfo, *const c_void, *mut H) -> R);
    let plci = PipelineLayoutCreateInfo { sType: ST_PIPELINE_LAYOUT_CREATE_INFO, pNext: null(), flags: 0, setLayoutCount: 1,
        pSetLayouts: &c.dsl, pushConstantRangeCount: 0, pPushConstantRanges: null() };
    verifie(create_pl(c.dev, &plci, null(), &mut c.pl), "vkCreatePipelineLayout")?;
    let create_cpool = vkfn!(c, "vkCreateCommandPool", unsafe extern "system" fn(Ptr, *const CommandPoolCreateInfo, *const c_void, *mut H) -> R);
    let cpi = CommandPoolCreateInfo { sType: ST_COMMAND_POOL_CREATE_INFO, pNext: null(), flags: 0, queueFamilyIndex: c.famille };
    verifie(create_cpool(c.dev, &cpi, null(), &mut c.cpool), "vkCreateCommandPool")?;
    let alloc_cb = vkfn!(c, "vkAllocateCommandBuffers", unsafe extern "system" fn(Ptr, *const CommandBufferAllocateInfo, *mut Ptr) -> R);
    let cbai = CommandBufferAllocateInfo { sType: ST_COMMAND_BUFFER_ALLOCATE_INFO, pNext: null(), commandPool: c.cpool,
        level: 0, commandBufferCount: 1 };
    verifie(alloc_cb(c.dev, &cbai, &mut c.cb), "vkAllocateCommandBuffers")?;
    let create_fence = vkfn!(c, "vkCreateFence", unsafe extern "system" fn(Ptr, *const FenceCreateInfo, *const c_void, *mut H) -> R);
    let fci = FenceCreateInfo { sType: ST_FENCE_CREATE_INFO, pNext: null(), flags: 0 };
    verifie(create_fence(c.dev, &fci, null(), &mut c.fence), "vkCreateFence")?;
    Ok(c)
}

impl Carte {
    unsafe fn pipeline(&mut self, spv: &[u32]) -> Result<H, String> {
        let pl = self.pl;
        self.pipeline_avec(spv, pl)
    }

    /// 0.816 : la mise en page à cinq tampons (faite la première fois)
    unsafe fn mise_en_page5(&mut self) -> Result<H, String> {
        if self.pl5 != 0 {
            return Ok(self.pl5);
        }
        let liaisons: Vec<DescriptorSetLayoutBinding> = (0..5u32).map(|k| DescriptorSetLayoutBinding { binding: k,
            descriptorType: DESCRIPTOR_STORAGE_BUFFER, descriptorCount: 1, stageFlags: STAGE_COMPUTE,
            pImmutableSamplers: null() }).collect();
        let create_dsl = vkfn!(self, "vkCreateDescriptorSetLayout", unsafe extern "system" fn(Ptr, *const DescriptorSetLayoutCreateInfo, *const c_void, *mut H) -> R);
        let dslci = DescriptorSetLayoutCreateInfo { sType: ST_DESCRIPTOR_SET_LAYOUT_CREATE_INFO, pNext: null(), flags: 0,
            bindingCount: 5, pBindings: liaisons.as_ptr() };
        verifie(create_dsl(self.dev, &dslci, null(), &mut self.dsl5), "vkCreateDescriptorSetLayout")?;
        let create_pl = vkfn!(self, "vkCreatePipelineLayout", unsafe extern "system" fn(Ptr, *const PipelineLayoutCreateInfo, *const c_void, *mut H) -> R);
        let plci = PipelineLayoutCreateInfo { sType: ST_PIPELINE_LAYOUT_CREATE_INFO, pNext: null(), flags: 0, setLayoutCount: 1,
            pSetLayouts: &self.dsl5, pushConstantRangeCount: 0, pPushConstantRanges: null() };
        verifie(create_pl(self.dev, &plci, null(), &mut self.pl5), "vkCreatePipelineLayout")?;
        Ok(self.pl5)
    }

    unsafe fn pipeline_avec(&mut self, spv: &[u32], pl: H) -> Result<H, String> {
        let cle = spv.as_ptr() as usize;
        if let Some(&(_, p)) = self.pipelines.iter().find(|(k, _)| *k == cle) {
            return Ok(p);
        }
        let create_sm = vkfn!(self, "vkCreateShaderModule", unsafe extern "system" fn(Ptr, *const ShaderModuleCreateInfo, *const c_void, *mut H) -> R);
        let smci = ShaderModuleCreateInfo { sType: ST_SHADER_MODULE_CREATE_INFO, pNext: null(), flags: 0,
            codeSize: spv.len() * 4, pCode: spv.as_ptr() };
        let mut module: H = 0;
        verifie(create_sm(self.dev, &smci, null(), &mut module), "vkCreateShaderModule")?;
        let create_cp = vkfn!(self, "vkCreateComputePipelines", unsafe extern "system" fn(Ptr, H, u32, *const ComputePipelineCreateInfo, *const c_void, *mut H) -> R);
        let cpci = ComputePipelineCreateInfo { sType: ST_COMPUTE_PIPELINE_CREATE_INFO, pNext: null(), flags: 0,
            stage: PipelineShaderStageCreateInfo { sType: ST_PIPELINE_SHADER_STAGE_CREATE_INFO, pNext: null(), flags: 0,
                stage: STAGE_COMPUTE, module, pName: b"main\0".as_ptr() as _, pSpecializationInfo: null() },
            layout: pl, basePipelineHandle: 0, basePipelineIndex: -1 };
        let mut p: H = 0;
        verifie(create_cp(self.dev, 0, 1, &cpci, null(), &mut p), "vkCreateComputePipelines (le SPIR-V refusé ?)")?;
        self.pipelines.push((cle, p));
        Ok(p)
    }

    unsafe fn tampon(&self, taille: u64, usage: u32, voulu: u32) -> Result<(H, H), String> {
        let create_buffer = vkfn!(self, "vkCreateBuffer", unsafe extern "system" fn(Ptr, *const BufferCreateInfo, *const c_void, *mut H) -> R);
        let reqs = vkfn!(self, "vkGetBufferMemoryRequirements", unsafe extern "system" fn(Ptr, H, *mut MemoryRequirements));
        let alloc = vkfn!(self, "vkAllocateMemory", unsafe extern "system" fn(Ptr, *const MemoryAllocateInfo, *const c_void, *mut H) -> R);
        let bind = vkfn!(self, "vkBindBufferMemory", unsafe extern "system" fn(Ptr, H, H, u64) -> R);
        let bci = BufferCreateInfo { sType: ST_BUFFER_CREATE_INFO, pNext: null(), flags: 0, size: taille, usage,
            sharingMode: 0, queueFamilyIndexCount: 0, pQueueFamilyIndices: null() };
        let mut b: H = 0;
        verifie(create_buffer(self.dev, &bci, null(), &mut b), "vkCreateBuffer")?;
        let mut mr = MemoryRequirements::default();
        reqs(self.dev, b, &mut mr);
        let ty = (0..self.mp.memoryTypeCount)
            .find(|&k| mr.memoryTypeBits & (1 << k) != 0 && self.mp.memoryTypes[k as usize].propertyFlags & voulu == voulu)
            .ok_or(format!("aucune mémoire du type {:#x}", voulu))?;
        let mai = MemoryAllocateInfo { sType: ST_MEMORY_ALLOCATE_INFO, pNext: null(), allocationSize: mr.size, memoryTypeIndex: ty };
        let mut m: H = 0;
        verifie(alloc(self.dev, &mai, null(), &mut m), "vkAllocateMemory")?;
        verifie(bind(self.dev, b, m, 0), "vkBindBufferMemory")?;
        Ok((b, m))
    }

    /// le noyau sur `fils` fils ; la fenêtre et les paramètres montent, puis redescendent (p[5] est rempli ici) ;
    /// vide : la fenêtre n'a que des zéros (elle n'est pas copiée : la carte la remplit elle-même) ; rend les
    /// millisecondes : préparer et monter, la carte (copies dans la carte, calcul, attente), redescendre
    pub fn lancer(&mut self, spv: &[u32], fenetre: &mut [u64], params: &mut [u64], fils: u64, vide: bool) -> Result<[f64; 3], String> {
        unsafe { self.lancer_(spv, fenetre, params, fils, vide) }
    }

    unsafe fn lancer_(&mut self, spv: &[u32], fenetre: &mut [u64], params: &mut [u64], fils: u64, vide: bool) -> Result<[f64; 3], String> {
        let t0 = std::time::Instant::now();
        let tf = (fenetre.len().max(1) * 8) as u64;
        let tp = (params.len() * 8) as u64;
        if tf > self.stockage_max {
            return Err(format!("fenêtre de {} octets : la carte en prend {} au plus par tampon", tf, self.stockage_max));
        }
        let groupes = fils.div_ceil(LARGEUR).max(1);
        let gx = groupes.min(self.groupes_max);
        let gy = groupes.div_ceil(gx);
        if gy > self.groupes_max {
            return Err("trop de fils".into());
        }
        params[5] = gx * LARGEUR;
        let pipeline = self.pipeline(spv)?;
        let (bdev, mdev) = self.tampon(tf, BUFFER_USAGE_STORAGE | BUFFER_USAGE_TRANSFER_SRC | BUFFER_USAGE_TRANSFER_DST, MEM_DEVICE_LOCAL)?;
        // le passage : une mémoire visible du processeur et cachée (relire une mémoire non cachée est très lent)
        let (bpas, mpas) = match self.tampon(tf, BUFFER_USAGE_TRANSFER_SRC | BUFFER_USAGE_TRANSFER_DST, MEM_HOST_VISIBLE | MEM_HOST_COHERENT | MEM_HOST_CACHED) {
            Ok(x) => x,
            Err(_) => self.tampon(tf, BUFFER_USAGE_TRANSFER_SRC | BUFFER_USAGE_TRANSFER_DST, MEM_HOST_VISIBLE | MEM_HOST_COHERENT)?,
        };
        let (bpar, mpar) = self.tampon(tp, BUFFER_USAGE_STORAGE, MEM_HOST_VISIBLE | MEM_HOST_COHERENT)?;
        let map = vkfn!(self, "vkMapMemory", unsafe extern "system" fn(Ptr, H, u64, u64, u32, *mut *mut c_void) -> R);
        let mut vf: *mut c_void = null_mut();
        let mut vp: *mut c_void = null_mut();
        verifie(map(self.dev, mpas, 0, tf, 0, &mut vf), "vkMapMemory")?;
        verifie(map(self.dev, mpar, 0, tp, 0, &mut vp), "vkMapMemory")?;
        if !vide {
            std::ptr::copy_nonoverlapping(fenetre.as_ptr(), vf as *mut u64, fenetre.len());
        }
        std::ptr::copy_nonoverlapping(params.as_ptr(), vp as *mut u64, params.len());
        // les liaisons
        let taille_pool = DescriptorPoolSize { ty: DESCRIPTOR_STORAGE_BUFFER, descriptorCount: 2 };
        let create_dp = vkfn!(self, "vkCreateDescriptorPool", unsafe extern "system" fn(Ptr, *const DescriptorPoolCreateInfo, *const c_void, *mut H) -> R);
        let dpci = DescriptorPoolCreateInfo { sType: ST_DESCRIPTOR_POOL_CREATE_INFO, pNext: null(), flags: 0, maxSets: 1,
            poolSizeCount: 1, pPoolSizes: &taille_pool };
        let mut dp: H = 0;
        verifie(create_dp(self.dev, &dpci, null(), &mut dp), "vkCreateDescriptorPool")?;
        let alloc_ds = vkfn!(self, "vkAllocateDescriptorSets", unsafe extern "system" fn(Ptr, *const DescriptorSetAllocateInfo, *mut H) -> R);
        let dsai = DescriptorSetAllocateInfo { sType: ST_DESCRIPTOR_SET_ALLOCATE_INFO, pNext: null(), descriptorPool: dp,
            descriptorSetCount: 1, pSetLayouts: &self.dsl };
        let mut ds: H = 0;
        verifie(alloc_ds(self.dev, &dsai, &mut ds), "vkAllocateDescriptorSets")?;
        let infos = [DescriptorBufferInfo { buffer: bdev, offset: 0, range: tf },
                     DescriptorBufferInfo { buffer: bpar, offset: 0, range: tp }];
        let ecr = [0u32, 1].map(|k| WriteDescriptorSet { sType: ST_WRITE_DESCRIPTOR_SET, pNext: null(), dstSet: ds,
            dstBinding: k, dstArrayElement: 0, descriptorCount: 1, descriptorType: DESCRIPTOR_STORAGE_BUFFER,
            pImageInfo: null(), pBufferInfo: &infos[k as usize], pTexelBufferView: null() });
        let update_ds = vkfn!(self, "vkUpdateDescriptorSets", unsafe extern "system" fn(Ptr, u32, *const WriteDescriptorSet, u32, *const c_void));
        update_ds(self.dev, 2, ecr.as_ptr(), 0, null());
        // les commandes : monter, calculer, redescendre
        let reset_pool = vkfn!(self, "vkResetCommandPool", unsafe extern "system" fn(Ptr, H, u32) -> R);
        let begin = vkfn!(self, "vkBeginCommandBuffer", unsafe extern "system" fn(Ptr, *const CommandBufferBeginInfo) -> R);
        let bind_p = vkfn!(self, "vkCmdBindPipeline", unsafe extern "system" fn(Ptr, u32, H));
        let bind_ds = vkfn!(self, "vkCmdBindDescriptorSets", unsafe extern "system" fn(Ptr, u32, H, u32, u32, *const H, u32, *const u32));
        let dispatch = vkfn!(self, "vkCmdDispatch", unsafe extern "system" fn(Ptr, u32, u32, u32));
        let barrier = vkfn!(self, "vkCmdPipelineBarrier", unsafe extern "system" fn(Ptr, u32, u32, u32, u32, *const MemoryBarrier, u32, *const c_void, u32, *const c_void));
        let copy = vkfn!(self, "vkCmdCopyBuffer", unsafe extern "system" fn(Ptr, H, H, u32, *const BufferCopy));
        let end = vkfn!(self, "vkEndCommandBuffer", unsafe extern "system" fn(Ptr) -> R);
        let submit = vkfn!(self, "vkQueueSubmit", unsafe extern "system" fn(Ptr, u32, *const SubmitInfo, H) -> R);
        let wait = vkfn!(self, "vkWaitForFences", unsafe extern "system" fn(Ptr, u32, *const H, u32, u64) -> R);
        let reset_f = vkfn!(self, "vkResetFences", unsafe extern "system" fn(Ptr, u32, *const H) -> R);
        verifie(reset_pool(self.dev, self.cpool, 0), "vkResetCommandPool")?;
        let cbbi = CommandBufferBeginInfo { sType: ST_COMMAND_BUFFER_BEGIN_INFO, pNext: null(), flags: 1, pInheritanceInfo: null() };
        verifie(begin(self.cb, &cbbi), "vkBeginCommandBuffer")?;
        let fill = vkfn!(self, "vkCmdFillBuffer", unsafe extern "system" fn(Ptr, H, u64, u64, u32));
        let region = BufferCopy { srcOffset: 0, dstOffset: 0, size: tf };
        if vide {
            fill(self.cb, bdev, 0, tf, 0);
        } else {
            copy(self.cb, bpas, bdev, 1, &region);
        }
        let b1 = MemoryBarrier { sType: ST_MEMORY_BARRIER, pNext: null(), srcAccessMask: ACCESS_TRANSFER_WRITE,
            dstAccessMask: ACCESS_SHADER_READ | ACCESS_SHADER_WRITE };
        barrier(self.cb, STAGE_TRANSFER, STAGE_COMPUTE_SHADER, 0, 1, &b1, 0, null(), 0, null());
        bind_p(self.cb, BIND_POINT_COMPUTE, pipeline);
        bind_ds(self.cb, BIND_POINT_COMPUTE, self.pl, 0, 1, &ds, 0, null());
        dispatch(self.cb, gx as u32, gy as u32, 1);
        let b2 = MemoryBarrier { sType: ST_MEMORY_BARRIER, pNext: null(), srcAccessMask: ACCESS_SHADER_WRITE,
            dstAccessMask: ACCESS_TRANSFER_READ | ACCESS_HOST_READ };
        barrier(self.cb, STAGE_COMPUTE_SHADER, STAGE_TRANSFER | STAGE_HOST, 0, 1, &b2, 0, null(), 0, null());
        copy(self.cb, bdev, bpas, 1, &region);
        let b3 = MemoryBarrier { sType: ST_MEMORY_BARRIER, pNext: null(), srcAccessMask: ACCESS_TRANSFER_WRITE, dstAccessMask: ACCESS_HOST_READ };
        barrier(self.cb, STAGE_TRANSFER, STAGE_HOST, 0, 1, &b3, 0, null(), 0, null());
        verifie(end(self.cb), "vkEndCommandBuffer")?;
        let si = SubmitInfo { sType: ST_SUBMIT_INFO, pNext: null(), waitSemaphoreCount: 0, pWaitSemaphores: null(),
            pWaitDstStageMask: null(), commandBufferCount: 1, pCommandBuffers: &self.cb, signalSemaphoreCount: 0,
            pSignalSemaphores: null() };
        let t1 = std::time::Instant::now();
        verifie(submit(self.file, 1, &si, self.fence), "vkQueueSubmit")?;
        verifie(wait(self.dev, 1, &self.fence, 1, 60_000_000_000), "vkWaitForFences")?;
        verifie(reset_f(self.dev, 1, &self.fence), "vkResetFences")?;
        let t2 = std::time::Instant::now();
        std::ptr::copy_nonoverlapping(vf as *const u64, fenetre.as_mut_ptr(), fenetre.len());
        std::ptr::copy_nonoverlapping(vp as *const u64, params.as_mut_ptr(), params.len());
        // rendre ce qui a servi
        let unmap = vkfn!(self, "vkUnmapMemory", unsafe extern "system" fn(Ptr, H));
        let destroy_b = vkfn!(self, "vkDestroyBuffer", unsafe extern "system" fn(Ptr, H, *const c_void));
        let free_m = vkfn!(self, "vkFreeMemory", unsafe extern "system" fn(Ptr, H, *const c_void));
        let destroy_dp = vkfn!(self, "vkDestroyDescriptorPool", unsafe extern "system" fn(Ptr, H, *const c_void));
        unmap(self.dev, mpas);
        unmap(self.dev, mpar);
        destroy_dp(self.dev, dp, null());
        for (b, m) in [(bdev, mdev), (bpas, mpas), (bpar, mpar)] {
            destroy_b(self.dev, b, null());
            free_m(self.dev, m, null());
        }
        let ms = |a: std::time::Instant, b: std::time::Instant| (b - a).as_secs_f64() * 1e3;
        Ok([ms(t0, t1), ms(t1, t2), t2.elapsed().as_secs_f64() * 1e3])
    }
}

impl Carte {
    /// 0.816 : le noyau en mode pages sur `fils` fils : les pages montent (et redescendent), la table et les paramètres
    /// aussi ; les marques (lue, écrite) de chaque page redescendent ; les auteurs restent dans la carte (remis à zéro).
    /// Rend les millisecondes (préparer et monter, la carte, redescendre) et les marques.
    pub fn lancer_pages(&mut self, spv: &[u32], pages: &mut [u64], table: &[u32], params: &mut [u64], fils: u64)
                        -> Result<([f64; 3], Vec<u32>), String> {
        unsafe { self.lancer_pages_(spv, pages, table, params, fils) }
    }

    unsafe fn lancer_pages_(&mut self, spv: &[u32], pages: &mut [u64], table: &[u32], params: &mut [u64], fils: u64)
                            -> Result<([f64; 3], Vec<u32>), String> {
        let t0 = std::time::Instant::now();
        let nplaces = pages.len() / 65536;
        let tf = (pages.len().max(1) * 8) as u64;
        let tp = (params.len() * 8) as u64;
        let tt = (table.len() * 4) as u64;
        // les marques : lue, écrite, pour chaque page ; puis la demande de chaque page absente (65536 + 1)
        let nmarques = nplaces.max(1) * 2 + 65537;
        let tm = (nmarques * 4) as u64;
        let ta = (nplaces.max(1) * 65536 * 4) as u64;
        if tf > self.stockage_max || ta > self.stockage_max {
            return Err(format!("pages de {} octets : la carte en prend {} au plus par tampon", tf, self.stockage_max));
        }
        let groupes = fils.div_ceil(LARGEUR).max(1);
        let gx = groupes.min(self.groupes_max);
        let gy = groupes.div_ceil(gx);
        if gy > self.groupes_max {
            return Err("trop de fils".into());
        }
        params[5] = gx * LARGEUR;
        let pl = self.mise_en_page5()?;
        let pipeline = self.pipeline_avec(spv, pl)?;
        let stock = BUFFER_USAGE_STORAGE | BUFFER_USAGE_TRANSFER_SRC | BUFFER_USAGE_TRANSFER_DST;
        let (bdev, mdev) = self.tampon(tf, stock, MEM_DEVICE_LOCAL)?;
        let (baut, maut) = self.tampon(ta, stock, MEM_DEVICE_LOCAL)?;
        let (bpas, mpas) = match self.tampon(tf, BUFFER_USAGE_TRANSFER_SRC | BUFFER_USAGE_TRANSFER_DST, MEM_HOST_VISIBLE | MEM_HOST_COHERENT | MEM_HOST_CACHED) {
            Ok(x) => x,
            Err(_) => self.tampon(tf, BUFFER_USAGE_TRANSFER_SRC | BUFFER_USAGE_TRANSFER_DST, MEM_HOST_VISIBLE | MEM_HOST_COHERENT)?,
        };
        let (bpar, mpar) = self.tampon(tp, BUFFER_USAGE_STORAGE, MEM_HOST_VISIBLE | MEM_HOST_COHERENT)?;
        let (btab, mtab) = self.tampon(tt, BUFFER_USAGE_STORAGE, MEM_HOST_VISIBLE | MEM_HOST_COHERENT)?;
        let (bmar, mmar) = self.tampon(tm, BUFFER_USAGE_STORAGE, MEM_HOST_VISIBLE | MEM_HOST_COHERENT)?;
        let map = vkfn!(self, "vkMapMemory", unsafe extern "system" fn(Ptr, H, u64, u64, u32, *mut *mut c_void) -> R);
        let (mut vf, mut vp, mut vt, mut vm): (*mut c_void, *mut c_void, *mut c_void, *mut c_void) = (null_mut(), null_mut(), null_mut(), null_mut());
        verifie(map(self.dev, mpas, 0, tf, 0, &mut vf), "vkMapMemory")?;
        verifie(map(self.dev, mpar, 0, tp, 0, &mut vp), "vkMapMemory")?;
        verifie(map(self.dev, mtab, 0, tt, 0, &mut vt), "vkMapMemory")?;
        verifie(map(self.dev, mmar, 0, tm, 0, &mut vm), "vkMapMemory")?;
        std::ptr::copy_nonoverlapping(pages.as_ptr(), vf as *mut u64, pages.len());
        std::ptr::copy_nonoverlapping(params.as_ptr(), vp as *mut u64, params.len());
        std::ptr::copy_nonoverlapping(table.as_ptr(), vt as *mut u32, table.len());
        std::ptr::write_bytes(vm as *mut u8, 0, tm as usize);
        let taille_pool = DescriptorPoolSize { ty: DESCRIPTOR_STORAGE_BUFFER, descriptorCount: 5 };
        let create_dp = vkfn!(self, "vkCreateDescriptorPool", unsafe extern "system" fn(Ptr, *const DescriptorPoolCreateInfo, *const c_void, *mut H) -> R);
        let dpci = DescriptorPoolCreateInfo { sType: ST_DESCRIPTOR_POOL_CREATE_INFO, pNext: null(), flags: 0, maxSets: 1,
            poolSizeCount: 1, pPoolSizes: &taille_pool };
        let mut dp: H = 0;
        verifie(create_dp(self.dev, &dpci, null(), &mut dp), "vkCreateDescriptorPool")?;
        let alloc_ds = vkfn!(self, "vkAllocateDescriptorSets", unsafe extern "system" fn(Ptr, *const DescriptorSetAllocateInfo, *mut H) -> R);
        let dsai = DescriptorSetAllocateInfo { sType: ST_DESCRIPTOR_SET_ALLOCATE_INFO, pNext: null(), descriptorPool: dp,
            descriptorSetCount: 1, pSetLayouts: &self.dsl5 };
        let mut ds: H = 0;
        verifie(alloc_ds(self.dev, &dsai, &mut ds), "vkAllocateDescriptorSets")?;
        let infos = [DescriptorBufferInfo { buffer: bdev, offset: 0, range: tf },
                     DescriptorBufferInfo { buffer: bpar, offset: 0, range: tp },
                     DescriptorBufferInfo { buffer: btab, offset: 0, range: tt },
                     DescriptorBufferInfo { buffer: bmar, offset: 0, range: tm },
                     DescriptorBufferInfo { buffer: baut, offset: 0, range: ta }];
        let ecr = [0u32, 1, 2, 3, 4].map(|k| WriteDescriptorSet { sType: ST_WRITE_DESCRIPTOR_SET, pNext: null(), dstSet: ds,
            dstBinding: k, dstArrayElement: 0, descriptorCount: 1, descriptorType: DESCRIPTOR_STORAGE_BUFFER,
            pImageInfo: null(), pBufferInfo: &infos[k as usize], pTexelBufferView: null() });
        let update_ds = vkfn!(self, "vkUpdateDescriptorSets", unsafe extern "system" fn(Ptr, u32, *const WriteDescriptorSet, u32, *const c_void));
        update_ds(self.dev, 5, ecr.as_ptr(), 0, null());
        let reset_pool = vkfn!(self, "vkResetCommandPool", unsafe extern "system" fn(Ptr, H, u32) -> R);
        let begin = vkfn!(self, "vkBeginCommandBuffer", unsafe extern "system" fn(Ptr, *const CommandBufferBeginInfo) -> R);
        let bind_p = vkfn!(self, "vkCmdBindPipeline", unsafe extern "system" fn(Ptr, u32, H));
        let bind_ds = vkfn!(self, "vkCmdBindDescriptorSets", unsafe extern "system" fn(Ptr, u32, H, u32, u32, *const H, u32, *const u32));
        let dispatch = vkfn!(self, "vkCmdDispatch", unsafe extern "system" fn(Ptr, u32, u32, u32));
        let barrier = vkfn!(self, "vkCmdPipelineBarrier", unsafe extern "system" fn(Ptr, u32, u32, u32, u32, *const MemoryBarrier, u32, *const c_void, u32, *const c_void));
        let copy = vkfn!(self, "vkCmdCopyBuffer", unsafe extern "system" fn(Ptr, H, H, u32, *const BufferCopy));
        let fill = vkfn!(self, "vkCmdFillBuffer", unsafe extern "system" fn(Ptr, H, u64, u64, u32));
        let end = vkfn!(self, "vkEndCommandBuffer", unsafe extern "system" fn(Ptr) -> R);
        let submit = vkfn!(self, "vkQueueSubmit", unsafe extern "system" fn(Ptr, u32, *const SubmitInfo, H) -> R);
        let wait = vkfn!(self, "vkWaitForFences", unsafe extern "system" fn(Ptr, u32, *const H, u32, u64) -> R);
        let reset_f = vkfn!(self, "vkResetFences", unsafe extern "system" fn(Ptr, u32, *const H) -> R);
        verifie(reset_pool(self.dev, self.cpool, 0), "vkResetCommandPool")?;
        let cbbi = CommandBufferBeginInfo { sType: ST_COMMAND_BUFFER_BEGIN_INFO, pNext: null(), flags: 1, pInheritanceInfo: null() };
        verifie(begin(self.cb, &cbbi), "vkBeginCommandBuffer")?;
        let region = BufferCopy { srcOffset: 0, dstOffset: 0, size: tf };
        copy(self.cb, bpas, bdev, 1, &region);
        fill(self.cb, baut, 0, ta, 0);
        let b1 = MemoryBarrier { sType: ST_MEMORY_BARRIER, pNext: null(), srcAccessMask: ACCESS_TRANSFER_WRITE,
            dstAccessMask: ACCESS_SHADER_READ | ACCESS_SHADER_WRITE };
        barrier(self.cb, STAGE_TRANSFER, STAGE_COMPUTE_SHADER, 0, 1, &b1, 0, null(), 0, null());
        bind_p(self.cb, BIND_POINT_COMPUTE, pipeline);
        bind_ds(self.cb, BIND_POINT_COMPUTE, pl, 0, 1, &ds, 0, null());
        dispatch(self.cb, gx as u32, gy as u32, 1);
        let b2 = MemoryBarrier { sType: ST_MEMORY_BARRIER, pNext: null(), srcAccessMask: ACCESS_SHADER_WRITE,
            dstAccessMask: ACCESS_TRANSFER_READ | ACCESS_HOST_READ };
        barrier(self.cb, STAGE_COMPUTE_SHADER, STAGE_TRANSFER | STAGE_HOST, 0, 1, &b2, 0, null(), 0, null());
        copy(self.cb, bdev, bpas, 1, &region);
        let b3 = MemoryBarrier { sType: ST_MEMORY_BARRIER, pNext: null(), srcAccessMask: ACCESS_TRANSFER_WRITE, dstAccessMask: ACCESS_HOST_READ };
        barrier(self.cb, STAGE_TRANSFER, STAGE_HOST, 0, 1, &b3, 0, null(), 0, null());
        verifie(end(self.cb), "vkEndCommandBuffer")?;
        let si = SubmitInfo { sType: ST_SUBMIT_INFO, pNext: null(), waitSemaphoreCount: 0, pWaitSemaphores: null(),
            pWaitDstStageMask: null(), commandBufferCount: 1, pCommandBuffers: &self.cb, signalSemaphoreCount: 0,
            pSignalSemaphores: null() };
        let t1 = std::time::Instant::now();
        verifie(submit(self.file, 1, &si, self.fence), "vkQueueSubmit")?;
        verifie(wait(self.dev, 1, &self.fence, 1, 120_000_000_000), "vkWaitForFences")?;
        verifie(reset_f(self.dev, 1, &self.fence), "vkResetFences")?;
        let t2 = std::time::Instant::now();
        std::ptr::copy_nonoverlapping(vf as *const u64, pages.as_mut_ptr(), pages.len());
        std::ptr::copy_nonoverlapping(vp as *const u64, params.as_mut_ptr(), params.len());
        let mut marques = vec![0u32; nmarques];
        std::ptr::copy_nonoverlapping(vm as *const u32, marques.as_mut_ptr(), nmarques);
        let unmap = vkfn!(self, "vkUnmapMemory", unsafe extern "system" fn(Ptr, H));
        let destroy_b = vkfn!(self, "vkDestroyBuffer", unsafe extern "system" fn(Ptr, H, *const c_void));
        let free_m = vkfn!(self, "vkFreeMemory", unsafe extern "system" fn(Ptr, H, *const c_void));
        let destroy_dp = vkfn!(self, "vkDestroyDescriptorPool", unsafe extern "system" fn(Ptr, H, *const c_void));
        for m in [mpas, mpar, mtab, mmar] {
            unmap(self.dev, m);
        }
        destroy_dp(self.dev, dp, null());
        for (b, m) in [(bdev, mdev), (baut, maut), (bpas, mpas), (bpar, mpar), (btab, mtab), (bmar, mmar)] {
            destroy_b(self.dev, b, null());
            free_m(self.dev, m, null());
        }
        let ms = |a: std::time::Instant, b: std::time::Instant| (b - a).as_secs_f64() * 1e3;
        Ok(([ms(t0, t1), ms(t1, t2), t2.elapsed().as_secs_f64() * 1e3], marques))
    }
}

/// 0.817 : la résidence : le cube gardé sur la carte d'un lancement à l'autre. Les pages vivent dans un tampon de la
/// carte (une place par page) ; un tampon du processeur, visible des deux, en est le miroir exact (ce que la carte a) :
/// avant un lancement, seules les places dont la page a changé y sont recopiées et montent ; après, seules les places
/// écrites redescendent.
pub struct Residence {
    pub cap: usize,
    bdev: H,
    mdev: H,
    baut: H,
    maut: H,
    bmir: H,
    mmir: H,
    pub miroir: *mut u64,
    bpar: H,
    mpar: H,
    vpar: *mut u64,
    btab: H,
    mtab: H,
    vtab: *mut u32,
    bmar: H,
    mmar: H,
    vmar: *mut u32,
    dp: H,
    ds: H,
}

const PARAMS_RES: usize = 512;

impl Carte {
    /// une résidence d'au moins `cap` places (une nouvelle, vide, si la précédente est trop petite : rend vrai)
    pub fn residence(&mut self, res: &mut Option<Residence>, cap: usize) -> Result<bool, String> {
        unsafe { self.residence_(res, cap) }
    }

    unsafe fn residence_(&mut self, res: &mut Option<Residence>, cap: usize) -> Result<bool, String> {
        if res.as_ref().map_or(false, |r| r.cap >= cap) {
            return Ok(false);
        }
        if let Some(r) = res.take() {
            self.liberer(r);
        }
        // de la marge (la moitié en plus), sans dépasser ce que la carte prend par tampon
        let max_places = (self.stockage_max / (65536 * 8)) as usize;
        let cap = (cap + cap / 2).max(16).min(max_places.max(cap));
        let tf = (cap * 65536 * 8) as u64;
        let ta = (cap * 65536 * 4) as u64;
        if tf > self.stockage_max {
            return Err(format!("{} pages : {} octets, la carte en prend {} au plus par tampon", cap, tf, self.stockage_max));
        }
        let stock = BUFFER_USAGE_STORAGE | BUFFER_USAGE_TRANSFER_SRC | BUFFER_USAGE_TRANSFER_DST;
        let (bdev, mdev) = self.tampon(tf, stock, MEM_DEVICE_LOCAL)?;
        let (baut, maut) = self.tampon(ta, stock, MEM_DEVICE_LOCAL)?;
        let (bmir, mmir) = match self.tampon(tf, BUFFER_USAGE_TRANSFER_SRC | BUFFER_USAGE_TRANSFER_DST, MEM_HOST_VISIBLE | MEM_HOST_COHERENT | MEM_HOST_CACHED) {
            Ok(x) => x,
            Err(_) => self.tampon(tf, BUFFER_USAGE_TRANSFER_SRC | BUFFER_USAGE_TRANSFER_DST, MEM_HOST_VISIBLE | MEM_HOST_COHERENT)?,
        };
        let tp = (PARAMS_RES * 8) as u64;
        let tt = (65536 * 4) as u64;
        let tm = ((cap * 2 + 65537) * 4) as u64;
        let (bpar, mpar) = self.tampon(tp, BUFFER_USAGE_STORAGE, MEM_HOST_VISIBLE | MEM_HOST_COHERENT)?;
        let (btab, mtab) = self.tampon(tt, BUFFER_USAGE_STORAGE, MEM_HOST_VISIBLE | MEM_HOST_COHERENT)?;
        let (bmar, mmar) = self.tampon(tm, BUFFER_USAGE_STORAGE, MEM_HOST_VISIBLE | MEM_HOST_COHERENT)?;
        let map = vkfn!(self, "vkMapMemory", unsafe extern "system" fn(Ptr, H, u64, u64, u32, *mut *mut c_void) -> R);
        let (mut a, mut b, mut c, mut d): (*mut c_void, *mut c_void, *mut c_void, *mut c_void) = (null_mut(), null_mut(), null_mut(), null_mut());
        verifie(map(self.dev, mmir, 0, tf, 0, &mut a), "vkMapMemory")?;
        verifie(map(self.dev, mpar, 0, tp, 0, &mut b), "vkMapMemory")?;
        verifie(map(self.dev, mtab, 0, tt, 0, &mut c), "vkMapMemory")?;
        verifie(map(self.dev, mmar, 0, tm, 0, &mut d), "vkMapMemory")?;
        let pl = self.mise_en_page5()?;
        let _ = pl;
        let taille_pool = DescriptorPoolSize { ty: DESCRIPTOR_STORAGE_BUFFER, descriptorCount: 5 };
        let create_dp = vkfn!(self, "vkCreateDescriptorPool", unsafe extern "system" fn(Ptr, *const DescriptorPoolCreateInfo, *const c_void, *mut H) -> R);
        let dpci = DescriptorPoolCreateInfo { sType: ST_DESCRIPTOR_POOL_CREATE_INFO, pNext: null(), flags: 0, maxSets: 1,
            poolSizeCount: 1, pPoolSizes: &taille_pool };
        let mut dp: H = 0;
        verifie(create_dp(self.dev, &dpci, null(), &mut dp), "vkCreateDescriptorPool")?;
        let alloc_ds = vkfn!(self, "vkAllocateDescriptorSets", unsafe extern "system" fn(Ptr, *const DescriptorSetAllocateInfo, *mut H) -> R);
        let dsai = DescriptorSetAllocateInfo { sType: ST_DESCRIPTOR_SET_ALLOCATE_INFO, pNext: null(), descriptorPool: dp,
            descriptorSetCount: 1, pSetLayouts: &self.dsl5 };
        let mut ds: H = 0;
        verifie(alloc_ds(self.dev, &dsai, &mut ds), "vkAllocateDescriptorSets")?;
        let infos = [DescriptorBufferInfo { buffer: bdev, offset: 0, range: tf },
                     DescriptorBufferInfo { buffer: bpar, offset: 0, range: tp },
                     DescriptorBufferInfo { buffer: btab, offset: 0, range: tt },
                     DescriptorBufferInfo { buffer: bmar, offset: 0, range: tm },
                     DescriptorBufferInfo { buffer: baut, offset: 0, range: ta }];
        let ecr = [0u32, 1, 2, 3, 4].map(|k| WriteDescriptorSet { sType: ST_WRITE_DESCRIPTOR_SET, pNext: null(), dstSet: ds,
            dstBinding: k, dstArrayElement: 0, descriptorCount: 1, descriptorType: DESCRIPTOR_STORAGE_BUFFER,
            pImageInfo: null(), pBufferInfo: &infos[k as usize], pTexelBufferView: null() });
        let update_ds = vkfn!(self, "vkUpdateDescriptorSets", unsafe extern "system" fn(Ptr, u32, *const WriteDescriptorSet, u32, *const c_void));
        update_ds(self.dev, 5, ecr.as_ptr(), 0, null());
        *res = Some(Residence { cap, bdev, mdev, baut, maut, bmir, mmir, miroir: a as *mut u64, bpar, mpar, vpar: b as *mut u64,
            btab, mtab, vtab: c as *mut u32, bmar, mmar, vmar: d as *mut u32, dp, ds });
        Ok(true)
    }

    unsafe fn liberer(&mut self, r: Residence) {
        let _ = self.liberer_(r);
    }

    unsafe fn liberer_(&mut self, r: Residence) -> Result<(), String> {
        let wait_idle = vkfn!(self, "vkDeviceWaitIdle", unsafe extern "system" fn(Ptr) -> R);
        let _ = wait_idle(self.dev);
        let unmap = vkfn!(self, "vkUnmapMemory", unsafe extern "system" fn(Ptr, H));
        let destroy_b = vkfn!(self, "vkDestroyBuffer", unsafe extern "system" fn(Ptr, H, *const c_void));
        let free_m = vkfn!(self, "vkFreeMemory", unsafe extern "system" fn(Ptr, H, *const c_void));
        let destroy_dp = vkfn!(self, "vkDestroyDescriptorPool", unsafe extern "system" fn(Ptr, H, *const c_void));
        for m in [r.mmir, r.mpar, r.mtab, r.mmar] {
            unmap(self.dev, m);
        }
        destroy_dp(self.dev, r.dp, null());
        for (b, m) in [(r.bdev, r.mdev), (r.baut, r.maut), (r.bmir, r.mmir), (r.bpar, r.mpar), (r.btab, r.mtab), (r.bmar, r.mmar)] {
            destroy_b(self.dev, b, null());
            free_m(self.dev, m, null());
        }
        Ok(())
    }

    /// lancer en résidence : `montees` (des places) montent du miroir ; la table et les paramètres sont recopiés ;
    /// rend les millisecondes (préparer, la carte) et les marques (lue, écrite par place ; puis les demandes)
    pub fn lancer_resident(&mut self, r: &mut Residence, spv: &[u32], montees: &[u32], table: &[u32], params: &mut [u64],
                           fils: u64) -> Result<([f64; 2], Vec<u32>), String> {
        unsafe { self.lancer_resident_(r, spv, montees, table, params, fils) }
    }

    unsafe fn lancer_resident_(&mut self, r: &mut Residence, spv: &[u32], montees: &[u32], table: &[u32], params: &mut [u64],
                               fils: u64) -> Result<([f64; 2], Vec<u32>), String> {
        let t0 = std::time::Instant::now();
        if params.len() > PARAMS_RES {
            return Err("trop de paramètres".into());
        }
        let groupes = fils.div_ceil(LARGEUR).max(1);
        let gx = groupes.min(self.groupes_max);
        let gy = groupes.div_ceil(gx);
        if gy > self.groupes_max {
            return Err("trop de fils".into());
        }
        params[5] = gx * LARGEUR;
        let pl = self.mise_en_page5()?;
        let pipeline = self.pipeline_avec(spv, pl)?;
        let nmarques = r.cap * 2 + 65537;
        std::ptr::copy_nonoverlapping(params.as_ptr(), r.vpar, params.len());
        std::ptr::copy_nonoverlapping(table.as_ptr(), r.vtab, table.len().min(65536));
        std::ptr::write_bytes(r.vmar, 0, nmarques);
        let reset_pool = vkfn!(self, "vkResetCommandPool", unsafe extern "system" fn(Ptr, H, u32) -> R);
        let begin = vkfn!(self, "vkBeginCommandBuffer", unsafe extern "system" fn(Ptr, *const CommandBufferBeginInfo) -> R);
        let bind_p = vkfn!(self, "vkCmdBindPipeline", unsafe extern "system" fn(Ptr, u32, H));
        let bind_ds = vkfn!(self, "vkCmdBindDescriptorSets", unsafe extern "system" fn(Ptr, u32, H, u32, u32, *const H, u32, *const u32));
        let dispatch = vkfn!(self, "vkCmdDispatch", unsafe extern "system" fn(Ptr, u32, u32, u32));
        let barrier = vkfn!(self, "vkCmdPipelineBarrier", unsafe extern "system" fn(Ptr, u32, u32, u32, u32, *const MemoryBarrier, u32, *const c_void, u32, *const c_void));
        let copy = vkfn!(self, "vkCmdCopyBuffer", unsafe extern "system" fn(Ptr, H, H, u32, *const BufferCopy));
        let fill = vkfn!(self, "vkCmdFillBuffer", unsafe extern "system" fn(Ptr, H, u64, u64, u32));
        let end = vkfn!(self, "vkEndCommandBuffer", unsafe extern "system" fn(Ptr) -> R);
        let submit = vkfn!(self, "vkQueueSubmit", unsafe extern "system" fn(Ptr, u32, *const SubmitInfo, H) -> R);
        let wait = vkfn!(self, "vkWaitForFences", unsafe extern "system" fn(Ptr, u32, *const H, u32, u64) -> R);
        let reset_f = vkfn!(self, "vkResetFences", unsafe extern "system" fn(Ptr, u32, *const H) -> R);
        verifie(reset_pool(self.dev, self.cpool, 0), "vkResetCommandPool")?;
        let cbbi = CommandBufferBeginInfo { sType: ST_COMMAND_BUFFER_BEGIN_INFO, pNext: null(), flags: 1, pInheritanceInfo: null() };
        verifie(begin(self.cb, &cbbi), "vkBeginCommandBuffer")?;
        let regions: Vec<BufferCopy> = montees.iter().map(|&s| BufferCopy { srcOffset: s as u64 * 524288,
            dstOffset: s as u64 * 524288, size: 524288 }).collect();
        if !regions.is_empty() {
            copy(self.cb, r.bmir, r.bdev, regions.len() as u32, regions.as_ptr());
        }
        fill(self.cb, r.baut, 0, (r.cap * 65536 * 4) as u64, 0);
        let b1 = MemoryBarrier { sType: ST_MEMORY_BARRIER, pNext: null(), srcAccessMask: ACCESS_TRANSFER_WRITE,
            dstAccessMask: ACCESS_SHADER_READ | ACCESS_SHADER_WRITE };
        barrier(self.cb, STAGE_TRANSFER, STAGE_COMPUTE_SHADER, 0, 1, &b1, 0, null(), 0, null());
        bind_p(self.cb, BIND_POINT_COMPUTE, pipeline);
        bind_ds(self.cb, BIND_POINT_COMPUTE, pl, 0, 1, &r.ds, 0, null());
        dispatch(self.cb, gx as u32, gy as u32, 1);
        let b2 = MemoryBarrier { sType: ST_MEMORY_BARRIER, pNext: null(), srcAccessMask: ACCESS_SHADER_WRITE,
            dstAccessMask: ACCESS_TRANSFER_READ | ACCESS_HOST_READ };
        barrier(self.cb, STAGE_COMPUTE_SHADER, STAGE_TRANSFER | STAGE_HOST, 0, 1, &b2, 0, null(), 0, null());
        verifie(end(self.cb), "vkEndCommandBuffer")?;
        let si = SubmitInfo { sType: ST_SUBMIT_INFO, pNext: null(), waitSemaphoreCount: 0, pWaitSemaphores: null(),
            pWaitDstStageMask: null(), commandBufferCount: 1, pCommandBuffers: &self.cb, signalSemaphoreCount: 0,
            pSignalSemaphores: null() };
        let t1 = std::time::Instant::now();
        verifie(submit(self.file, 1, &si, self.fence), "vkQueueSubmit")?;
        verifie(wait(self.dev, 1, &self.fence, 1, 120_000_000_000), "vkWaitForFences")?;
        verifie(reset_f(self.dev, 1, &self.fence), "vkResetFences")?;
        let t2 = std::time::Instant::now();
        std::ptr::copy_nonoverlapping(r.vpar as *const u64, params.as_mut_ptr(), params.len());
        let mut marques = vec![0u32; nmarques];
        std::ptr::copy_nonoverlapping(r.vmar as *const u32, marques.as_mut_ptr(), nmarques);
        let ms = |a: std::time::Instant, b: std::time::Instant| (b - a).as_secs_f64() * 1e3;
        Ok(([ms(t0, t1), ms(t1, t2)], marques))
    }

    /// les places écrites redescendent dans le miroir ; rend les millisecondes
    pub fn redescendre(&mut self, r: &mut Residence, places: &[u32]) -> Result<f64, String> {
        unsafe {
            let t0 = std::time::Instant::now();
            if places.is_empty() {
                return Ok(0.0);
            }
            let reset_pool = vkfn!(self, "vkResetCommandPool", unsafe extern "system" fn(Ptr, H, u32) -> R);
            let begin = vkfn!(self, "vkBeginCommandBuffer", unsafe extern "system" fn(Ptr, *const CommandBufferBeginInfo) -> R);
            let barrier = vkfn!(self, "vkCmdPipelineBarrier", unsafe extern "system" fn(Ptr, u32, u32, u32, u32, *const MemoryBarrier, u32, *const c_void, u32, *const c_void));
            let copy = vkfn!(self, "vkCmdCopyBuffer", unsafe extern "system" fn(Ptr, H, H, u32, *const BufferCopy));
            let end = vkfn!(self, "vkEndCommandBuffer", unsafe extern "system" fn(Ptr) -> R);
            let submit = vkfn!(self, "vkQueueSubmit", unsafe extern "system" fn(Ptr, u32, *const SubmitInfo, H) -> R);
            let wait = vkfn!(self, "vkWaitForFences", unsafe extern "system" fn(Ptr, u32, *const H, u32, u64) -> R);
            let reset_f = vkfn!(self, "vkResetFences", unsafe extern "system" fn(Ptr, u32, *const H) -> R);
            verifie(reset_pool(self.dev, self.cpool, 0), "vkResetCommandPool")?;
            let cbbi = CommandBufferBeginInfo { sType: ST_COMMAND_BUFFER_BEGIN_INFO, pNext: null(), flags: 1, pInheritanceInfo: null() };
            verifie(begin(self.cb, &cbbi), "vkBeginCommandBuffer")?;
            let regions: Vec<BufferCopy> = places.iter().map(|&s| BufferCopy { srcOffset: s as u64 * 524288,
                dstOffset: s as u64 * 524288, size: 524288 }).collect();
            copy(self.cb, r.bdev, r.bmir, regions.len() as u32, regions.as_ptr());
            let b3 = MemoryBarrier { sType: ST_MEMORY_BARRIER, pNext: null(), srcAccessMask: ACCESS_TRANSFER_WRITE, dstAccessMask: ACCESS_HOST_READ };
            barrier(self.cb, STAGE_TRANSFER, STAGE_HOST, 0, 1, &b3, 0, null(), 0, null());
            verifie(end(self.cb), "vkEndCommandBuffer")?;
            let si = SubmitInfo { sType: ST_SUBMIT_INFO, pNext: null(), waitSemaphoreCount: 0, pWaitSemaphores: null(),
                pWaitDstStageMask: null(), commandBufferCount: 1, pCommandBuffers: &self.cb, signalSemaphoreCount: 0,
                pSignalSemaphores: null() };
            verifie(submit(self.file, 1, &si, self.fence), "vkQueueSubmit")?;
            verifie(wait(self.dev, 1, &self.fence, 1, 120_000_000_000), "vkWaitForFences")?;
            verifie(reset_f(self.dev, 1, &self.fence), "vkResetFences")?;
            Ok(t0.elapsed().as_secs_f64() * 1e3)
        }
    }
}
