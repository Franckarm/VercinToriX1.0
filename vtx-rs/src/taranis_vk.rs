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
    dsl: H,
    pl: H,
    pipelines: Vec<(usize, H)>,
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
        mp: std::mem::zeroed(), groupes_max: 65535, stockage_max: 1 << 27, nom: String::new(), dsl: 0, pl: 0,
        pipelines: Vec::new(), cpool: 0, cb: null_mut(), fence: 0 };
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
    // les noyaux de vtx calculent les entiers de 64 bits en deux mots de 32 bits : aucune option de la carte n'est demandée
    let _ = feats;
    let voulu = [0u32; 55];
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
            layout: self.pl, basePipelineHandle: 0, basePipelineIndex: -1 };
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
    /// rend les millisecondes de la carte (lancement compris)
    pub fn lancer(&mut self, spv: &[u32], fenetre: &mut [u64], params: &mut [u64], fils: u64) -> Result<f64, String> {
        unsafe { self.lancer_(spv, fenetre, params, fils) }
    }

    unsafe fn lancer_(&mut self, spv: &[u32], fenetre: &mut [u64], params: &mut [u64], fils: u64) -> Result<f64, String> {
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
        let (bpas, mpas) = self.tampon(tf, BUFFER_USAGE_TRANSFER_SRC | BUFFER_USAGE_TRANSFER_DST, MEM_HOST_VISIBLE | MEM_HOST_COHERENT)?;
        let (bpar, mpar) = self.tampon(tp, BUFFER_USAGE_STORAGE, MEM_HOST_VISIBLE | MEM_HOST_COHERENT)?;
        let map = vkfn!(self, "vkMapMemory", unsafe extern "system" fn(Ptr, H, u64, u64, u32, *mut *mut c_void) -> R);
        let mut vf: *mut c_void = null_mut();
        let mut vp: *mut c_void = null_mut();
        verifie(map(self.dev, mpas, 0, tf, 0, &mut vf), "vkMapMemory")?;
        verifie(map(self.dev, mpar, 0, tp, 0, &mut vp), "vkMapMemory")?;
        std::ptr::copy_nonoverlapping(fenetre.as_ptr(), vf as *mut u64, fenetre.len());
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
        let region = BufferCopy { srcOffset: 0, dstOffset: 0, size: tf };
        copy(self.cb, bpas, bdev, 1, &region);
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
        verifie(submit(self.file, 1, &si, self.fence), "vkQueueSubmit")?;
        verifie(wait(self.dev, 1, &self.fence, 1, 60_000_000_000), "vkWaitForFences")?;
        verifie(reset_f(self.dev, 1, &self.fence), "vkResetFences")?;
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
        Ok(t0.elapsed().as_secs_f64() * 1e3)
    }
}
