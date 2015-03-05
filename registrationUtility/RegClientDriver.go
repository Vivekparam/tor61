package main

import (
	"fmt"
	"log"
	"os/exec"
	"time"
)

// Change to your agent here
const (
	PORT = "12345"
	NAME = "BEN IS COOL"
	DATA = "12345"
)

func main() {
	register(PORT, NAME, DATA)
	for {
		time.Sleep(time.Second * 3)
		fmt.Println("I'm still here")
	}
}

func register(port string, name string, data string) {
	cmd := exec.Command("python", "registration_client.py", port, name, data)
	if err := cmd.Start(); err != nil {
		log.Fatal(err)
	}
}
