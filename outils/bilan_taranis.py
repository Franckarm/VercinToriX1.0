"""0.848 : le bilan des lancements de Taranis (les lignes « taranis : … » de VTX_TARANIS=1) : ce que coûtent, par
image, la montée (16 -> 8 octets), la carte, la descente et la conversion 8 -> 16 octets. Ce que les mots de 8 octets
gagneraient : la conversion de la descente (B), et la part de la montée qui convertit.

    python bilan_taranis.py JOURNAL"""
import re
import statistics
import sys

MOTIF = re.compile(r"taranis : (\d+) noyau\(x\), (\d+) tours, Taranis \((\d+) places, (\d+) montées, (\d+) redescendues\) : "
                   r"préparer ([\d.]+) ms, lancer ([\d.]+) ms, la carte ([\d.]+) ms, redescendre ([\d.]+) \+ ([\d.]+) ms")
lignes = [MOTIF.search(l) for l in open(sys.argv[1], encoding="utf-8", errors="replace")]
v = [tuple(float(x) for x in m.groups()) for m in lignes if m]
if not v:
    print("aucune ligne « taranis : » : la carte n'a pas été jouée (VTX_TARANIS=1 et VTX_CARTE=1 ?)")
    sys.exit(0)
# la mise en place (les premiers lancements, quand tout monte) à part : le régime, ce sont les autres
regime = v[3:] if len(v) > 6 else v


def med(k):
    return statistics.median(x[k] for x in regime)


print(f"{len(v)} lancements de la carte ({len(regime)} en régime) ; par lancement, la médiane :")
print(f"  pages montées {med(3):.0f}, pages redescendues {med(4):.0f}")
print(f"  préparer (dont la conversion 16 -> 8 octets) {med(5):.2f} ms")
print(f"  lancer {med(6):.2f} ms, la carte {med(7):.2f} ms")
print(f"  redescendre : la copie de la carte {med(8):.2f} ms + la conversion 8 -> 16 octets {med(9):.2f} ms")
total = med(5) + med(6) + med(7) + med(8) + med(9)
print(f"  en tout {total:.2f} ms ; la conversion 8 -> 16 seule : {100 * med(9) / max(total, 1e-9):.1f} % du lancement")
print("Ce que les mots de 8 octets gagneraient au plus : la conversion de la descente, et la part de « préparer » qui "
      "convertit les pages montées (sans elle, une copie simple).")
