public class Crible { public static void main(String[] args) { final int N = 5000000; int[] p = new int[N];
  for (int q = 2; q < N; q++) p[q] = 1;
  for (int i = 2; i * i < N; i++) if (p[i] == 1) for (int j = i * i; j < N; j += i) p[j] = 0;
  int n = 0; for (int k = 2; k < N; k++) n += p[k]; System.out.println(n); } }
