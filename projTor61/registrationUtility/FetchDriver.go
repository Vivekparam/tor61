package main

import (
	"bufio"
	"fmt"
	"log"
	"os"
	"os/exec"
)

func main() {
    if (len(os.Args) != 2) {
        fmt.Println("Usage: go run FetchDriver serviceName");
        return
    }
	name := os.Args[1]
	fetch(name)
}

func fetch(name string) {
	cmd := exec.Command("python", "fetch.py", name)
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		log.Fatal(err)
	}
	if err := cmd.Start(); err != nil {
		log.Fatal(err)
	}

	reader := bufio.NewReader(stdout)
	for {
		line, err := reader.ReadString('\n')

		if err != nil {
			break
		}

		fmt.Printf("Read: %s", line)
	}

	if err := cmd.Wait(); err != nil {
		log.Fatal(err)
	}
}
