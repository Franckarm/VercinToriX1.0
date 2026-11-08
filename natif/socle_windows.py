"""Le socle des programmes traduits en x86-64, pour Windows : les primitives OS_* du socle (natif/socle.py) par les
fonctions de KERNEL32 (la seule bibliothèque, toujours là), et la table d'import de l'exécutable PE.

Le reste du socle est commun (sorties, texte, canaux, services, fin) : seules ces primitives parlent au système.
Ce qui change pour Windows :
  - un appel suit la convention de Windows x64 (rcx, rdx, r8, r9, puis la pile ; 32 octets réservés ; la pile alignée
    sur 16 ; r8 à r11 effacés) : chaque primitive garde ce que le socle attend d'elle (tout sauf rax, rcx, rdx) ;
  - les descripteurs 0, 1, 2 du socle sont l'entrée, la sortie et les erreurs (GetStdHandle) ; un fichier ouvert rend
    son handle (un nombre de 32 bits, comme le veut Windows) ;
  - la console passe en UTF-8 (SetConsoleOutputCP, SetConsoleCP) ; une ligne tapée perd son \\r ;
  - les noms de fichiers en UTF-8 deviennent de l'UTF-16 (MultiByteToWideChar) : les accents passent ;
  - la mémoire du SPU (256 Mo) est réservée et engagée d'un coup (VirtualAlloc), remplie de zéros à la demande ;
  - le bruit : le compteur du processeur (rdtsc), brassé ;
  - pas encore : la voix (parler ne dit rien), les cubes rangés par accorder (erreur claire).
"""
from x86 import *  # noqa
from socle import OCTET, ENVP, CHIFFRES, VEC, TAILLE_ETAT  # noqa

# le nom en UTF-16 : juste après la zone d'état (l'exécutable PE réserve EXTRA octets de plus)
CHEMIN16 = TAILLE_ETAT
# le compte d'octets lus ou écrits que Windows rend (pas dans OCTET : le socle y lit et y écrit un caractère)
COMPTE = TAILLE_ETAT + 16384
EXTRA = 16384 + 64
MSG_FERMER = "\n(Entrée pour fermer la fenêtre)".encode("utf-8")

FONCTIONS = ["GetStdHandle", "WriteFile", "ReadFile", "CreateFileW", "CloseHandle", "GetFileSizeEx", "VirtualAlloc",
             "VirtualFree", "ExitProcess", "GetCommandLineA", "SetConsoleOutputCP", "SetConsoleCP",
             "MultiByteToWideChar", "GetConsoleProcessList"]
GARDES = [R8_, R9_, R10_, R11_]


def appel(s, nom, pile=()):
    """Appelle KERNEL32!nom (rcx, rdx, r8, r9 déjà remplis ; pile : les valeurs des arguments 5, 6, 7..., chacune un
    registre ou un nombre) ; r12 garde la pile d'avant. Le résultat dans rax."""
    a = s.a
    a.push(R12_)
    a.mov(R12_, RSP)
    a.alu("and", RSP, -16)
    a.alu("sub", RSP, 96)
    for k, v in enumerate(pile):
        a.mov(qword(RSP, depl=32 + 8 * k), v)
    a.call_r(qword(etiq="IAT_" + nom))
    a.mov(RSP, R12_)
    a.pop(R12_)


def handle(s, reg32):
    """rcx = le handle du descripteur du socle (0, 1, 2 : l'entrée, la sortie, les erreurs ; sinon : un handle)"""
    a = s.a
    n = s.n_local()
    a.mov(ECX, reg32)
    a.alu("cmp", ECX, 2)
    a.jcc("a", n)
    a.mov(EAX, 0xFFFFFFF6)               # STD_INPUT_HANDLE = -10 ; -11, -12 pour 1 et 2
    a.alu("sub", EAX, ECX)
    a.mov(ECX, EAX)
    appel(s, "GetStdHandle")
    a.mov(RCX, RAX)
    a.etiquette(n)


def primitives_windows(s):
    a = s.a
    compte = [0]

    def n_local():
        compte[0] += 1
        return f"OSW_{compte[0]}"
    s.n_local = n_local

    # OS_INIT : la console en UTF-8
    a.etiquette("OS_INIT")
    s.sauver(GARDES)
    a.mov(ECX, 65001)
    appel(s, "SetConsoleOutputCP")
    a.mov(ECX, 65001)
    appel(s, "SetConsoleCP")
    s.restaurer(GARDES)
    a.ret()

    # OS_PAGES : toutes les pages des étages 1 à 3 sont dites présentes (Windows n'a pas de mincore simple)
    a.etiquette("OS_PAGES")
    s.sauver([RDI])
    a.lea(RDI, qword(RBP, depl=VEC))
    a.mov(EAX, 0x01010101)
    a.mov(ECX, 49152 // 4)
    a.rep_stosd()
    s.restaurer([RDI])
    a.ret()

    # OS_ECRIRE : edi le descripteur, rsi le tampon, rdx la longueur (tout est écrit) ; rax < 0 en cas d'échec
    a.etiquette("OS_ECRIRE")
    s.sauver([RCX, RDX, RSI, RBX] + GARDES)
    a.mov(RBX, RDX)
    a.etiquette("OS_ECRIRE_B")
    a.test(RBX, RBX)
    a.jcc("e", "OS_ECRIRE_F")
    handle(s, EDI)
    a.mov(RDX, RSI)
    a.mov(R32[8], EBX)
    a.lea(R9_, qword(RBP, depl=COMPTE))
    appel(s, "WriteFile", (0,))
    a.test(EAX, EAX)
    a.jcc("e", "OS_ECRIRE_X")
    a.mov(EAX, dword(RBP, depl=COMPTE))
    a.test(EAX, EAX)
    a.jcc("e", "OS_ECRIRE_X")
    a.alu("add", RSI, RAX)
    a.alu("sub", RBX, RAX)
    a.jmp("OS_ECRIRE_B")
    a.etiquette("OS_ECRIRE_X")
    a.mov(RAX, -1)
    a.jmp("OS_ECRIRE_R")
    a.etiquette("OS_ECRIRE_F")
    a.alu("xor", EAX, EAX)
    a.etiquette("OS_ECRIRE_R")
    s.restaurer([RCX, RDX, RSI, RBX] + GARDES)
    a.ret()

    # OS_LIRE : edi, rsi, rdx -> rax octets lus (0 à la fin) ; les \r sont retirés (une ligne tapée finit par \r\n)
    a.etiquette("OS_LIRE")
    s.sauver([RSI, RDI, RBX] + GARDES)
    a.mov(RBX, RDX)
    a.etiquette("OS_LIRE_B")
    handle(s, EDI)
    a.mov(RDX, RSI)
    a.mov(R32[8], EBX)
    a.lea(R9_, qword(RBP, depl=COMPTE))
    appel(s, "ReadFile", (0,))
    a.test(EAX, EAX)
    a.jcc("e", "OS_LIRE_FIN")
    a.mov(ECX, dword(RBP, depl=COMPTE))
    a.test(ECX, ECX)
    a.jcc("e", "OS_LIRE_FIN")
    # retirer les \r : rsi lit, rdi écrit, ecx le compte
    a.mov(R10_, RSI)
    a.mov(R11_, RSI)
    a.etiquette("OS_LIRE_C")
    a.movzx8(EAX, byte(R10_))
    a.alu("add", R10_, 1)
    a.alu("cmp", EAX, 13)
    a.jcc("e", "OS_LIRE_S")
    a.mov(byte(R11_), AL)
    a.alu("add", R11_, 1)
    a.etiquette("OS_LIRE_S")
    a.alu("sub", ECX, 1)
    a.jcc("ne", "OS_LIRE_C")
    a.mov(RAX, R11_)
    a.alu("sub", RAX, RSI)
    a.jcc("e", "OS_LIRE_B")               # rien que des \r : lire encore
    a.jmp("OS_LIRE_R")
    a.etiquette("OS_LIRE_FIN")
    a.alu("xor", EAX, EAX)
    a.etiquette("OS_LIRE_R")
    s.restaurer([RSI, RDI, RBX] + GARDES)
    a.ret()

    # OS_OUVRIR : rdi le nom (UTF-8, terminé par 0), esi 0 lecture / 1 écriture (créé, vidé) -> rax handle (< 0 : échec)
    a.etiquette("OS_OUVRIR")
    s.sauver([RCX, RDX, RSI, RBX] + GARDES)
    a.mov(EBX, ESI)
    # le nom en UTF-16, juste après la zone d'état (8192 caractères au plus)
    a.mov(ECX, 65001)
    a.alu("xor", EDX, EDX)
    a.mov(R8_, RDI)
    a.mov(R32[9], 0xFFFFFFFF)
    a.lea(RAX, qword(RBP, depl=CHEMIN16))
    appel(s, "MultiByteToWideChar", (RAX, 8192))
    a.test(EAX, EAX)
    a.jcc("e", "OS_OUVRIR_X")
    a.lea(RCX, qword(RBP, depl=CHEMIN16))
    a.mov(EDX, 0x80000000)                # GENERIC_READ
    a.mov(R32[8], 1 | 2)                  # FILE_SHARE_READ | FILE_SHARE_WRITE
    a.alu("xor", R32[9], R32[9])
    a.mov(EAX, 3)                         # OPEN_EXISTING
    a.test(EBX, EBX)
    a.jcc("e", "OS_OUVRIR_L")
    a.mov(EDX, 0x40000000)                # GENERIC_WRITE
    a.mov(EAX, 2)                         # CREATE_ALWAYS
    a.etiquette("OS_OUVRIR_L")
    appel(s, "CreateFileW", (RAX, 0x80, 0))
    a.jmp("OS_OUVRIR_R")
    a.etiquette("OS_OUVRIR_X")
    a.mov(RAX, -1)
    a.etiquette("OS_OUVRIR_R")
    s.restaurer([RCX, RDX, RSI, RBX] + GARDES)
    a.ret()

    # OS_FERMER : edi
    a.etiquette("OS_FERMER")
    s.sauver(GARDES)
    a.mov(ECX, EDI)
    appel(s, "CloseHandle")
    s.restaurer(GARDES)
    a.ret()

    # OS_TAILLE : edi -> rax la taille du fichier
    a.etiquette("OS_TAILLE")
    s.sauver(GARDES)
    a.mov(ECX, EDI)
    a.lea(RDX, qword(RBP, depl=COMPTE))
    appel(s, "GetFileSizeEx")
    a.mov(RAX, qword(RBP, depl=COMPTE))
    s.restaurer(GARDES)
    a.ret()

    # OS_RESERVER : rsi la taille -> rax l'adresse (mémoire à zéro, remplie à la demande), < 0 : échec
    a.etiquette("OS_RESERVER")
    s.sauver(GARDES)
    a.alu("xor", ECX, ECX)
    a.mov(RDX, RSI)
    a.mov(R32[8], 0x3000)                 # MEM_COMMIT | MEM_RESERVE
    a.mov(R32[9], 4)                      # PAGE_READWRITE
    appel(s, "VirtualAlloc")
    a.test(RAX, RAX)
    a.jcc("ne", "OS_RESERVER_R")
    a.mov(RAX, -1)
    a.etiquette("OS_RESERVER_R")
    s.restaurer(GARDES)
    a.ret()

    # OS_RENDRE : rdi l'adresse, rsi la taille (Windows rend toute la réservation)
    a.etiquette("OS_RENDRE")
    s.sauver(GARDES)
    a.mov(RCX, RDI)
    a.alu("xor", EDX, EDX)
    a.mov(R32[8], 0x8000)                 # MEM_RELEASE
    appel(s, "VirtualFree")
    s.restaurer(GARDES)
    a.ret()

    # OS_QUITTER : edi le code de sortie ; si le programme est seul dans sa fenêtre (ouvert d'un double clic), elle
    # attend Entrée avant de se fermer : on lit ce que le programme a écrit
    a.etiquette("OS_QUITTER")
    a.mov(EBX, EDI)
    a.lea(RCX, qword(RBP, depl=COMPTE))
    a.mov(EDX, 4)
    appel(s, "GetConsoleProcessList")
    a.alu("cmp", EAX, 1)
    a.jcc("ne", "OS_QUITTER_F")
    a.mov(ECX, 0xFFFFFFF5)                # la sortie
    appel(s, "GetStdHandle")
    a.mov(RCX, RAX)
    a.lea(RDX, qword(etiq="MSG_FERMER"))
    a.mov(R32[8], len(MSG_FERMER))
    a.lea(R9_, qword(RBP, depl=COMPTE))
    appel(s, "WriteFile", (0,))
    a.mov(ECX, 0xFFFFFFF6)                # l'entrée
    appel(s, "GetStdHandle")
    a.mov(RCX, RAX)
    a.lea(RDX, qword(RBP, depl=COMPTE + 16))
    a.mov(R32[8], 32)
    a.lea(R9_, qword(RBP, depl=COMPTE))
    appel(s, "ReadFile", (0,))
    a.etiquette("OS_QUITTER_F")
    a.mov(ECX, EBX)
    appel(s, "ExitProcess")
    a.ud2()

    # OS_BRUIT -> eax : le compteur du processeur, brassé (32 bits imprévisibles)
    a.etiquette("OS_BRUIT")
    a.rdtsc()
    a.alu("xor", EAX, EDX)
    a.mov(EDX, EAX)
    a.decaler("shr", EDX, 16)
    a.alu("xor", EAX, EDX)
    a.mov(EDX, 0x45D9F3B)
    a.imul(EAX, EDX)
    a.mov(EDX, EAX)
    a.decaler("shr", EDX, 16)
    a.alu("xor", EAX, EDX)
    a.ret()

    # OS_PARLER : pas encore de voix sous Windows (le texte est déjà écrit à la console)
    a.etiquette("OS_PARLER")
    a.ret()

    # OS_ACCORDER : les cubes rangés ne sont pas encore là sous Windows
    a.etiquette("OS_ACCORDER")
    a.jmp("E_CUBES")

    # OS_ARGS : la ligne de commande (sans le nom du programme) comme un seul argument : rsi le tableau, edx 1
    a.etiquette("OS_ARGS")
    s.sauver(GARDES)
    appel(s, "GetCommandLineA")
    a.mov(qword(RBP, depl=ENVP), 0)
    a.movzx8(ECX, byte(RAX))
    a.alu("cmp", ECX, 34)                 # « " » : le nom va jusqu'au guillemet suivant
    a.jcc("ne", "OS_ARGS_ESP")
    a.etiquette("OS_ARGS_G")
    a.alu("add", RAX, 1)
    a.movzx8(ECX, byte(RAX))
    a.test(ECX, ECX)
    a.jcc("e", "OS_ARGS_F")
    a.alu("cmp", ECX, 34)
    a.jcc("ne", "OS_ARGS_G")
    a.alu("add", RAX, 1)
    a.jmp("OS_ARGS_F")
    a.etiquette("OS_ARGS_ESP")            # sinon : jusqu'au premier espace
    a.movzx8(ECX, byte(RAX))
    a.test(ECX, ECX)
    a.jcc("e", "OS_ARGS_F")
    a.alu("cmp", ECX, 32)
    a.jcc("e", "OS_ARGS_F")
    a.alu("add", RAX, 1)
    a.jmp("OS_ARGS_ESP")
    a.etiquette("OS_ARGS_F")
    a.lea(RSI, qword(RBP, depl=CHIFFRES))
    a.mov(qword(RSI), RAX)
    a.mov(EDX, 1)
    s.restaurer(GARDES)
    a.ret()


def chaines_windows(s):
    """la table d'import : KERNEL32.dll et ses fonctions (par leur nom)"""
    a = s.a
    a.aligner(8)
    a.etiquette("IMPORTS")
    a.rva32("ILT")
    a.mots32([0, 0])
    a.rva32("DLL_KERNEL32")
    a.rva32("IAT")
    a.mots32([0, 0, 0, 0, 0])
    a.etiquette("FIN_IMPORTS")
    a.aligner(8)
    a.etiquette("ILT")
    for f in FONCTIONS:
        a.rva64("NOM_" + f)
    a.quad(0)
    a.etiquette("IAT")
    for f in FONCTIONS:
        a.etiquette("IAT_" + f)
        a.rva64("NOM_" + f)
    a.quad(0)
    a.etiquette("FIN_IAT")
    for f in FONCTIONS:
        a.aligner(2)
        a.etiquette("NOM_" + f)
        a.octets(b"\0\0" + f.encode() + b"\0")
    a.etiquette("MSG_FERMER")
    a.octets(MSG_FERMER)
    a.etiquette("DLL_KERNEL32")
    a.octets(b"KERNEL32.dll\0")
