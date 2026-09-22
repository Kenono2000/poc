package main

import "fmt"

func deferDemo() {
    defer fmt.Println("Deferred 1")
    defer fmt.Println("Deferred 2")
    defer fmt.Println("Deferred 3")
    fmt.Println("Function body")
    // Output:
    // Function body
    // Deferred 3
    // Deferred 2
    // Deferred 1 (LIFO order)
}

func safeDivide(a, b int) (result int, err error) {
    defer func() {
        if r := recover(); r != nil {
            err = fmt.Errorf("recovered from panic: %v", r)
        }
    }()
    
    if b == 0 {
        panic("division by zero")
    }
    
    return a / b, nil
}

func main() {
    deferDemo()
    
    result, err := safeDivide(10, 0)
    if err != nil {
        fmt.Println("Error:", err)
    } else {
        fmt.Println("Result:", result)
    }
    
    result, err = safeDivide(10, 2)
    if err != nil {
        fmt.Println("Error:", err)
    } else {
        fmt.Println("Result:", result)
    }
}