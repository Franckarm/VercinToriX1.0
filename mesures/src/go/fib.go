package main
import "fmt"
func fib(n uint32) uint32 { if n < 2 { return n }; return fib(n-1) + fib(n-2) }
func main() { fmt.Println(fib(32)) }
