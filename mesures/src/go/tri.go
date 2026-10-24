package main
import "fmt"
const N = 500000
var a [N]uint32
func trier(g, d int) {
	for g < d {
		p := a[(g+d)/2]; i, j := g, d
		for i <= j {
			for a[i] < p { i++ }
			for a[j] > p { j-- }
			if i <= j { a[i], a[j] = a[j], a[i]; i++; j-- }
		}
		if j-g < d-i { if g < j { trier(g, j) }; g = i } else { if i < d { trier(i, d) }; d = j }
	}
}
func main() {
	x := uint32(2463534242)
	for i := 0; i < N; i++ { x ^= x << 13; x ^= x >> 17; x ^= x << 5; a[i] = x & 16777215 }
	trier(0, N-1)
	var s uint32
	for i := 0; i < N; i++ { s = s*31 + a[i] }
	fmt.Println(s)
}
