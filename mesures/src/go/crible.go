package main
import "fmt"
const N = 5000000
func main() {
	p := make([]uint32, N)
	for q := 2; q < N; q++ { p[q] = 1 }
	for i := 2; i*i < N; i++ { if p[i] == 1 { for j := i * i; j < N; j += i { p[j] = 0 } } }
	var n uint32
	for k := 2; k < N; k++ { n += p[k] }
	fmt.Println(n)
}
