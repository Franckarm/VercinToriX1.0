public class Banc64 {
    static long fib(long n) { return n < 2 ? n : fib(n - 1) + fib(n - 2); }
    public static void main(String[] a) {
        int n = 2000000; long compte = 0;
        long[] crible = new long[n];
        for (int i = 2; i < n; i++) if (crible[i] == 0) { compte++; for (long j = (long) i * i; j < n; j += i) crible[(int) j] = 1; }
        System.out.println("premiers : " + compte);
        System.out.println("fib(27) : " + fib(27));
        long h = 7;
        for (long k = 0; k < 3000000; k++) h = (h * 31 + k) ^ (h >>> 3);
        System.out.println("brassage : " + h);
    }
}
