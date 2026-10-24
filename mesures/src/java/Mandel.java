public class Mandel { public static void main(String[] args) { int total = 0;
  for (int py = 0; py < 300; py++) { float ci = (float) py * 0.008f - 1.2f;
    for (int px = 0; px < 400; px++) { float cr = (float) px * 0.0075f - 2.1f; float x = 0f, y = 0f; int k = 0;
      while (k < 200 && x * x + y * y <= 4.0f) { float t = x * x - y * y + cr; y = 2.0f * x * y + ci; x = t; k++; }
      total += k; } }
  System.out.println(total); } }
