package main
import "fmt"
const M = 524288
func main() {
	u := make([]byte, M*16); v := make([]byte, M*16)
	x := uint32(2463534242)
	for i := 0; i < M; i++ {
		x ^= x << 13; x ^= x >> 17; x ^= x << 5
		for q := 0; q < 16; q++ { u[i*16+q] = byte((x >> (2 * q)) & 3) }
		x ^= x << 13; x ^= x >> 17; x ^= x << 5
		for q := 0; q < 16; q++ { v[i*16+q] = byte((x >> (2 * q)) & 3) }
	}
	var n uint32
	for r := 0; r < 4; r++ { for i := 0; i < M*16; i++ { if u[i] == v[i] { n++ } } }
	fmt.Println(n)
}
