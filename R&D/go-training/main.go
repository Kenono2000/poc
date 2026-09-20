package main

import "fmt"

func average(numbers []float64) (float64, error) {
	if len(numbers) == 0 {
		return 0, fmt.Errorf("cannot calculate average of empty slice")
	}

	var total float64

	for _, number := range numbers {
		total += number
	}

	return total / float64(len(numbers)), nil
}

func main() {
	scores := []float64{80, 90, 75, 95}

	result, err := average(scores)
	if err != nil {
		fmt.Println("Error:", err)
		return
	}

	fmt.Printf("Average: %.2f\n", result)
}