import java.math.BigInteger;
public class Banc128 {
    static final BigInteger M = BigInteger.ONE.shiftLeft(128).subtract(BigInteger.ONE), DEUX = BigInteger.TWO;
    static BigInteger fib(BigInteger n) { return n.compareTo(DEUX) < 0 ? n : fib(n.subtract(BigInteger.ONE)).add(fib(n.subtract(DEUX))); }
    public static void main(String[] a) {
        int n = 2000000; BigInteger compte = BigInteger.ZERO;
        BigInteger[] crible = new BigInteger[n];
        java.util.Arrays.fill(crible, BigInteger.ZERO);
        for (int i = 2; i < n; i++) if (crible[i].signum() == 0) { compte = compte.add(BigInteger.ONE); for (long j = (long) i * i; j < n; j += i) crible[(int) j] = BigInteger.ONE; }
        System.out.println("premiers : " + compte);
        System.out.println("fib(27) : " + fib(BigInteger.valueOf(27)));
        BigInteger h = BigInteger.valueOf(7), t31 = BigInteger.valueOf(31);
        for (long k = 0; k < 3000000; k++) {
            BigInteger s = h.testBit(127) ? h.subtract(M).subtract(BigInteger.ONE) : h;
            h = h.multiply(t31).add(BigInteger.valueOf(k)).xor(s.shiftRight(3)).and(M);
        }
        System.out.println("brassage : " + h.shiftRight(64).longValue() + " " + h.longValue());
    }
}
