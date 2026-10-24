public class Adn { public static void main(String[] args) { final int M = 524288; byte[] u = new byte[M * 16], v = new byte[M * 16];
  int x = (int) 2463534242L;
  for (int i = 0; i < M; i++) { x ^= x << 13; x ^= x >>> 17; x ^= x << 5; for (int q = 0; q < 16; q++) u[i * 16 + q] = (byte) ((x >>> (2 * q)) & 3);
    x ^= x << 13; x ^= x >>> 17; x ^= x << 5; for (int q = 0; q < 16; q++) v[i * 16 + q] = (byte) ((x >>> (2 * q)) & 3); }
  int n = 0; for (int r = 0; r < 4; r++) for (int i = 0; i < M * 16; i++) if (u[i] == v[i]) n++;
  System.out.println(n); } }
