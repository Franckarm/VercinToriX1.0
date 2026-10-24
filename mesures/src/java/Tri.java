public class Tri { static final int N = 500000; static int[] a = new int[N];
  static void trier(int g, int d) { while (g < d) { int p = a[(g + d) / 2]; int i = g, j = d;
      while (i <= j) { while (a[i] < p) i++; while (a[j] > p) j--; if (i <= j) { int t = a[i]; a[i] = a[j]; a[j] = t; i++; j--; } }
      if (j - g < d - i) { if (g < j) trier(g, j); g = i; } else { if (i < d) trier(i, d); d = j; } } }
  public static void main(String[] args) { int x = (int) 2463534242L;
    for (int i = 0; i < N; i++) { x ^= x << 13; x ^= x >>> 17; x ^= x << 5; a[i] = x & 16777215; }
    trier(0, N - 1); int s = 0; for (int i = 0; i < N; i++) s = s * 31 + a[i];
    System.out.println(Integer.toUnsignedString(s)); } }
