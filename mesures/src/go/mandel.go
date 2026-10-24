package main
import "fmt"
func main() {
	var total uint32
	for py := 0; py < 300; py++ {
		ci := float32(py)*0.008 - 1.2
		for px := 0; px < 400; px++ {
			cr := float32(px)*0.0075 - 2.1
			var x, y float32
			var k uint32
			for k < 200 && x*x+y*y <= 4.0 { t := x*x - y*y + cr; y = 2.0*x*y + ci; x = t; k++ }
			total += k
		}
	}
	fmt.Println(total)
}
